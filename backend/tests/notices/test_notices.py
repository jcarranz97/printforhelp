"""Tests for the site notices endpoints (page banners + entity notices)."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.constants import UserRole
from app.users.models import User

NOTICES = "/api/v1/notices"
RESOURCES = "/api/v1/resources"
CENTERS = "/api/v1/collection-centers"
REQUESTS = "/api/v1/requests"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _translation(
    language: str = "en",
    message: str = "Heads up: centers change fast.",
    title: str | None = "Notice",
    action_label: str | None = None,
    action_url: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"language": language, "message": message}
    if title is not None:
        payload["title"] = title
    if action_label is not None:
        payload["action_label"] = action_label
    if action_url is not None:
        payload["action_url"] = action_url
    return payload


def _page_payload(
    scopes: list[str] | None = None,
    severity: str = "info",
    translations: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "severity": severity,
        "scopes": scopes if scopes is not None else ["centers"],
        "translations": translations if translations is not None else [_translation()],
    }


def _create_resource(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        RESOURCES,
        headers=headers,
        json={"name": "Ferula", "source_url": "https://example.com/f.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_center(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(
        CENTERS,
        headers=headers,
        json={
            "name": "Centro 1",
            "address": "Calle 1",
            "country": "Venezuela",
            "city": "Caracas",
            "contact": "+58 000",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_request(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    resp = client.post(REQUESTS, headers=headers, json={"title": "Campaign"})
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreatePageNotice:
    def test_requires_maintainer(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES, headers=auth_headers(normal_user), json=_page_payload()
        )
        assert resp.status_code == 403

    def test_requires_auth(self, client: TestClient):
        assert client.post(NOTICES, json=_page_payload()).status_code == 401

    def test_admin_creates_approved_page_notice(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES, headers=auth_headers(admin_user), json=_page_payload()
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "approved"
        assert body["scopes"] == ["centers"]
        assert body["approved_by_id"] == str(admin_user.id)
        assert len(body["translations"]) == 1
        assert body["translations"][0]["language"] == "en"

    def test_maintainer_creates_with_multiple_languages(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        maintainer = make_user("m1", UserRole.MAINTAINER)
        resp = client.post(
            NOTICES,
            headers=auth_headers(maintainer),
            json=_page_payload(
                scopes=["all"],
                translations=[
                    _translation("en", "English copy"),
                    _translation("es", "Texto en espanol"),
                ],
            ),
        )
        assert resp.status_code == 201, resp.text
        langs = {t["language"] for t in resp.json()["translations"]}
        assert langs == {"en", "es"}

    def test_empty_translations_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(translations=[]),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "TRANSLATIONS_REQUIRED"

    def test_duplicate_language_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(
                translations=[_translation("en", "one"), _translation("EN", "two")]
            ),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "DUPLICATE_LANGUAGE"

    def test_both_modes_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(admin_user)
        resource = _create_resource(client, h)
        payload = _page_payload()
        payload["target_type"] = "resource"
        payload["target_id"] = resource["id"]
        resp = client.post(NOTICES, headers=h, json=payload)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_NOTICE_MODE"

    def test_neither_mode_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(scopes=[]),
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_NOTICE_MODE"

    def test_partial_target_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        payload = _page_payload(scopes=[])
        payload["target_type"] = "resource"
        resp = client.post(NOTICES, headers=auth_headers(admin_user), json=payload)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_NOTICE_MODE"

    def test_blank_action_url_collapses(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(
                translations=[_translation(action_label=None, action_url="   ")]
            ),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["translations"][0]["action_url"] is None

    def test_explicit_null_title_allowed(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(
                translations=[{"language": "en", "message": "hi", "title": None}]
            ),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["translations"][0]["title"] is None

    def test_action_link_pairing_enforced(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(
                translations=[_translation(action_label="Join", action_url=None)]
            ),
        )
        assert resp.status_code == 422

    def test_action_url_scheme_validated(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(
                translations=[_translation(action_label="Join", action_url="ftp://bad")]
            ),
        )
        assert resp.status_code == 422

    def test_blank_optional_fields_collapse(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json=_page_payload(translations=[_translation(title="   ")]),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["translations"][0]["title"] is None


class TestCreateEntityNoticeDirectly:
    def test_admin_creates_entity_notice(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(admin_user)
        center = _create_center(client, h)
        resp = client.post(
            NOTICES,
            headers=h,
            json={
                "severity": "warning",
                "target_type": "collection_center",
                "target_id": center["id"],
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "approved"
        assert body["target_type"] == "collection_center"
        assert body["scopes"] == []

    def test_unknown_target_id_404(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            NOTICES,
            headers=auth_headers(admin_user),
            json={
                "target_type": "resource",
                "target_id": "00000000-0000-0000-0000-000000000000",
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 404


class TestRequestEntityNotice:
    def test_requires_auth(self, client: TestClient):
        resp = client.post(
            f"{NOTICES}/request",
            json={
                "target_type": "resource",
                "target_id": "00000000-0000-0000-0000-000000000000",
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 401

    def test_owner_request_is_pending(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        resp = client.post(
            f"{NOTICES}/request",
            headers=h,
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "pending"
        assert body["approved_by_id"] is None
        assert body["requested_by_id"] == str(normal_user.id)

    def test_non_owner_forbidden(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("owner", UserRole.USER)
        other = make_user("other", UserRole.USER)
        resource = _create_resource(client, auth_headers(owner))
        resp = client.post(
            f"{NOTICES}/request",
            headers=auth_headers(other),
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_ENTITY_OWNER"

    def test_maintainer_request_auto_approved(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("owner2", UserRole.USER)
        maintainer = make_user("maint", UserRole.MAINTAINER)
        resource = _create_resource(client, auth_headers(owner))
        resp = client.post(
            f"{NOTICES}/request",
            headers=auth_headers(maintainer),
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "approved"

    def test_request_owner_of_request_entity(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        request = _create_request(client, h)
        resp = client.post(
            f"{NOTICES}/request",
            headers=h,
            json={
                "target_type": "request",
                "target_id": request["id"],
                "translations": [_translation()],
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "pending"


class TestModeration:
    def _pending(
        self, client: TestClient, owner: User, auth_headers: AuthHeaders
    ) -> dict[str, object]:
        h = auth_headers(owner)
        resource = _create_resource(client, h)
        resp = client.post(
            f"{NOTICES}/request",
            headers=h,
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        )
        return resp.json()

    def test_approve_requires_maintainer(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        notice = self._pending(client, normal_user, auth_headers)
        resp = client.post(
            f"{NOTICES}/{notice['id']}/approve", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 403

    def test_maintainer_approves(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("o3", UserRole.USER)
        maintainer = make_user("m3", UserRole.MAINTAINER)
        notice = self._pending(client, owner, auth_headers)
        resp = client.post(
            f"{NOTICES}/{notice['id']}/approve", headers=auth_headers(maintainer)
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "approved"

    def test_approve_non_pending_conflict(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("o4", UserRole.USER)
        admin = make_user("a4", UserRole.ADMIN)
        notice = self._pending(client, owner, auth_headers)
        client.post(f"{NOTICES}/{notice['id']}/approve", headers=auth_headers(admin))
        resp = client.post(
            f"{NOTICES}/{notice['id']}/approve", headers=auth_headers(admin)
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "NOTICE_NOT_PENDING"

    def test_maintainer_declines_with_reason(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("o5", UserRole.USER)
        maintainer = make_user("m5", UserRole.MAINTAINER)
        notice = self._pending(client, owner, auth_headers)
        resp = client.post(
            f"{NOTICES}/{notice['id']}/decline",
            headers=auth_headers(maintainer),
            json={"reason": "Not relevant"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "declined"
        assert body["decline_reason"] == "Not relevant"

    def test_decline_non_pending_conflict(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("o6", UserRole.USER)
        admin = make_user("a6", UserRole.ADMIN)
        notice = self._pending(client, owner, auth_headers)
        client.post(f"{NOTICES}/{notice['id']}/decline", headers=auth_headers(admin))
        resp = client.post(
            f"{NOTICES}/{notice['id']}/decline", headers=auth_headers(admin)
        )
        assert resp.status_code == 409

    def test_approve_missing_notice_404(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        resp = client.post(
            f"{NOTICES}/00000000-0000-0000-0000-000000000000/approve",
            headers=auth_headers(admin_user),
        )
        assert resp.status_code == 404


class TestToggleUpdateDelete:
    def _approved_page(
        self, client: TestClient, admin: User, auth_headers: AuthHeaders
    ) -> dict[str, object]:
        return client.post(
            NOTICES, headers=auth_headers(admin), json=_page_payload()
        ).json()

    def test_toggle_disables_and_hides(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        notice = self._approved_page(client, admin_user, auth_headers)
        resp = client.post(
            f"{NOTICES}/{notice['id']}/toggle", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 200
        assert resp.json()["enabled"] is False
        public = client.get(NOTICES, params={"scope": "centers"})
        assert all(n["id"] != notice["id"] for n in public.json())

    def test_toggle_requires_maintainer(
        self,
        client: TestClient,
        admin_user: User,
        normal_user: User,
        auth_headers: AuthHeaders,
    ):
        notice = self._approved_page(client, admin_user, auth_headers)
        resp = client.post(
            f"{NOTICES}/{notice['id']}/toggle", headers=auth_headers(normal_user)
        )
        assert resp.status_code == 403

    def test_update_severity_and_translations(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        notice = self._approved_page(client, admin_user, auth_headers)
        resp = client.patch(
            f"{NOTICES}/{notice['id']}",
            headers=auth_headers(admin_user),
            json={
                "severity": "critical",
                "scopes": ["home", "centers"],
                "translations": [_translation("es", "Solo espanol")],
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["severity"] == "critical"
        assert sorted(body["scopes"]) == ["centers", "home"]
        assert [t["language"] for t in body["translations"]] == ["es"]

    def test_update_translations_only(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        notice = self._approved_page(client, admin_user, auth_headers)
        resp = client.patch(
            f"{NOTICES}/{notice['id']}",
            headers=auth_headers(admin_user),
            json={"translations": [_translation("es", "Solo cambio texto")]},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["severity"] == "info"
        assert [t["language"] for t in body["translations"]] == ["es"]

    def test_update_scopes_on_entity_notice_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(admin_user)
        center = _create_center(client, h)
        notice = client.post(
            NOTICES,
            headers=h,
            json={
                "target_type": "collection_center",
                "target_id": center["id"],
                "translations": [_translation()],
            },
        ).json()
        resp = client.patch(
            f"{NOTICES}/{notice['id']}", headers=h, json={"scopes": ["home"]}
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "INVALID_NOTICE_MODE"

    def test_update_empty_scopes_rejected(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        notice = self._approved_page(client, admin_user, auth_headers)
        resp = client.patch(
            f"{NOTICES}/{notice['id']}",
            headers=auth_headers(admin_user),
            json={"scopes": []},
        )
        assert resp.status_code == 422

    def test_requester_cancels_own_pending(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        notice = client.post(
            f"{NOTICES}/request",
            headers=h,
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        ).json()
        resp = client.delete(f"{NOTICES}/{notice['id']}", headers=h)
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_non_owner_cannot_delete(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("o7", UserRole.USER)
        other = make_user("ot7", UserRole.USER)
        resource = _create_resource(client, auth_headers(owner))
        notice = client.post(
            f"{NOTICES}/request",
            headers=auth_headers(owner),
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        ).json()
        resp = client.delete(f"{NOTICES}/{notice['id']}", headers=auth_headers(other))
        assert resp.status_code == 403

    def test_maintainer_can_delete_any(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        notice = self._approved_page(client, admin_user, auth_headers)
        resp = client.delete(
            f"{NOTICES}/{notice['id']}", headers=auth_headers(admin_user)
        )
        assert resp.status_code == 200


class TestPublicAndManageListing:
    def test_public_scope_includes_all_and_excludes_others(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(admin_user)
        client.post(NOTICES, headers=h, json=_page_payload(scopes=["centers"]))
        client.post(NOTICES, headers=h, json=_page_payload(scopes=["all"]))
        client.post(NOTICES, headers=h, json=_page_payload(scopes=["home"]))
        centers = client.get(NOTICES, params={"scope": "centers"}).json()
        scopes_seen = [n["scopes"] for n in centers]
        assert ["centers"] in scopes_seen
        assert ["all"] in scopes_seen
        assert ["home"] not in scopes_seen

    def test_public_default_returns_page_notices_only(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(admin_user)
        center = _create_center(client, h)
        client.post(NOTICES, headers=h, json=_page_payload(scopes=["home"]))
        client.post(
            NOTICES,
            headers=h,
            json={
                "target_type": "collection_center",
                "target_id": center["id"],
                "translations": [_translation()],
            },
        )
        body = client.get(NOTICES).json()
        assert all(n["target_type"] is None for n in body)
        assert len(body) == 1

    def test_public_entity_filter(
        self, client: TestClient, admin_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(admin_user)
        center = _create_center(client, h)
        client.post(
            NOTICES,
            headers=h,
            json={
                "target_type": "collection_center",
                "target_id": center["id"],
                "translations": [_translation()],
            },
        )
        body = client.get(
            NOTICES,
            params={"target_type": "collection_center", "target_id": center["id"]},
        ).json()
        assert len(body) == 1
        assert body[0]["target_id"] == center["id"]

    def test_public_excludes_pending(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        resource = _create_resource(client, h)
        client.post(
            f"{NOTICES}/request",
            headers=h,
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        )
        body = client.get(
            NOTICES,
            params={"target_type": "resource", "target_id": resource["id"]},
        ).json()
        assert body == []

    def test_manage_requires_maintainer(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        assert client.get(f"{NOTICES}/manage").status_code == 401
        resp = client.get(f"{NOTICES}/manage", headers=auth_headers(normal_user))
        assert resp.status_code == 403

    def test_manage_lists_all_with_status_filter(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        owner = make_user("o8", UserRole.USER)
        admin = make_user("a8", UserRole.ADMIN)
        h = auth_headers(admin)
        client.post(NOTICES, headers=h, json=_page_payload())
        resource = _create_resource(client, auth_headers(owner))
        client.post(
            f"{NOTICES}/request",
            headers=auth_headers(owner),
            json={
                "target_type": "resource",
                "target_id": resource["id"],
                "translations": [_translation()],
            },
        )
        all_notices = client.get(f"{NOTICES}/manage", headers=h).json()
        assert len(all_notices) == 2
        pending = client.get(
            f"{NOTICES}/manage", headers=h, params={"status": "pending"}
        ).json()
        assert len(pending) == 1
        assert pending[0]["status"] == "pending"
