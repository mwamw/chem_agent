from datetime import timedelta

from app.core.security import create_jwt_token, decode_jwt_token, hash_password, verify_password


def test_password_hash_verification_roundtrip():
    password_hash = hash_password("correct-password")
    assert verify_password("correct-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_standard_jwt_claims_roundtrip():
    token, token_id, _ = create_jwt_token(
        subject="user_1",
        tenant_id="tenant_1",
        roles=["admin"],
        token_use="access",
        expires_delta=timedelta(days=3650),
    )
    payload = decode_jwt_token(token, expected_use="access")
    assert payload["sub"] == "user_1"
    assert payload["tenant_id"] == "tenant_1"
    assert payload["roles"] == ["admin"]
    assert payload["jti"] == token_id
    assert payload["iss"] == "chemintel-api"
    assert payload["aud"] == "chemintel-api"
