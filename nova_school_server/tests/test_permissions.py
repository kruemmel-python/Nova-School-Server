from __future__ import annotations

import unittest

from nova_school_server.permissions import resolve_permissions


class PermissionTests(unittest.TestCase):
    def test_student_defaults_enable_ai_but_disable_web(self) -> None:
        permissions = resolve_permissions("student")
        self.assertTrue(permissions["ai.use"])
        self.assertTrue(permissions["mentor.use"])
        self.assertTrue(permissions["curriculum.use"])
        self.assertFalse(permissions["web.access"])
        self.assertTrue(permissions["run.python"])

    def test_user_override_wins_over_group_false(self) -> None:
        permissions = resolve_permissions(
            "student",
            group_overrides=[{"run.python": False, "chat.use": True}],
            user_overrides={"run.python": True},
        )
        self.assertTrue(permissions["run.python"])
        self.assertTrue(permissions["chat.use"])

    def test_admin_role_keeps_core_permissions_even_if_user_override_disables_them(self) -> None:
        permissions = resolve_permissions(
            "admin",
            user_overrides={"admin.manage": False, "chat.use": False, "docs.read": False},
        )
        self.assertTrue(permissions["admin.manage"])
        self.assertTrue(permissions["chat.use"])
        self.assertTrue(permissions["docs.read"])


if __name__ == "__main__":
    unittest.main()
