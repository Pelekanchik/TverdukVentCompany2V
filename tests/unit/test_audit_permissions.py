"""Tests for canonical permissions and audit service behavior."""

from types import SimpleNamespace

from ventilation_company.auth.permissions import TAB_PERMISSIONS, Role, has_permission
from ventilation_company.services.audit_service import log_action
from ventilation_company.services.auth_service import AuthUser


class TestCanonicalPermissions:
    def test_admin_can_access_all_tabs(self):
        for tab_id, permission in TAB_PERMISSIONS.items():
            assert has_permission(Role.ADMIN, permission), tab_id

    def test_director_can_access_all_tabs(self):
        for tab_id, permission in TAB_PERMISSIONS.items():
            assert has_permission(Role.DIRECTOR, permission), tab_id

    def test_manager_cannot_open_settings(self):
        assert not has_permission(Role.MANAGER, TAB_PERMISSIONS["settings"])

    def test_manager_can_open_projects_and_pricing(self):
        assert has_permission(Role.MANAGER, TAB_PERMISSIONS["projects"])
        assert has_permission(Role.MANAGER, TAB_PERMISSIONS["pricing"])

    def test_viewer_can_open_documents(self):
        assert has_permission(Role.VIEWER, TAB_PERMISSIONS["documents"])

    def test_unknown_role_has_no_permissions(self):
        assert not has_permission("unknown-role", TAB_PERMISSIONS["projects"])


class TestAuthUserFlags:
    def test_admin_flags(self):
        user = AuthUser(id=1, username="admin", full_name="Admin", role="admin", is_active=True)
        assert user.can_edit()
        assert user.can_delete()
        assert user.can_manage_users()

    def test_manager_can_edit_but_not_delete(self):
        user = AuthUser(
            id=2, username="manager", full_name="Manager", role="manager", is_active=True
        )
        assert user.can_edit()
        assert not user.can_delete()
        assert not user.can_manage_users()

    def test_viewer_cannot_edit(self):
        user = AuthUser(id=3, username="viewer", full_name="Viewer", role="viewer", is_active=True)
        assert not user.can_edit()
        assert not user.can_delete()
        assert not user.can_manage_users()


class FakeAuditSession:
    def __init__(self):
        self.added = []
        self.committed = False
        self.closed = False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class TestAuditService:
    def test_log_action_writes_audit_row(self, monkeypatch):
        from ventilation_company.services import audit_service

        fake = FakeAuditSession()
        monkeypatch.setattr(audit_service, "SessionLocal", lambda: fake)
        actor = SimpleNamespace(id=10, username="admin", role="admin")

        log_action(
            "product.create",
            entity_type="product",
            entity_id=99,
            details={"name": "Duct"},
            actor=actor,
        )

        assert fake.committed
        assert fake.closed
        assert len(fake.added) == 1
        row = fake.added[0]
        assert row.action == "product.create"
        assert row.entity_type == "product"
        assert row.entity_id == "99"
        assert row.details == {"name": "Duct"}
        assert row.actor_id == 10
        assert row.actor_username == "admin"
        assert row.actor_role == "admin"

    def test_log_action_never_raises_when_db_fails(self, monkeypatch):
        from ventilation_company.services import audit_service

        class BrokenSession:
            def add(self, obj):
                raise RuntimeError("db down")

            def commit(self):
                raise RuntimeError("db down")

            def close(self):
                pass

        monkeypatch.setattr(audit_service, "SessionLocal", lambda: BrokenSession())

        log_action("backup.create", details={"path": "/tmp/backup"})
