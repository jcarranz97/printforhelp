"""Startup bootstrap: default admin (FR-007) and local dev seed data."""

import logging
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.activity import service as activity_service
from app.activity.constants import ActivityAction, EntityType
from app.activity.models import Comment
from app.auth.utils import hash_password
from app.collection_centers.constants import CollectionCenterStatus
from app.collection_centers.models import CollectionCenter
from app.config import settings
from app.database import SessionLocal
from app.organizations.constants import OrganizationRole, OrganizationStatus
from app.organizations.models import Organization, OrganizationMembership
from app.shipments.constants import ShipmentStatus
from app.shipments.models import Shipment
from app.users import service as users_service
from app.users.constants import Locale, UserRole
from app.users.models import User

logger = logging.getLogger(__name__)


def _ensure_user(db: Session, username: str, password: str, role: UserRole) -> bool:
    """Create a user if the username is free. Returns True if created."""
    existing = db.query(User).filter(User.username == username).first()
    if existing is not None:
        return False
    db.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            preferred_locale=Locale.ES,
        )
    )
    return True


def bootstrap_admin(db: Session) -> None:
    """Create the default admin account on first run (FR-007)."""
    created = _ensure_user(
        db,
        settings.DEFAULT_ADMIN_USERNAME,
        settings.DEFAULT_ADMIN_PASSWORD,
        UserRole.ADMIN,
    )
    if created:
        db.commit()
        logger.info("Bootstrapped default admin '%s'", settings.DEFAULT_ADMIN_USERNAME)


def seed_dev_data(db: Session) -> None:
    """Seed a maintainer and a regular user for local development."""
    created_any = False
    created_any |= _ensure_user(
        db, "maintainer1", settings.SEED_DEV_PASSWORD, UserRole.MAINTAINER
    )
    created_any |= _ensure_user(db, "user1", settings.SEED_DEV_PASSWORD, UserRole.USER)
    if created_any:
        db.commit()
        logger.info("Seeded local development accounts (maintainer1, user1)")


