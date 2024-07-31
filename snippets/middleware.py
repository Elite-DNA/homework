import threading
from django.utils.deprecation import MiddlewareMixin

# Workaround to obtain current user to pass to signals

_thread_local = threading.local()

class CurrentUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _thread_local.current_user = getattr(request, 'user', None)

    def process_response(self, request, response):
        if hasattr(_thread_local, 'current_user'):
            del _thread_local.current_user
        return response

def get_current_user():
    return getattr(_thread_local, 'current_user', None)

