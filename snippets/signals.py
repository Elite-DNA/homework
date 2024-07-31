from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AuditLog, Snippet
from django.contrib.auth.models import User
from .middleware import get_current_user


TRACKED_MODELS = [User, Snippet]


@receiver(post_save)
def log_model_create_update(sender, instance, created, **kwargs):
    if sender in TRACKED_MODELS:
        action = "CREATE" if created else "UPDATE"
        user = get_current_user()
        if user:
            AuditLog.objects.create(
                model_name=sender.__name__,
                object_id=instance.pk,
                action=action,
                user=user,
            )
        else:
            # This is for testing purposes
            pass


@receiver(post_delete)
def log_model_delete(sender, instance, **kwargs):
    if sender in TRACKED_MODELS:
        user = get_current_user()
        if user:
            AuditLog.objects.create(
                model_name=sender.__name__,
                object_id=instance.pk,
                action="DELETE",
                user=user,
            )
        else:
            # This is for testing purposes
            pass
