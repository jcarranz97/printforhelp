"""Tests for local-dev directory seeding (bootstrap)."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.bootstrap import seed_dev_directory
from app.collection_centers.models import CollectionCenter
from app.organizations.models import Organization, OrganizationMembership
from app.users.constants import UserRole
from app.users.models import User

MakeUser = Callable[..., User]


def _seed_users(make_user: MakeUser) -> None:
    make_user("admin", UserRole.ADMIN)
    make_user("maintainer1", UserRole.MAINTAINER)
    make_user("user1", UserRole.USER)


class TestSeedDevDirectory:
    def test_seeds_org_and_centers(self, db: Session, make_user: MakeUser) -> None:
        _seed_users(make_user)
        seed_dev_directory(db)

        org = db.query(Organization).filter(Organization.name == "UCAB Lab 3D").one()
        assert org.verified is True
        assert org.verified_by_id is not None

        owner = (
            db.query(OrganizationMembership)
            .filter(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.role == "owner",
            )
            .one()
        )
        assert owner.active is True

        centers = db.query(CollectionCenter).all()
        assert len(centers) == 3
        verified = [c for c in centers if c.verified]
        assert len(verified) == 2
        org_owned = [c for c in centers if c.owner_organization_id == org.id]
        assert len(org_owned) == 1

    def test_is_idempotent(self, db: Session, make_user: MakeUser) -> None:
        _seed_users(make_user)
        seed_dev_directory(db)
        seed_dev_directory(db)

        assert db.query(Organization).count() == 1
        assert db.query(CollectionCenter).count() == 3
        assert db.query(OrganizationMembership).count() == 1

    def test_noop_without_seed_users(self, db: Session, make_user: MakeUser) -> None:
        # Only admin present; user1 / maintainer1 missing -> no seeding.
        make_user("admin", UserRole.ADMIN)
        seed_dev_directory(db)
        assert db.query(Organization).count() == 0
        assert db.query(CollectionCenter).count() == 0
