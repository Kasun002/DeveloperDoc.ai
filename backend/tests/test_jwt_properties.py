"""
Property-based tests for JWT security.

Feature: user-authentication-backend

This module tests the following properties:
- Property 9: JWT token structure - tokens contain user_id, exp, iat claims
- Property 18: JWT signature validation - tampered tokens are rejected
- Property 19: JWT algorithm enforcement - tokens use HS256/RS256

Requirements validated: 2.3, 7.3, 7.2, 7.4, 7.1
"""

from datetime import timedelta
from typing import Any, Dict

import pytest
from app.core.config import settings
from app.core.security import create_jwt_token, decode_jwt_token
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st
from jose import jwt

# ============================================================================
# Property 9: JWT token structure
# ============================================================================


@given(
    user_id=st.integers(min_value=1, max_value=1000000),
    expires_minutes=st.integers(min_value=1, max_value=60),
)
@hypothesis_settings(max_examples=100)
@pytest.mark.property_test
def test_property_9_jwt_token_structure(user_id: int, expires_minutes: int):
    """
    Property 9: JWT token structure - tokens contain user_id, exp, iat claims.

    **Validates: Requirements 2.3, 7.3**

    For any user_id and expiration time, a generated JWT token should contain:
    - user_id claim
    - exp (expiration) claim
    - iat (issued-at) claim
    """
    # Arrange
    data = {"user_id": user_id}
    expires_delta = timedelta(minutes=expires_minutes)

    # Act
    token = create_jwt_token(data, expires_delta)
    payload = decode_jwt_token(token)

    # Assert - token must contain all required claims
    assert "user_id" in payload, "Token must contain user_id claim"
    assert "exp" in payload, "Token must contain exp (expiration) claim"
    assert "iat" in payload, "Token must contain iat (issued-at) claim"

    # Verify the user_id matches
    assert payload["user_id"] == user_id, "Token user_id must match input"

    # Verify exp and iat are present and valid (exp > iat)
    assert payload["exp"] > payload["iat"], "Expiration must be after issued-at"


# ============================================================================
# Property 18: JWT signature validation
# ============================================================================


@given(
    user_id=st.integers(min_value=1, max_value=1000000),
    tamper_position=st.integers(min_value=0, max_value=50),
)
@hypothesis_settings(max_examples=100)
@pytest.mark.property_test
def test_property_18_jwt_signature_validation(user_id: int, tamper_position: int):
    """
    Property 18: JWT signature validation - tampered tokens are rejected.

    **Validates: Requirements 7.2, 7.4**

    For any valid JWT token, tampering with the token content should cause
    signature validation to fail and the token to be rejected.
    """
    # Arrange
    data = {"user_id": user_id}
    expires_delta = timedelta(minutes=30)

    # Act - create a valid token
    token = create_jwt_token(data, expires_delta)

    # Tamper with the token by modifying a character
    # JWT tokens have format: header.payload.signature
    token_parts = token.split(".")

    # Only tamper if we have a valid token structure
    if len(token_parts) == 3 and len(token_parts[1]) > tamper_position:
        # Tamper with the payload section
        payload_part = token_parts[1]
        tampered_char_list = list(payload_part)

        # Change a character (flip between 'A' and 'B' to ensure change)
        original_char = tampered_char_list[tamper_position % len(payload_part)]
        tampered_char_list[tamper_position % len(payload_part)] = (
            "B" if original_char != "B" else "A"
        )

        tampered_payload = "".join(tampered_char_list)
        tampered_token = f"{token_parts[0]}.{tampered_payload}.{token_parts[2]}"

        # Assert - tampered token should be rejected
        with pytest.raises(Exception):  # JWTError or similar
            decode_jwt_token(tampered_token)


@given(user_id=st.integers(min_value=1, max_value=1000000))
@hypothesis_settings(max_examples=100)
@pytest.mark.property_test
def test_property_18_jwt_wrong_secret_rejected(user_id: int):
    """
    Property 18: JWT signature validation - tokens signed with wrong secret are rejected.

    **Validates: Requirements 7.2, 7.4**

    For any JWT token signed with a different secret key, the token should be
    rejected during validation.
    """
    # Arrange
    data = {"user_id": user_id}
    expires_delta = timedelta(minutes=30)

    # Act - create a token with a different secret
    wrong_secret_token = jwt.encode(
        {"user_id": user_id, "exp": (timedelta(minutes=30)).total_seconds(), "iat": 0},
        "wrong_secret_key_12345",
        algorithm=settings.jwt_algorithm,
    )

    # Assert - token with wrong secret should be rejected
    with pytest.raises(Exception):  # JWTError or similar
        decode_jwt_token(wrong_secret_token)


# ============================================================================
# Property 19: JWT algorithm enforcement
# ============================================================================


@given(user_id=st.integers(min_value=1, max_value=1000000))
@hypothesis_settings(max_examples=100)
@pytest.mark.property_test
def test_property_19_jwt_algorithm_enforcement(user_id: int):
    """
    Property 19: JWT algorithm enforcement - tokens use HS256/RS256.

    **Validates: Requirements 7.1**

    For any generated JWT token, the token header should specify HS256 or RS256
    as the signing algorithm (as configured in settings).
    """
    # Arrange
    data = {"user_id": user_id}
    expires_delta = timedelta(minutes=30)

    # Act
    token = create_jwt_token(data, expires_delta)

    # Decode the token header without verification to check algorithm
    header = jwt.get_unverified_header(token)

    # Assert - algorithm must be HS256 or RS256
    assert "alg" in header, "Token header must contain algorithm field"
    assert header["alg"] in [
        "HS256",
        "RS256",
    ], f"Token algorithm must be HS256 or RS256, got {header['alg']}"

    # Verify it matches the configured algorithm
    assert (
        header["alg"] == settings.jwt_algorithm
    ), f"Token algorithm must match configured algorithm {settings.jwt_algorithm}"
