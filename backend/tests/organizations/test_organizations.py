"""Tests for the organizations endpoints (Phase 2)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

ORGS = "/api/v1/organizations"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_org(
    client: TestClient,
    headers: dict[str, str],
    name: str = "UCAB Lab 3D",
    country: str = "VE",
) -> dict[str, object]:
    resp = client.post(
        ORGS,
        headers=headers,
        json={
            "name": name,
            "description": "Lab 3D.",
            "contact": "fablab@ucab.edu.ve",
            "country": country,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateOrganization:
    def test_requires_auth(self, client: TestClient):
        assert client.post(ORGS, json={}).status_code == 401

    def test_creator_becomes_owner(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        assert org["verified"] is False
        assert org["registered_by_id"] == str(normal_user.id)

        members = client.get(
            f"{ORGS}/{org['id']}/members", headers=auth_headers(normal_user)
        ).json()
        owners = [m for m in members if m["role"] == "owner"]
        assert len(owners) == 1
        assert owners[0]["user_id"] == str(normal_user.id)

    def test_duplicate_name_conflicts(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        _create_org(client, auth_headers(normal_user))
        resp = client.post(
            ORGS,
            headers=auth_headers(normal_user),
            json={
                "name": "UCAB Lab 3D",
                "contact": "x@y.z",
                "country": "VE",
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_NAME_TAKEN"


class TestListAndGet:
    def test_guest_sees_only_verified(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        # Unverified: not in the public list.
        assert client.get(ORGS).json() == []
        # Verify it, then it shows up publicly.
        client.post(f"{ORGS}/{org['id']}/verify", headers=auth_headers(admin_user))
        names = {o["name"] for o in client.get(ORGS).json()}
        assert "UCAB Lab 3D" in names

    def test_unverified_detail_hidden_from_guest(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        assert client.get(f"{ORGS}/{org['id']}").status_code == 404
        # Owner can still see it.
        resp = client.get(f"{ORGS}/{org['id']}", headers=auth_headers(normal_user))
        assert resp.status_code == 200

    def test_country_filter(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        a = _create_org(client, auth_headers(normal_user), "Org VE", "VE")
        b = _create_org(client, auth_headers(normal_user), "Org CO", "CO")
        for org in (a, b):
            client.post(f"{ORGS}/{org['id']}/verify", headers=auth_headers(admin_user))
        names = {o["name"] for o in client.get(f"{ORGS}?country=CO").json()}
        assert names == {"Org CO"}


class TestVerification:
    def test_non_maintainer_cannot_verify(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/verify", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"

    def test_maintainer_verifies(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/verify", headers=auth_headers(maintainer)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is True
        assert body["verified_by_id"] == str(maintainer.id)


class TestMembership:
    def test_owner_adds_member(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        assert resp.status_code == 201
        assert resp.json()["user_id"] == str(bob.id)
        assert resp.json()["role"] == "member"

    def test_add_unknown_user_404(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "ghost"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "USER_NOT_FOUND"

    def test_non_owner_cannot_add(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(bob),
            json={"username": "bob"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

    def test_owner_cannot_leave(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.delete(
            f"{ORGS}/{org['id']}/members/{normal_user.id}",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "OWNER_CANNOT_LEAVE"

    def test_member_leaves(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.delete(
            f"{ORGS}/{org['id']}/members/{bob.id}",
            headers=auth_headers(bob),
        )
        assert resp.status_code == 204


class TestOwnershipTransfer:
    def test_transfer_to_member(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.post(
            f"{ORGS}/{org['id']}/transfer-ownership",
            headers=auth_headers(normal_user),
            json={"target_user_id": str(bob.id)},
        )
        assert resp.status_code == 200
        members = client.get(
            f"{ORGS}/{org['id']}/members", headers=auth_headers(bob)
        ).json()
        roles = {m["user_id"]: m["role"] for m in members}
        assert roles[str(bob.id)] == "owner"
        assert roles[str(normal_user.id)] == "member"

    def test_transfer_to_non_member_conflicts(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/transfer-ownership",
            headers=auth_headers(normal_user),
            json={"target_user_id": str(stranger.id)},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "NOT_ORG_MEMBER"

    def test_force_transfer_by_maintainer(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        stranger = make_user("stranger")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/force-transfer-ownership",
            headers=auth_headers(maintainer),
            json={"target_user_id": str(stranger.id)},
        )
        assert resp.status_code == 200
        members = client.get(
            f"{ORGS}/{org['id']}/members", headers=auth_headers(maintainer)
        ).json()
        owners = [m["user_id"] for m in members if m["role"] == "owner"]
        assert owners == [str(stranger.id)]


class TestListSearchAndPrivileged:
    def test_q_search(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        a = _create_org(client, auth_headers(normal_user), "Alpha Lab")
        b = _create_org(client, auth_headers(normal_user), "Beta Works")
        for org in (a, b):
            client.post(f"{ORGS}/{org['id']}/verify", headers=auth_headers(admin_user))
        names = {o["name"] for o in client.get(f"{ORGS}?q=Alpha").json()}
        assert names == {"Alpha Lab"}

    def test_guest_verified_param_does_not_expose_unverified(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        # Unlike centers, unverified orgs stay private even with ?verified=false.
        _create_org(client, auth_headers(normal_user))
        assert client.get(f"{ORGS}?verified=false").json() == []

    def test_maintainer_can_list_unverified(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        org = _create_org(client, auth_headers(normal_user))
        listing = client.get(
            f"{ORGS}?verified=false", headers=auth_headers(maintainer)
        ).json()
        assert org["name"] in {o["name"] for o in listing}


class TestOrgDetailAndMembersAuth:
    def test_nonexistent_404(self, client: TestClient):
        assert client.get(f"{ORGS}/{uuid.uuid4()}").status_code == 404

    def test_non_member_cannot_list_members(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.get(f"{ORGS}/{org['id']}/members", headers=auth_headers(stranger))
        assert resp.status_code == 404


class TestUpdateOrganization:
    def test_owner_edits(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.put(
            f"{ORGS}/{org['id']}",
            headers=auth_headers(normal_user),
            json={"description": "Updated desc", "contact": "new@x.z"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Updated desc"
        assert body["contact"] == "new@x.z"

    def test_requires_auth(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.put(f"{ORGS}/{org['id']}", json={"description": "x"})
        assert resp.status_code == 401

    def test_non_owner_forbidden(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.put(
            f"{ORGS}/{org['id']}",
            headers=auth_headers(stranger),
            json={"description": "Hacked"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

    def test_name_clash_conflicts(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        a = _create_org(client, auth_headers(normal_user), "Org A")
        _create_org(client, auth_headers(normal_user), "Org B")
        resp = client.put(
            f"{ORGS}/{a['id']}",
            headers=auth_headers(normal_user),
            json={"name": "Org B"},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_NAME_TAKEN"

    def test_maintainer_can_edit(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        org = _create_org(client, auth_headers(normal_user))
        resp = client.put(
            f"{ORGS}/{org['id']}",
            headers=auth_headers(maintainer),
            json={"description": "By mod"},
        )
        assert resp.status_code == 200


class TestRevokeAndArchive:
    def test_maintainer_revokes_verification(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        org = _create_org(client, auth_headers(normal_user))
        client.post(f"{ORGS}/{org['id']}/verify", headers=auth_headers(maintainer))
        resp = client.post(
            f"{ORGS}/{org['id']}/revoke-verification",
            headers=auth_headers(maintainer),
            json={"reason": "no longer valid"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["verified"] is False
        assert body["verified_by_id"] is None

    def test_non_maintainer_cannot_revoke(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/revoke-verification",
            headers=auth_headers(normal_user),
            json={},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"

    def test_owner_archives_empty_org(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/archive", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_non_owner_cannot_archive(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/archive", headers=auth_headers(stranger)
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"


class TestMembershipExtra:
    def test_owner_removes_member(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.delete(
            f"{ORGS}/{org['id']}/members/{bob.id}",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 204

    def test_remove_non_member_conflicts(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.delete(
            f"{ORGS}/{org['id']}/members/{stranger.id}",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "NOT_ORG_MEMBER"

    def test_non_owner_cannot_transfer(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.post(
            f"{ORGS}/{org['id']}/transfer-ownership",
            headers=auth_headers(bob),
            json={"target_user_id": str(bob.id)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

    def test_force_transfer_requires_maintainer(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        org = _create_org(client, auth_headers(normal_user))
        resp = client.post(
            f"{ORGS}/{org['id']}/force-transfer-ownership",
            headers=auth_headers(normal_user),
            json={"target_user_id": str(bob.id)},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"
