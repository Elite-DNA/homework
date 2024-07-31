from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework import status
from .models import AuditLog


class UserTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create both staff and non staff user
        self.user = User.objects.create_user(username="user", password="password")
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )

        self.client.login(username="staff", password="password")

        # Create test user for operations
        self.test_user = User.objects.create(username="testuser", is_active=True)

    def test_list_users_non_staff(self):
        # set test user to inactive
        self.test_user.is_active = False
        self.test_user.save()

        # Log in as non-staff user
        self.client.login(username="user", password="password")

        # Non staff user should not see soft deleted users
        response = self.client.get("/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("results", [])
        usernames = [user.get("username") for user in results]
        # Make sure test user is not in user response
        self.assertNotIn("testuser", usernames)

    def test_list_users_staff_with_flag(self):
        # Log in as staff user
        self.client.login(username="staff", password="password")

        User.objects.filter(username="testuser").update(is_active=False)
        response = self.client.get("/users/", {"show_deleted": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("results", [])
        usernames = [user.get("username") for user in results]
        self.assertIn("testuser", usernames)

    def test_create_user_staff(self):
        # Log in as staff user
        self.client.login(username="staff", password="password")

        data = {"username": "newuser", "password": "newpassword"}
        response = self.client.post("/users/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(username="newuser")
        self.assertEqual(new_user.username, "newuser")

    def test_create_user_non_staff(self):
        # Log in as non staff user
        self.client.login(username="user", password="password")

        data = {"username": "newuser", "password": "newpassword"}
        response = self.client.post("/users/", data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_user_staff(self):
        # Log in as staff user
        self.client.login(username="staff", password="password")

        response = self.client.delete(f"/users/{self.test_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.get(id=self.test_user.id).is_active)

    def test_destroy_user_non_staff(self):
        # Log in as non-staff user
        self.client.login(username="user", password="password")

        response = self.client.delete(f"/users/{self.test_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(User.objects.get(id=self.test_user.id).is_active)


class AuditLogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="user", password="password")
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )

        # Log in as the staff user
        self.client.login(username="staff", password="password")

        # Create a test user for operations
        self.test_user = User.objects.create_user(
            username="testuser", password="password"
        )

        # Create some initial logs
        self.audit_log1 = AuditLog.objects.create(
            model_name="User",
            object_id=self.test_user.id,
            action="CREATE",
            timestamp="2024-01-01T00:00:00Z",
            user=self.staff_user,
        )

    def test_audit_log_entry_created(self):
        # Performing action that should be logged
        self.client.login(username="staff", password="password")
        response = self.client.post(
            "/users/", {"username": "newuser", "password": "newpassword"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure the audit log has been created
        logs = AuditLog.objects.all()
        self.assertGreater(logs.count(), 1)
        new_log = logs.latest("timestamp")
        self.assertEqual(new_log.action, "CREATE")
        self.assertEqual(new_log.model_name, "User")
        self.assertEqual(new_log.object_id, User.objects.get(username="newuser").id)

    def test_view_audit_logs_by_staff(self):
        # Ensure the staff user can view audit logs
        self.client.login(username="staff", password="password")
        response = self.client.get("/audit-logs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        results = data.get("results", [])
        self.assertGreater(len(results), 0)
        # Verify logs contain required fields
        for log in results:
            self.assertIn("user", log)
            self.assertIn("model_name", log)
            self.assertIn("object_id", log)
            self.assertIn("action", log)
            self.assertIn("timestamp", log)

    def test_view_audit_logs_by_non_staff(self):
        # Log in as a non-staff user
        self.client.login(username="user", password="password")
        response = self.client.get("/audit-logs/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_add_or_edit_audit_log(self):
        self.client.login(username="staff", password="password")
        data = {
            "model_name": "User",
            "object_id": 1,
            "action": "DELETE",
            "timestamp": "2024-01-02T00:00:00Z",
        }
        response = self.client.post("/audit-logs/", data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        response = self.client.put(f"/audit-logs/{self.audit_log1.id}/", data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
