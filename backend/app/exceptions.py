"""Domain exceptions for Camera Monitor."""


class CameraNotFoundError(Exception):
    """Raised when a requested camera does not exist."""


class DuplicateIpError(Exception):
    """Raised when a camera IP address already exists."""
