"""
Custom exception classes for the authentication system.

These exceptions are used throughout the application to signal specific
error conditions. Global exception handlers in main.py map these to
appropriate HTTP responses.
"""


class AuthenticationError(Exception):
    """
    Raised when authentication fails.

    This includes invalid credentials, missing tokens, or expired tokens.
    Maps to HTTP 401 Unauthorized.
    """

    pass


class InvalidTokenError(Exception):
    """
    Raised when a token is invalid, expired, or tampered with.

    This includes JWT signature validation failures, expired tokens,
    and malformed token structures.
    Maps to HTTP 401 Unauthorized.
    """

    pass


class WeakPasswordError(Exception):
    """
    Raised when a password doesn't meet strength requirements.

    This includes passwords that are too short, lack required character types,
    or fail other validation rules.
    Maps to HTTP 422 Unprocessable Entity.
    """

    pass


class EmailAlreadyExistsError(Exception):
    """
    Raised when attempting to register with an email that already exists.

    Maps to HTTP 409 Conflict.
    """

    pass


class InvalidResetTokenError(Exception):
    """
    Raised when a password reset token is invalid, expired, or already used.

    Maps to HTTP 400 Bad Request.
    """

    pass


class IncorrectPasswordError(Exception):
    """
    Raised when the current password provided for password change is incorrect.

    Maps to HTTP 400 Bad Request.
    """

    pass
