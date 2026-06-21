import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.auth import create_token, decode_token


def test_token_roundtrip():
    token = create_token(user_id=42)
    payload = decode_token(token)
    assert payload["sub"] == "42"


def test_token_contains_exp():
    token = create_token(user_id=1)
    payload = decode_token(token)
    assert "exp" in payload


def test_different_users_get_different_tokens():
    t1 = create_token(user_id=1)
    t2 = create_token(user_id=2)
    assert t1 != t2


def test_invalid_token_raises():
    import pytest
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        decode_token("invalid.token.here")
