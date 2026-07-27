"""HTTP Bearer auth dependency regresyon testleri."""

import os
import unittest

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.infrastructure.security.jwt_service import create_access_token, create_stream_token
from src.presentation.api.dependencies import get_current_user


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class AuthDependencyTests(unittest.TestCase):
    def test_requires_bearer_credentials(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user(None)

        self.assertEqual(context.exception.status_code, 401)

    def test_rejects_invalid_token(self):
        with self.assertRaises(HTTPException) as context:
            get_current_user(bearer("not-a-valid-token"))

        self.assertEqual(context.exception.status_code, 401)

    def test_rejects_stream_token_for_access_dependency(self):
        token = create_stream_token("viewer1", "viewer", camera_id=1)

        with self.assertRaises(HTTPException) as context:
            get_current_user(bearer(token))

        self.assertEqual(context.exception.status_code, 401)

    def test_accepts_access_token(self):
        token = create_access_token("viewer1", "viewer", expires_minutes=5)

        current_user = get_current_user(bearer(token))

        self.assertEqual(current_user["sub"], "viewer1")
        self.assertEqual(current_user["role"], "viewer")
        self.assertEqual(current_user["purpose"], "access")


if __name__ == "__main__":
    unittest.main()