def _get_user(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def _ensure_organization(
    db: Session,
    *,
    name: str,
    contact: str,
    country: str,
    registered_by_id: uuid.UUID,
    owner_user_id: uuid.UUID,
    verified_by_id: uuid.UUID,
    description: str | None = None,
    website: str | None = None,
) -> Organization | None:
    """Create a verified organization + owner membership if name is free.

    Returns the newly created organization, or ``None`` if it already
    existed (so callers can skip dependent seeding).
    """
    existing = db.query(Organization).filter(Organization.name == name).first()
    if existing is not None:
        return None
    org = Organization(
        name=name,
        description=description,
        contact=contact,
        website=website,
        country=country,
        verified=True,
        registered_by_id=registered_by_id,
        verified_by_id=verified_by_id,
        status=OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    db.add(
        OrganizationMembership(
            organization_id=org.id,
            user_id=owner_user_id,
            role=OrganizationRole.OWNER,
            invited_by_id=owner_user_id,
        )
    )
    return org


def _ensure_collection_center(
    db: Session,
    *,
    name: str,
    address: str,
    country: str,
    city: str,
    contact: str,
    registered_by_id: uuid.UUID,
    owner_user_id: uuid.UUID | None = None,
    owner_organization_id: uuid.UUID | None = None,
    verified: bool = False,
    verified_by_id: uuid.UUID | None = None,
    opening_hours: str | None = None,
    notes: str | None = None,
) -> bool:
    """Create a collection center keyed by name. Returns True if created."""
    existing = db.query(CollectionCenter).filter(CollectionCenter.name == name).first()
    if existing is not None:
        return False
    db.add(
        CollectionCenter(
            name=name,
            address=address,
            country=country,
            city=city,
            contact=contact,
            opening_hours=opening_hours,
            notes=notes,
            verified=verified,
            verified_by_id=verified_by_id,
            registered_by_id=registered_by_id,
            owner_user_id=owner_user_id,
            owner_organization_id=owner_organization_id,
            status=CollectionCenterStatus.ACTIVE,
        )
    )
    return True


def seed_dev_directory(db: Session) -> None:
    """Seed a sample directory of organizations and centers (dev only).

    Idempotent: every entity is keyed by name, so re-running on startup
    never creates duplicates. Gives the public read endpoints (and the
    Phase 3 frontend) realistic data — a verified org with an org-owned
    center, a user-owned verified center, and one unverified center to
    exercise the "No verificado" badge.
    """
    admin = _get_user(db, settings.DEFAULT_ADMIN_USERNAME)
    user1 = _get_user(db, "user1")
    maintainer1 = _get_user(db, "maintainer1")
    if admin is None or user1 is None or maintainer1 is None:
        return

    org = _ensure_organization(
        db,
        name="UCAB Lab 3D",
        description="Laboratorio de impresión 3D de la UCAB en Caracas.",
        contact="fablab@ucab.edu.ve",
        website="https://lab.ucab.edu.ve",
        country="VE",
        registered_by_id=user1.id,
        owner_user_id=user1.id,
        verified_by_id=admin.id,
    )
    if org is not None:
        db.flush()

    existing_org = (
        db.query(Organization).filter(Organization.name == "UCAB Lab 3D").first()
    )

    created_any = org is not None
    if existing_org is not None:
        created_any |= _ensure_collection_center(
            db,
            name="UCAB Lab — Caracas",
            address="Av. Teherán, Montalbán, Caracas",
            country="VE",
            city="Caracas",
            contact="+58-212-407-4400 / fablab@ucab.edu.ve",
            opening_hours="Lun-Vie 9-17",
            notes="Entrega por la puerta principal del edificio Mendoza.",
            registered_by_id=user1.id,
            owner_organization_id=existing_org.id,
            verified=True,
            verified_by_id=admin.id,
        )

    created_any |= _ensure_collection_center(
        db,
        name="Refugio Maker Valencia",
        address="Calle 130, Urb. Prebo, Valencia",
        country="VE",
        city="Valencia",
        contact="+58-241-555-0102",
        opening_hours="Sáb 10-14",
        registered_by_id=user1.id,
        owner_user_id=user1.id,
        verified=True,
        verified_by_id=admin.id,
    )

    created_any |= _ensure_collection_center(
        db,
        name="Centro Maker Maracaibo (sin verificar)",
        address="Av. 5 de Julio, Maracaibo",
        country="VE",
        city="Maracaibo",
        contact="+58-261-555-0199",
        registered_by_id=maintainer1.id,
        owner_user_id=maintainer1.id,
        verified=False,
    )

    if created_any:
        db.commit()
        logger.info("Seeded local development directory (orgs + centers)")


def _ensure_shipment(
    db: Session,
    *,
    collection_center_id: uuid.UUID,
    shipment_date: date,
    created_by_id: uuid.UUID,
    status: ShipmentStatus = ShipmentStatus.RECEIVING,
    destination: str | None = None,
    description: str | None = None,
) -> tuple[Shipment, bool]:
    """Create a shipment keyed by (center, date). Returns (shipment, created).

    Records a ``created`` activity event so the public timeline mirrors
    what the real endpoint produces (FR-127 / FR-133).
    """
    existing = (
        db.query(Shipment)
        .filter(
            Shipment.collection_center_id == collection_center_id,
            Shipment.shipment_date == shipment_date,
        )
        .first()
    )
    if existing is not None:
        return existing, False
    shipment = Shipment(
        collection_center_id=collection_center_id,
        shipment_date=shipment_date,
        status=status,
        destination=destination,
        description=description,
        created_by_id=created_by_id,
    )
    db.add(shipment)
    db.flush()
    activity_service.record(
        db,
        entity_type=EntityType.SHIPMENT,
        entity_id=shipment.id,
        actor_user_id=created_by_id,
        action=ActivityAction.CREATED,
        changes={"shipment_date": shipment_date.isoformat(), "status": status.value},
    )
    return shipment, True


def _ensure_comment(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: uuid.UUID,
    author_user_id: uuid.UUID,
    body: str,
) -> bool:
    """Create a comment keyed by (entity, body). Returns True if created.

    Records a ``commented`` activity event, like the real endpoint
    (FR-131 / FR-133).
    """
    existing = (
        db.query(Comment)
        .filter(
            Comment.entity_type == entity_type.value,
            Comment.entity_id == entity_id,
            Comment.body == body,
        )
        .first()
    )
    if existing is not None:
        return False
    comment = Comment(
        entity_type=entity_type.value,
        entity_id=entity_id,
        author_user_id=author_user_id,
        body=body,
    )
    db.add(comment)
    db.flush()
    activity_service.record(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=author_user_id,
        action=ActivityAction.COMMENTED,
        changes={"comment_id": str(comment.id)},
    )
    return True


def seed_dev_shipments_and_comments(db: Session) -> None:
    """Seed sample shipments and Markdown comments on seeded centers.

    Idempotent: shipments are keyed by (center, date) and comments by
    (entity, body), so re-running on startup never duplicates. Gives the
    Phase 3 frontend realistic shipment lists and community feeds, on both
    a center and one of its shipments.
    """
    admin = _get_user(db, settings.DEFAULT_ADMIN_USERNAME)
    user1 = _get_user(db, "user1")
    maintainer1 = _get_user(db, "maintainer1")
    if admin is None or user1 is None or maintainer1 is None:
        return

    caracas = (
        db.query(CollectionCenter)
        .filter(CollectionCenter.name == "UCAB Lab — Caracas")
        .first()
    )
    valencia = (
        db.query(CollectionCenter)
        .filter(CollectionCenter.name == "Refugio Maker Valencia")
        .first()
    )

    created_any = False

    if caracas is not None:
        upcoming, made = _ensure_shipment(
            db,
            collection_center_id=caracas.id,
            shipment_date=date(2026, 7, 15),
            created_by_id=user1.id,
            destination="Caracas → Mérida (zona del sismo)",
            description=(
                "Primer despacho del lote. Trae tus **férulas** antes del "
                "14 de julio. El camión sale a las 8am."
            ),
        )
        created_any |= made
        created_any |= _ensure_shipment(
            db,
            collection_center_id=caracas.id,
            shipment_date=date(2026, 8, 5),
            created_by_id=user1.id,
            destination="Caracas → Trujillo",
            description="Segundo lote. Aún _recibiendo_ piezas.",
        )[1]
        created_any |= _ensure_shipment(
            db,
            collection_center_id=caracas.id,
            shipment_date=date(2026, 6, 20),
            created_by_id=user1.id,
            status=ShipmentStatus.CLOSED,
            destination="Caracas → Barinas (despachado)",
            description="¡Enviadas 48 férulas! Gracias a toda la comunidad.",
        )[1]
        created_any |= _ensure_comment(
            db,
            entity_type=EntityType.COLLECTION_CENTER,
            entity_id=caracas.id,
            author_user_id=maintainer1.id,
            body=(
                "Este centro está **verificado**. Coordinen sus entregas por "
                "el grupo de Discord 🙌"
            ),
        )
        created_any |= _ensure_comment(
            db,
            entity_type=EntityType.SHIPMENT,
            entity_id=upcoming.id,
            author_user_id=user1.id,
            body="Llevaré **12 férulas** talla M el lunes por la mañana.",
        )

    if valencia is not None:
        created_any |= _ensure_shipment(
            db,
            collection_center_id=valencia.id,
            shipment_date=date(2026, 7, 28),
            created_by_id=user1.id,
            destination="Valencia → San Cristóbal",
            description=(
                "Recogemos los sábados. Avisa si necesitas que pasemos a buscar."
            ),
        )[1]
        created_any |= _ensure_comment(
            db,
            entity_type=EntityType.COLLECTION_CENTER,
            entity_id=valencia.id,
            author_user_id=user1.id,
            body="¿Aceptan también soportes de mano? Tengo el modelo listo.",
        )

    if created_any:
        db.commit()
        logger.info("Seeded local development shipments and comments")


def run_startup_bootstrap() -> None:
    """Run admin bootstrap and (optionally) dev seeding in one session."""
    db = SessionLocal()
    try:
        bootstrap_admin(db)
        # System account that owns guest-submitted assets (open API).
        users_service.get_or_create_anonymous_user(db)
        if settings.SEED_DEV_DATA:
            seed_dev_data(db)
            seed_dev_directory(db)
            seed_dev_shipments_and_comments(db)
    finally:
        db.close()
