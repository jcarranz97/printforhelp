"""Constants and error codes for the uploads domain."""

from enum import StrEnum

# Longest edge (px) an uploaded image is downscaled to before storage.
MAX_IMAGE_DIMENSION = 2000

# Allowlisted extensions for an uploaded model/source file. Stored as-is
# (no re-encoding), so the set is deliberately conservative: common 3D
# model formats plus archives makers bundle multi-part prints in.
ALLOWED_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        "stl",
        "3mf",
        "obj",
        "step",
        "stp",
        "gcode",
        "ply",
        "amf",
        "scad",
        "f3d",
        "zip",
        "7z",
        "rar",
    }
)

# Best-effort content type per extension (used by remote backends; the
# local static mount infers its own). Anything else falls back to a
# generic binary type.
FILE_CONTENT_TYPES: dict[str, str] = {
    "3mf": "model/3mf",
    "stl": "model/stl",
    "obj": "model/obj",
    "zip": "application/zip",
}
DEFAULT_FILE_CONTENT_TYPE = "application/octet-stream"


class ErrorCode(StrEnum):
    """Error codes raised by the uploads domain."""

    INVALID_IMAGE = "INVALID_IMAGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
