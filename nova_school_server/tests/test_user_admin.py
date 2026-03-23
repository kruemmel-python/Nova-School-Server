from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nova_school_server.database import SchoolRepository
from nova_school_server.user_admin import UserAdministrationService


class UserAdministrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repository = SchoolRepository(Path(self.tmp.name) / "school.db")
        self.service = UserAdministrationService(self.repository)
        self.repository.create_user(
            username="student",
            display_name="Student Demo",
            password_hash="hash",
            password_salt="salt",
            role="student",
            permissions={"chat.use": True},
            status="active",
        )

    def tearDown(self) -> None:
        self.repository.close()
        self.tmp.cleanup()

    def test_update_user_changes_status_role_and_logs_audit(self) -> None:
        payload = self.service.update_user(
            actor_username="teacher",
            username="student",
            display_name="Student Eins",
            role="teacher",
            status="suspended",
            password="NeuesPasswort123!",
        )

        self.assertEqual(payload["user"]["display_name"], "Student Eins")
        self.assertEqual(payload["user"]["role"], "teacher")
        self.assertEqual(payload["user"]["status"], "suspended")
        self.assertNotIn("password_hash", payload["user"])
        self.assertIn("password", payload["changes"])

        entries = self.service.audit_entries("student")
        self.assertEqual(entries[0]["action"], "admin.user.update")
        self.assertEqual(entries[0]["payload"]["changes"]["status"]["after"], "suspended")
        self.assertTrue(entries[0]["payload"]["changes"]["password"]["reset"])

    def test_permission_audit_payload_only_contains_changed_keys(self) -> None:
        before = self.repository.get_user("student")
        self.repository.update_user_permissions("student", {"chat.use": False, "ai.use": True})
        after = self.repository.get_user("student")

        payload = self.service.permission_audit_payload(before, after)
        self.assertEqual(set(payload["changes"]), {"chat.use", "ai.use"})
        self.assertEqual(payload["changes"]["chat.use"]["before"], True)
        self.assertEqual(payload["changes"]["chat.use"]["after"], False)

    def test_cannot_deactivate_own_current_account(self) -> None:
        with self.assertRaisesRegex(ValueError, "deaktiviert"):
            self.service.update_user(
                actor_username="student",
                username="student",
                display_name="Student Demo",
                role="student",
                status="inactive",
            )


if __name__ == "__main__":
    unittest.main()
