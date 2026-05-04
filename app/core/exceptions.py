class ChemIntelError(Exception):
    """Base application error."""


class AuthenticationError(ChemIntelError):
    """Authentication failure."""


class AuthorizationError(ChemIntelError):
    """Authorization failure."""


class NotFoundError(ChemIntelError):
    """Entity not found."""
