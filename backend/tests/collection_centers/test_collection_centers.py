"""Tests for the collection centers endpoints (Phase 2)."""

import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

CENTERS = "/api/v1/collection-centers"
ORGS = "/api/v1/organizations"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _create_center(
    client: TestClient,
    headers: dict[str, str],
    name: str = "UCAB Lab - Caracas",
    country: str = "VE",
    city: str = "Caracas",
    owner_organization_id: str | None = None,
    state: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": name,
        "address": "Av. Teheran, Caracas",
        "country": country,
        "city": city,
        "contact": "+58-212-407-4400",
    }
    if owner_organization_id is not None:
        payload["owner_organization_id"] = owner_organization_id
    if state is not None:
        payload["state"] = state
    if tags is not None:
        payload["tags"] = tags
    resp = client.post(CENTERS, headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _verify(client: TestClient, center_id: object, headers: dict[str, str]) -> None:
    resp = client.post(f"{CENTERS}/{center_id}/verify", headers=headers)
    assert resp.status_code == 200, resp.text


class TestTags:
    def test_create_with_tags(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        cc = _create_center(
            client, auth_headers(normal_user), tags=["ferulas", "drop-off"]
        )
        assert cc["tags"] == ["ferulas", "drop-off"]

    def test_tags_default_to_empty(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        cc = _create_center(client, auth_headers(normal_user))
        assert cc["tags"] == []

    def test_filter_by_tag(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        headers = auth_headers(normal_user)
        tagged = _create_center(client, headers, name="Tagged", tags=["ferulas"])
        _create_center(client, headers, name="Untagged")
        listing = client.get(CENTERS, params={"tag": "ferulas"}).json()
        ids = {c["id"] for c in listing}
        assert tagged["id"] in ids
        assert all("ferulas" in c["tags"] for c in listing)

    def test_update_tags(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        headers = auth_headers(normal_user)
        cc = _create_center(client, headers, tags=["old"])
        resp = client.put(
            f"{CENTERS}/{cc['id']}", headers=headers, json={"tags": ["new", "fresh"]}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["tags"] == ["new", "fresh"]


class TestCreateCenter:
    def test_invalid_body_is_rejected(self, client: TestClient):
        # Open endpoint, but the payload is still validated.
        assert client.post(CENTERS, json={}).status_code == 422

    def test_anonymous_can_create(self, client: TestClient):
        # No auth header: a guest registers a center (open API).
        cc = _create_center(client, headers={}, name="Centro Anónimo")
        assert cc["verified"] is False
        # Owned by the system anonymous account, not an org.
        assert cc["owner_user_id"] is not None
        assert cc["owner_organization_id"] is None
        assert cc["registered_by_id"] == cc["owner_user_id"]
        # It is immediately resource of the public directory (unverified).
        listing = client.get(CENTERS).json()
        assert cc["id"] in {c["id"] for c in listing}

    def test_owner_defaults_to_caller(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        assert cc["owner_user_id"] == str(normal_user.id)
        assert cc["owner_organization_id"] is None
        assert cc["verified"] is False

    def test_on_behalf_of_org_requires_membership(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("orgowner")
        org = client.post(
            ORGS,
            headers=auth_headers(owner),
            json={"name": "Org", "contact": "x@y.z", "country": "VE"},
        ).json()
        resp = client.post(
            CENTERS,
            headers=auth_headers(normal_user),
            json={
                "name": "C",
                "address": "A",
                "country": "VE",
                "city": "Caracas",
                "contact": "x",
                "owner_organization_id": org["id"],
            },
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ORG_MEMBERSHIP_REQUIRED"

    def test_on_behalf_of_org_as_member(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = client.post(
            ORGS,
            headers=auth_headers(normal_user),
            json={"name": "Org", "contact": "x@y.z", "country": "VE"},
        ).json()
        cc = _create_center(
            client, auth_headers(normal_user), owner_organization_id=org["id"]
        )
        assert cc["owner_organization_id"] == org["id"]
        assert cc["owner_user_id"] is None

    def test_location_url_is_stored(self, client: TestClient):
        maps = "https://maps.google.com/?q=Caracas"
        resp = client.post(
            CENTERS,
            json={
                "name": "Mapped Center",
                "address": "Av. Teheran, Caracas",
                "country": "VE",
                "city": "Caracas",
                "contact": "x",
                "location_url": maps,
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["location_url"] == maps

    def test_blank_location_url_collapses_to_null(self, client: TestClient):
        resp = client.post(
            CENTERS,
            json={
                "name": "Blank Map Center",
                "address": "Av. Teheran, Caracas",
                "country": "VE",
                "city": "Caracas",
                "contact": "x",
                "location_url": "   ",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["location_url"] is None

    def test_non_http_location_url_is_rejected(self, client: TestClient):
        resp = client.post(
            CENTERS,
            json={
                "name": "Bad Map Center",
                "address": "Av. Teheran, Caracas",
                "country": "VE",
                "city": "Caracas",
                "contact": "x",
                "location_url": "javascript:alert(1)",
            },
        )
        assert resp.status_code == 422


class TestPublicRead:
    def test_guest_sees_unverified_with_flag(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        # Unverified active centers are now public, flagged verified=false.
        listing = client.get(CENTERS).json()
        assert [c["id"] for c in listing] == [cc["id"]]
        assert listing[0]["verified"] is False
        # Verification flips the flag, not the visibility.
        _verify(client, cc["id"], auth_headers(maintainer))
        flags = {c["id"]: c["verified"] for c in client.get(CENTERS).json()}
        assert flags[cc["id"]] is True

    def test_unverified_detail_visible_to_guest(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.get(f"{CENTERS}/{cc['id']}")
        assert resp.status_code == 200
        assert resp.json()["verified"] is False

    def test_inactive_center_hidden_from_guest(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        # Operationally inactive centers are not resource of the public list.
        client.post(
            f"{CENTERS}/{cc['id']}/toggle-status",
            headers=auth_headers(normal_user),
            json={"status": "inactive"},
        )
        assert client.get(CENTERS).json() == []
        assert client.get(f"{CENTERS}/{cc['id']}").status_code == 404
        # The owner (effective member) can still see it.
        resp = client.get(f"{CENTERS}/{cc['id']}", headers=auth_headers(normal_user))
        assert resp.status_code == 200

    def test_country_city_filters(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        a = _create_center(client, auth_headers(normal_user), "A", "VE", "Caracas")
        b = _create_center(client, auth_headers(normal_user), "B", "VE", "Maracaibo")
        for cc in (a, b):
            _verify(client, cc["id"], auth_headers(maintainer))
        names = {c["name"] for c in client.get(f"{CENTERS}?city=Maracaibo").json()}
        assert names == {"B"}

    def test_state_filter(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        # ``state`` is optional: one center has it, one does not.
        with_state = _create_center(
            client, auth_headers(normal_user), "A", "US", "Los Angeles", state="CA"
        )
        without_state = _create_center(
            client, auth_headers(normal_user), "B", "US", "Austin"
        )
        assert with_state["state"] == "CA"
        assert without_state["state"] is None
        for cc in (with_state, without_state):
            _verify(client, cc["id"], auth_headers(maintainer))
        # Filtering by state returns only the matching center (the
        # state-less one is excluded).
        names = {c["name"] for c in client.get(f"{CENTERS}?state=CA").json()}
        assert names == {"A"}

    def test_verified_filter_applies_to_guests(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        verified = _create_center(client, auth_headers(normal_user), "Verified")
        unverified = _create_center(client, auth_headers(normal_user), "Unverified")
        _verify(client, verified["id"], auth_headers(maintainer))

        # No filter: both are returned.
        assert len(client.get(CENTERS).json()) == 2
        # verified=true: only the verified one (guest, no auth).
        only_true = client.get(f"{CENTERS}?verified=true").json()
        assert [c["id"] for c in only_true] == [verified["id"]]
        # verified=false: only the unverified one (guest, no auth).
        only_false = client.get(f"{CENTERS}?verified=false").json()
        assert [c["id"] for c in only_false] == [unverified["id"]]


class TestMembershipPowers:
    def test_non_member_cannot_edit(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.put(
            f"{CENTERS}/{cc['id']}",
            headers=auth_headers(stranger),
            json={"name": "Hacked"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_MEMBER"

    def test_owner_toggles_status(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/toggle-status",
            headers=auth_headers(normal_user),
            json={"status": "inactive"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"

    def test_contributor_gains_member_powers(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        cc = _create_center(client, auth_headers(normal_user))
        add = client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        assert add.status_code == 201
        # Bob can now edit the center as an effective member.
        resp = client.put(
            f"{CENTERS}/{cc['id']}",
            headers=auth_headers(bob),
            json={"description": "Updated by contributor"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated by contributor"

    def test_contributor_cannot_add_contributors(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        carol = make_user("carol")
        cc = _create_center(client, auth_headers(normal_user))
        client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        # Bob is a member, not an effective owner.
        resp = client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(bob),
            json={"username": "carol"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"
        assert carol  # referenced

    def test_contributor_self_removes(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        cc = _create_center(client, auth_headers(normal_user))
        client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.delete(
            f"{CENTERS}/{cc['id']}/contributors/{bob.id}",
            headers=auth_headers(bob),
        )
        assert resp.status_code == 204


class TestArchive:
    def test_owner_archives(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/archive", headers=auth_headers(normal_user)
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
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/archive", headers=auth_headers(stranger)
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

    def test_maintainer_force_archives(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/force-archive",
            headers=auth_headers(maintainer),
        )
        assert resp.status_code == 200
        assert resp.json()["active"] is False


class TestRestore:
    def _archive(
        self, client: TestClient, center_id: object, headers: dict[str, str]
    ) -> None:
        resp = client.post(f"{CENTERS}/{center_id}/archive", headers=headers)
        assert resp.status_code == 200, resp.text

    def test_maintainer_lists_archived_centers(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        self._archive(client, cc["id"], auth_headers(normal_user))

        # Archived centers vanish from the public and default listings...
        assert client.get(CENTERS).json() == []
        assert client.get(CENTERS, headers=auth_headers(maintainer)).json() == []
        # ...but a maintainer can pull them with active=false.
        archived = client.get(
            f"{CENTERS}?active=false", headers=auth_headers(maintainer)
        ).json()
        assert cc["id"] in {c["id"] for c in archived}

    def test_active_filter_ignored_for_non_privileged(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        self._archive(client, cc["id"], auth_headers(normal_user))
        # A non-privileged caller cannot surface archived centers.
        assert client.get(f"{CENTERS}?active=false").json() == []
        owner_view = client.get(
            f"{CENTERS}?active=false", headers=auth_headers(normal_user)
        ).json()
        assert owner_view == []

    def test_maintainer_restores_center(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        self._archive(client, cc["id"], auth_headers(normal_user))

        resp = client.post(
            f"{CENTERS}/{cc['id']}/restore", headers=auth_headers(maintainer)
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["active"] is True
        assert resp.json()["status"] == "active"
        # Back in the public directory.
        assert cc["id"] in {c["id"] for c in client.get(CENTERS).json()}

    def test_non_maintainer_cannot_restore(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        self._archive(client, cc["id"], auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/restore", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 403

    def test_restore_unknown_center_is_404(
        self,
        client: TestClient,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        resp = client.post(
            f"{CENTERS}/{uuid.uuid4()}/restore", headers=auth_headers(maintainer)
        )
        assert resp.status_code == 404


class TestOrgArchiveGuard:
    def test_org_archive_blocked_by_active_center(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        org = client.post(
            ORGS,
            headers=auth_headers(normal_user),
            json={"name": "Org", "contact": "x@y.z", "country": "VE"},
        ).json()
        _create_center(
            client, auth_headers(normal_user), owner_organization_id=org["id"]
        )
        resp = client.post(
            f"{ORGS}/{org['id']}/archive", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORG_ARCHIVE_BLOCKED"


class TestListVisibilityForPrivileged:
    def test_maintainer_sees_inactive_centers(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        client.post(
            f"{CENTERS}/{cc['id']}/toggle-status",
            headers=auth_headers(normal_user),
            json={"status": "inactive"},
        )
        # Guest does not see operationally-inactive centers...
        assert client.get(CENTERS).json() == []
        # ...but a maintainer does.
        listing = client.get(CENTERS, headers=auth_headers(maintainer)).json()
        assert cc["id"] in {c["id"] for c in listing}

    def test_country_filter(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        _create_center(client, auth_headers(normal_user), "A", "VE", "Caracas")
        _create_center(client, auth_headers(normal_user), "B", "CO", "Bogota")
        names = {c["name"] for c in client.get(f"{CENTERS}?country=CO").json()}
        assert names == {"B"}


class TestDetail:
    def test_nonexistent_returns_404(self, client: TestClient):
        resp = client.get(f"{CENTERS}/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "COLLECTION_CENTER_NOT_FOUND"


class TestRevokeVerification:
    def test_maintainer_revokes(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        _verify(client, cc["id"], auth_headers(maintainer))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/revoke-verification",
            headers=auth_headers(maintainer),
            json={"reason": "stale info"},
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
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/revoke-verification",
            headers=auth_headers(normal_user),
            json={},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"


class TestMutationAuthorization:
    def test_verify_requires_maintainer(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/verify", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"

    def test_verify_requires_auth(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        assert client.post(f"{CENTERS}/{cc['id']}/verify").status_code == 401

    def test_force_archive_requires_maintainer(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/force-archive",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "ROLE_REQUIRED"

    def test_toggle_status_non_member_forbidden(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/toggle-status",
            headers=auth_headers(stranger),
            json={"status": "inactive"},
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_EFFECTIVE_MEMBER"

    def test_update_requires_auth(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.put(f"{CENTERS}/{cc['id']}", json={"name": "x"})
        assert resp.status_code == 401


class TestUpdate:
    def test_maintainer_can_edit_any_center(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        maintainer = make_user("maint", UserRole.MAINTAINER)
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.put(
            f"{CENTERS}/{cc['id']}",
            headers=auth_headers(maintainer),
            json={"name": "Renamed by mod"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed by mod"

    def test_member_can_set_and_clear_location_url(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        maps = "https://maps.app.goo.gl/abc123"
        set_resp = client.put(
            f"{CENTERS}/{cc['id']}",
            headers=auth_headers(normal_user),
            json={"location_url": maps},
        )
        assert set_resp.status_code == 200
        assert set_resp.json()["location_url"] == maps
        clear_resp = client.put(
            f"{CENTERS}/{cc['id']}",
            headers=auth_headers(normal_user),
            json={"location_url": ""},
        )
        assert clear_resp.status_code == 200
        assert clear_resp.json()["location_url"] is None

    def test_update_nonexistent_404(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        resp = client.put(
            f"{CENTERS}/{uuid.uuid4()}",
            headers=auth_headers(normal_user),
            json={"name": "x"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "COLLECTION_CENTER_NOT_FOUND"


class TestContributorsManagement:
    def test_member_lists_contributors(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        make_user("bob")
        cc = _create_center(client, auth_headers(normal_user))
        client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.get(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 200
        assert "bob" in {c["username"] for c in resp.json()}

    def test_non_member_cannot_list_contributors(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.get(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(stranger),
        )
        assert resp.status_code == 404

    def test_add_unknown_user_404(
        self,
        client: TestClient,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "ghost"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "USER_NOT_FOUND"

    def test_owner_removes_contributor(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        bob = make_user("bob")
        cc = _create_center(client, auth_headers(normal_user))
        client.post(
            f"{CENTERS}/{cc['id']}/contributors",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        resp = client.delete(
            f"{CENTERS}/{cc['id']}/contributors/{bob.id}",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 204

    def test_remove_non_contributor_conflicts(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        stranger = make_user("stranger")
        cc = _create_center(client, auth_headers(normal_user))
        resp = client.delete(
            f"{CENTERS}/{cc['id']}/contributors/{stranger.id}",
            headers=auth_headers(normal_user),
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "NOT_CONTRIBUTOR"


class TestOrgOwnedCenterAuthorization:
    """Polymorphic ownership: powers resolve through the owning org."""

    def test_member_has_member_powers_only_owner_has_owner_powers(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        # normal_user owns the org; bob is a plain org member.
        bob = make_user("bob")
        org = client.post(
            ORGS,
            headers=auth_headers(normal_user),
            json={"name": "Org", "contact": "x@y.z", "country": "VE"},
        ).json()
        client.post(
            f"{ORGS}/{org['id']}/members",
            headers=auth_headers(normal_user),
            json={"username": "bob"},
        )
        cc = _create_center(
            client, auth_headers(normal_user), owner_organization_id=org["id"]
        )

        # An org member is an effective member of the org-owned center: edit OK.
        edit = client.put(
            f"{CENTERS}/{cc['id']}",
            headers=auth_headers(bob),
            json={"description": "edited by org member"},
        )
        assert edit.status_code == 200

        # ...but not an effective owner: archive is forbidden for the member.
        member_archive = client.post(
            f"{CENTERS}/{cc['id']}/archive", headers=auth_headers(bob)
        )
        assert member_archive.status_code == 403
        assert member_archive.json()["error"]["code"] == "NOT_EFFECTIVE_OWNER"

        # The org owner has owner powers on the org-owned center.
        owner_archive = client.post(
            f"{CENTERS}/{cc['id']}/archive", headers=auth_headers(normal_user)
        )
        assert owner_archive.status_code == 200
        assert owner_archive.json()["active"] is False
