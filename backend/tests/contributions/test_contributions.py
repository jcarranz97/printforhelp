"""Tests for the Contribution lifecycle endpoints (Phase 4)."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.contributions.models import Contribution
from app.contributions.service import expire_stale_claims
from app.scheduled import expire_claims
from app.users.models import User

RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CENTERS = "/api/v1/collection-centers"
CONTRIB = "/api/v1/contributions"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _resource(client: TestClient, h: dict[str, str]) -> str:
    return client.post(
        RESOURCES,
        headers=h,
        json={"name": "Ferula", "source_url": "https://x.io/p.stl"},
    ).json()["id"]


def _request_item(
    client: TestClient, h: dict[str, str], resource_id: str, qty: int
) -> str:
    request = client.post(
        REQUESTS,
        headers=h,
        json={
            "title": "Campaign",
            "items": [{"resource_id": resource_id, "quantity": qty}],
        },
    ).json()
    return request["items"][0]["id"]


def _verified_center(
    client: TestClient,
    owner_h: dict[str, str],
    admin_h: dict[str, str],
    name: str = "Centro",
) -> str:
    cc = client.post(
        CENTERS,
        headers=owner_h,
        json={
            "name": name,
            "address": "Av. 1",
            "country": "VE",
            "city": "Caracas",
            "contact": "x@y.z",
        },
    ).json()
    client.post(f"{CENTERS}/{cc['id']}/verify", headers=admin_h)
    return cc["id"]


# Returns the parsed JSON contribution body (a dynamic shape) typed as
# Any so tests can read fields like ``id`` without casts.
def _claim(
    client: TestClient, h: dict[str, str], item_id: str, center_id: str, qty: int = 4
) -> dict[str, Any]:
    resp = client.post(
        CONTRIB,
        headers=h,
        json={
            "request_item_id": item_id,
            "collection_center_id": center_id,
            "quantity": qty,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestCreateContribution:
    def test_requires_auth(self, client: TestClient):
        assert client.post(CONTRIB, json={}).status_code == 401

    def test_center_must_be_verified(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        resource_id = _resource(client, h)
        item_id = _request_item(client, h, resource_id, 10)
        # Unverified center.
        cc = client.post(
            CENTERS,
            headers=h,
            json={
                "name": "Unverified",
                "address": "a",
                "country": "VE",
                "city": "C",
                "contact": "x@y.z",
            },
        ).json()
        resp = client.post(
            CONTRIB,
            headers=h,
            json={
                "request_item_id": item_id,
                "collection_center_id": cc["id"],
                "quantity": 2,
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CENTER_NOT_AVAILABLE"

    def test_cannot_claim_on_closed_item(
        self,
        client: TestClient,
        normal_user: User,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        h = auth_headers(normal_user)
        a = auth_headers(admin_user)
        resource_id = _resource(client, h)
        request = client.post(
            REQUESTS,
            headers=h,
            json={"title": "C", "items": [{"resource_id": resource_id, "quantity": 5}]},
        ).json()
        item_id = request["items"][0]["id"]
        center_id = _verified_center(client, h, a)
        client.post(f"{REQUESTS}/{request['id']}/close", headers=h, json={})
        resp = client.post(
            CONTRIB,
            headers=h,
            json={
                "request_item_id": item_id,
                "collection_center_id": center_id,
                "quantity": 2,
            },
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "REQUEST_ITEM_NOT_OPEN"


class TestOptionalCenter:
    def test_claim_without_center(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        maker = make_user("nc1")
        h = auth_headers(maker)
        resource_id = _resource(client, h)
        item_id = _request_item(client, h, resource_id, 10)
        resp = client.post(
            CONTRIB,
            headers=h,
            json={"request_item_id": item_id, "quantity": 2},
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["collection_center_id"] is None

    def test_deliver_requires_center(
        self, client: TestClient, make_user: MakeUser, auth_headers: AuthHeaders
    ):
        maker = make_user("nc2")
        h = auth_headers(maker)
        resource_id = _resource(client, h)
        item_id = _request_item(client, h, resource_id, 10)
        c = client.post(
            CONTRIB,
            headers=h,
            json={"request_item_id": item_id, "quantity": 2},
        ).json()
        client.post(f"{CONTRIB}/{c['id']}/mark-prepared", headers=h)
        resp = client.post(f"{CONTRIB}/{c['id']}/mark-delivered", headers=h)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CENTER_REQUIRED"

    def test_set_center_later_then_deliver(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("nc3")
        h = auth_headers(maker)
        resource_id = _resource(client, h)
        item_id = _request_item(client, h, resource_id, 10)
        # The maker owns the center, so delivery later auto-receives.
        center_id = _verified_center(client, h, auth_headers(admin_user))
        c = client.post(
            CONTRIB,
            headers=h,
            json={"request_item_id": item_id, "quantity": 2},
        ).json()
        assert c["collection_center_id"] is None
        client.post(f"{CONTRIB}/{c['id']}/mark-prepared", headers=h)
        upd = client.patch(
            f"{CONTRIB}/{c['id']}",
            headers=h,
            json={"collection_center_id": center_id},
        )
        assert upd.status_code == 200, upd.text
        assert upd.json()["collection_center_id"] == center_id
        delivered = client.post(f"{CONTRIB}/{c['id']}/mark-delivered", headers=h).json()
        assert delivered["status"] == "received"


class TestLifecycle:
    def test_full_flow_with_member_confirm(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("centerowner")
        maker = make_user("maker")
        oh, mh, ah = (
            auth_headers(owner),
            auth_headers(maker),
            auth_headers(admin_user),
        )
        resource_id = _resource(client, oh)
        item_id = _request_item(client, oh, resource_id, 10)
        center_id = _verified_center(client, oh, ah)

        c = _claim(client, mh, item_id, center_id, qty=4)
        assert c["status"] == "claimed"

        # Progress reflects the claim.
        detail = client.get(REQUESTS).json()
        assert detail  # campaign listed

        prepared = client.post(f"{CONTRIB}/{c['id']}/mark-prepared", headers=mh).json()
        assert prepared["status"] == "prepared"
        delivered = client.post(
            f"{CONTRIB}/{c['id']}/mark-delivered", headers=mh
        ).json()
        # Maker is not a center member -> stays delivered (no auto-receive).
        assert delivered["status"] == "delivered"
        assert delivered["auto_received"] is False

        # A stranger cannot confirm receipt.
        stranger = make_user("stranger")
        resp = client.post(
            f"{CONTRIB}/{c['id']}/confirm-received", headers=auth_headers(stranger)
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_RECEIVER"

        # The center owner (effective member) confirms.
        received = client.post(
            f"{CONTRIB}/{c['id']}/confirm-received", headers=oh
        ).json()
        assert received["status"] == "received"
        assert received["received_by_id"] == str(owner.id)

    def test_auto_receive_when_maker_is_member(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        # The maker owns the center, so delivery auto-receives (FR-126).
        maker = make_user("makerowner")
        mh, ah = auth_headers(maker), auth_headers(admin_user)
        resource_id = _resource(client, mh)
        item_id = _request_item(client, mh, resource_id, 10)
        center_id = _verified_center(client, mh, ah)
        c = _claim(client, mh, item_id, center_id, qty=3)
        client.post(f"{CONTRIB}/{c['id']}/mark-prepared", headers=mh)
        delivered = client.post(
            f"{CONTRIB}/{c['id']}/mark-delivered", headers=mh
        ).json()
        assert delivered["status"] == "received"
        assert delivered["auto_received"] is True
        assert delivered["received_by_id"] == str(maker.id)

    def test_only_maker_advances(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("m1")
        other = make_user("m2")
        resource_id = _resource(client, auth_headers(maker))
        item_id = _request_item(client, auth_headers(maker), resource_id, 10)
        center_id = _verified_center(
            client, auth_headers(maker), auth_headers(admin_user)
        )
        c = _claim(client, auth_headers(maker), item_id, center_id)
        resp = client.post(
            f"{CONTRIB}/{c['id']}/mark-prepared", headers=auth_headers(other)
        )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_THE_MAKER"

    def test_invalid_transition(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("m3")
        mh = auth_headers(maker)
        resource_id = _resource(client, mh)
        item_id = _request_item(client, mh, resource_id, 10)
        center_id = _verified_center(client, mh, auth_headers(admin_user))
        c = _claim(client, mh, item_id, center_id)
        # claimed -> delivered (skipping prepared) is invalid.
        resp = client.post(f"{CONTRIB}/{c['id']}/mark-delivered", headers=mh)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVALID_TRANSITION"


class TestEditReleaseAndProgress:
    def test_edit_locked_after_prepared(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("m4")
        mh = auth_headers(maker)
        resource_id = _resource(client, mh)
        item_id = _request_item(client, mh, resource_id, 10)
        center_id = _verified_center(client, mh, auth_headers(admin_user))
        c = _claim(client, mh, item_id, center_id, qty=2)
        edited = client.patch(
            f"{CONTRIB}/{c['id']}", headers=mh, json={"quantity": 5}
        ).json()
        assert edited["quantity"] == 5
        client.post(f"{CONTRIB}/{c['id']}/mark-prepared", headers=mh)
        resp = client.patch(f"{CONTRIB}/{c['id']}", headers=mh, json={"quantity": 9})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CONTRIBUTION_LOCKED"

    def test_release_and_me_listing(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("m5")
        mh = auth_headers(maker)
        resource_id = _resource(client, mh)
        item_id = _request_item(client, mh, resource_id, 10)
        center_id = _verified_center(client, mh, auth_headers(admin_user))
        c = _claim(client, mh, item_id, center_id)
        released = client.post(f"{CONTRIB}/{c['id']}/release", headers=mh).json()
        assert released["status"] == "released"
        assert released["released_reason"] == "manual"
        mine = client.get(CONTRIB + "/me", headers=mh).json()
        assert {x["id"] for x in mine} == {c["id"]}
        # The listing is enriched with Resource + Request context.
        assert mine[0]["resource_name"] == "Ferula"
        assert mine[0]["request_title"] == "Campaign"
        assert mine[0]["request_id"]
        assert mine[0]["resource_id"]
        only_released = client.get(
            CONTRIB + "/me", headers=mh, params={"status": "released"}
        ).json()
        assert len(only_released) == 1

    def test_progress_and_auto_fulfill(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("m6")
        mh, ah = auth_headers(maker), auth_headers(admin_user)
        resource_id = _resource(client, mh)
        request = client.post(
            REQUESTS,
            headers=mh,
            json={"title": "C", "items": [{"resource_id": resource_id, "quantity": 5}]},
        ).json()
        item_id = request["items"][0]["id"]
        center_id = _verified_center(client, mh, ah)
        c = _claim(client, mh, item_id, center_id, qty=5)

        prog = client.get(f"{REQUESTS}/{request['id']}").json()["items"][0]["progress"]
        assert prog["claimed_quantity"] == 5
        assert prog["remaining"] == 0

        client.post(f"{CONTRIB}/{c['id']}/mark-prepared", headers=mh)
        # Maker owns the center -> delivery auto-receives and fulfills the item.
        client.post(f"{CONTRIB}/{c['id']}/mark-delivered", headers=mh)
        detail = client.get(f"{REQUESTS}/{request['id']}").json()
        assert detail["items"][0]["status"] == "fulfilled"
        assert detail["items"][0]["progress"]["at_center_quantity"] == 5
        assert detail["status"] == "fulfilled"


class TestRemoveItemBlocked:
    def test_remove_item_with_active_contributions(
        self,
        client: TestClient,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        owner = make_user("ro")
        oh, ah = auth_headers(owner), auth_headers(admin_user)
        resource_id = _resource(client, oh)
        resource2 = _resource(client, oh)
        request = client.post(
            REQUESTS,
            headers=oh,
            json={
                "title": "C",
                "items": [
                    {"resource_id": resource_id, "quantity": 5},
                    {"resource_id": resource2, "quantity": 5},
                ],
            },
        ).json()
        item_id = request["items"][0]["id"]
        center_id = _verified_center(client, oh, ah)
        _claim(client, oh, item_id, center_id, qty=2)
        resp = client.delete(f"{REQUESTS}/{request['id']}/items/{item_id}", headers=oh)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ITEM_HAS_CONTRIBUTIONS"


class TestExpiry:
    def test_no_stale_claims_returns_zero(self, db: Session):
        assert expire_stale_claims(db) == 0

    def test_scheduled_entrypoint_runs(self, db: Session):
        # The runnable wrapper opens its own session and returns the count.
        assert expire_claims.run() == 0

    def test_expire_stale_claim(
        self,
        client: TestClient,
        db: Session,
        make_user: MakeUser,
        admin_user: User,
        auth_headers: AuthHeaders,
    ):
        maker = make_user("m7")
        mh = auth_headers(maker)
        resource_id = _resource(client, mh)
        item_id = _request_item(client, mh, resource_id, 10)
        center_id = _verified_center(client, mh, auth_headers(admin_user))
        c = _claim(client, mh, item_id, center_id)

        # Age the claim past the 14-day threshold.
        row = db.query(Contribution).filter(Contribution.id == uuid.UUID(c["id"])).one()
        row.claimed_at = datetime.now(UTC) - timedelta(days=20)
        db.commit()

        assert expire_stale_claims(db) == 1
        refreshed = client.get(CONTRIB + "/me", headers=mh).json()[0]
        assert refreshed["status"] == "released"
        assert refreshed["released_reason"] == "expired"
