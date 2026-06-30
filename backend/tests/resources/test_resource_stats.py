"""Tests for the per-Resource requests-vs-claims stats endpoints."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.users.models import User

RESOURCES = "/api/v1/resources"
REQUESTS = "/api/v1/requests"
CONTRIB = "/api/v1/contributions"

AuthHeaders = Callable[[User], dict[str, str]]
MakeUser = Callable[..., User]


def _resource(client: TestClient, h: dict[str, str], name: str = "Ferula") -> str:
    resp = client.post(
        RESOURCES,
        headers=h,
        json={"name": name, "source_url": "https://example.com/p.stl"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _request_item(
    client: TestClient, h: dict[str, str], resource_id: str, qty: int = 10
) -> str:
    resp = client.post(
        REQUESTS,
        headers=h,
        json={
            "title": "Campaign",
            "items": [{"resource_id": resource_id, "quantity": qty}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["items"][0]["id"]


def _claim(client: TestClient, h: dict[str, str], item_id: str, qty: int = 2) -> None:
    resp = client.post(
        CONTRIB,
        headers=h,
        json={"request_item_id": item_id, "quantity": qty},
    )
    assert resp.status_code == 201, resp.text


class TestResourceStats:
    def test_zero_when_no_activity(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        rid = _resource(client, auth_headers(normal_user))
        resp = client.get(f"{RESOURCES}/{rid}/stats")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body == {
            "resource_id": rid,
            "request_count": 0,
            "claim_count": 0,
        }

    def test_counts_open_request_and_active_claim(
        self,
        client: TestClient,
        normal_user: User,
        make_user: MakeUser,
        auth_headers: AuthHeaders,
    ):
        requester_h = auth_headers(normal_user)
        rid = _resource(client, requester_h)

        # An open request item bumps the request count.
        item_id = _request_item(client, requester_h, rid)
        stats = client.get(f"{RESOURCES}/{rid}/stats").json()
        assert stats["request_count"] == 1
        assert stats["claim_count"] == 0

        # A maker claiming it bumps the claim count.
        maker = make_user("maker", role=normal_user.role)
        _claim(client, auth_headers(maker), item_id)
        stats = client.get(f"{RESOURCES}/{rid}/stats").json()
        assert stats["request_count"] == 1
        assert stats["claim_count"] == 1

    def test_list_stats_only_includes_active_resources(
        self, client: TestClient, normal_user: User, auth_headers: AuthHeaders
    ):
        h = auth_headers(normal_user)
        rid = _resource(client, h)
        _request_item(client, h, rid)
        # A second resource with no activity must be absent from the list.
        _resource(client, h, name="Idle")

        resp = client.get(f"{RESOURCES}/stats")
        assert resp.status_code == 200, resp.text
        by_id = {row["resource_id"]: row for row in resp.json()}
        assert by_id[rid]["request_count"] == 1

    def test_stats_404_for_missing_resource(self, client: TestClient):
        missing = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{RESOURCES}/{missing}/stats").status_code == 404
