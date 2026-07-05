"""Registry of generic per-user flags (traits and capabilities).

A flag is a yes/no attribute attached to a user (stored in ``user_flags``).
This module is the single source of truth for which flags exist and, crucially,
**who is allowed to set each one**:

- ``TRAIT`` flags are **self-declared** personalization (e.g. "I am a maker").
  They must never grant access — treat them as cosmetic.
- ``CAPABILITY`` flags are **admin/maintainer-granted** authorization grants
  (e.g. "can add parts"). They are checked server-side via
  ``permissions.has_capability`` and can only be toggled through the admin path.

Adding a new flag is a one-line registry entry here (no migration): the
``user_flags`` table is generic. ``maker`` is wired end-to-end in v1; the
capability keys exist so the admin grant path is real and tested, but they are
not yet enforced on any endpoint (a documented follow-up).
"""

from dataclasses import dataclass
from enum import StrEnum


class FlagKey(StrEnum):
    """Known per-user flag keys."""

    MAKER = "maker"
    # Capability scaffolding — admin-granted; not yet enforced anywhere.
    CAN_ADD_PART = "can_add_part"
    CAN_ADD_CENTER = "can_add_center"
    CAN_ADD_REQUEST = "can_add_request"


class FlagCategory(StrEnum):
    """Trust category for a flag."""

    TRAIT = "trait"  # self-declared, cosmetic; never authorizes
    CAPABILITY = "capability"  # admin-granted; may authorize


class FlagSource(StrEnum):
    """How a flag value came to be set (provenance)."""

    SELF = "self"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass(frozen=True)
class FlagDef:
    """Metadata describing how a flag may be used and set."""

    category: FlagCategory
    self_assignable: bool
    prompt_on_login: bool


FLAG_REGISTRY: dict[FlagKey, FlagDef] = {
    FlagKey.MAKER: FlagDef(
        category=FlagCategory.TRAIT,
        self_assignable=True,
        prompt_on_login=True,
    ),
    FlagKey.CAN_ADD_PART: FlagDef(
        category=FlagCategory.CAPABILITY,
        self_assignable=False,
        prompt_on_login=False,
    ),
    FlagKey.CAN_ADD_CENTER: FlagDef(
        category=FlagCategory.CAPABILITY,
        self_assignable=False,
        prompt_on_login=False,
    ),
    FlagKey.CAN_ADD_REQUEST: FlagDef(
        category=FlagCategory.CAPABILITY,
        self_assignable=False,
        prompt_on_login=False,
    ),
}
