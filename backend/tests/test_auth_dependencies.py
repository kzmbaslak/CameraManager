"""HTTP Bearer auth dependency regresyon testleri."""

import os
import unittest
from unittest.mock import patch

import bcrypt
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.infrastructure.security.jwt_service import create_access_token, create_stream_token
from src.domain.entities.user import User, UserRole
from src.presentation.api.schemas.auth_schema import ChangePasswordRequest
from src.presentation.api.dependencies import get_current_user
from src.presentation.api.routes import auth as auth_route


def bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class AuthDependencyTests(unittest.TestCase):
    def tearDown(self):
        auth_route._failed_logins.clear()

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

    def test_accepts_access_token_from_secure_cookie_fallback(self):
        token = create_access_token("operator1", "operator", expires_minutes=5)

        current_user = get_current_user(None, token)

        self.assertEqual(current_user["sub"], "operator1")
        self.assertEqual(current_user["role"], "operator")

    def test_secure_cookie_mode_sets_httponly_login_cookie(self):
        class Client:
            host = "10.0.0.10"

        class Request:
            client = Client()

        class UserRepo:
            def get_by_username(self, username):
                return User(
                    id=1,
                    username=username,
                    password_hash=bcrypt.hashpw(b"correct-password", bcrypt.gensalt()).decode("utf-8"),
                    role=UserRole.OPERATOR,
                    is_active=True,
                )

        previous = os.environ.get("AUTH_COOKIE_MODE")
        os.environ["AUTH_COOKIE_MODE"] = "secure"
        try:
            response = Response()
            with patch.object(auth_route, "write_audit_event"):
                auth_route.login(
                    auth_route.LoginRequest(username="operator1", password="correct-password"),
                    Request(),
                    response,
                    UserRepo(),
                )
        finally:
            if previous is None:
                os.environ.pop("AUTH_COOKIE_MODE", None)
            else:
                os.environ["AUTH_COOKIE_MODE"] = previous

        cookie_header = response.headers.get("set-cookie", "")
        self.assertIn("access_token=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)
        self.assertIn("Secure", cookie_header)
        self.assertIn("SameSite=strict", cookie_header)

    def test_logout_clears_cookie_without_requiring_current_user_dependency(self):
        class Client:
            host = "10.0.0.11"

        class Request:
            client = Client()
            headers = {}
            cookies = {}

        response = Response()
        with patch.object(auth_route, "write_audit_event") as audit:
            result = auth_route.logout(response, Request())

        cookie_header = response.headers.get("set-cookie", "")
        self.assertEqual(result["message"], "Oturum kapatildi.")
        self.assertIn("access_token=", cookie_header)
        self.assertIn("Max-Age=0", cookie_header)
        audit.assert_called_once()
        self.assertEqual(audit.call_args.args[0], "auth.logout")
        self.assertEqual(audit.call_args.args[1], "unknown")

    def test_failed_login_summary_redacts_keys_and_counts_active_window(self):
        class Client:
            host = "10.0.0.5"

        class Request:
            client = Client()

        auth_route._record_failed_login(Request(), "admin")
        auth_route._record_failed_login(Request(), "admin")

        summary = auth_route.failed_login_window_summary()

        self.assertEqual(summary["active_failed_login_key_count"], 1)
        self.assertEqual(summary["active_failed_login_attempt_count"], 2)
        self.assertEqual(summary["max_failed_login_attempts_for_key"], 2)
        self.assertEqual(summary["failed_login_limit"], 5)
        self.assertNotIn("10.0.0.5", str(summary))
        self.assertNotIn("admin", str(summary))

    def test_login_rate_limit_writes_audit_event(self):
        class Client:
            host = "10.0.0.8"

        class Request:
            client = Client()

        request = Request()
        for _ in range(auth_route._MAX_FAILED_ATTEMPTS):
            auth_route._record_failed_login(request, "Admin")

        with patch.object(auth_route, "write_audit_event") as audit:
            with self.assertRaises(HTTPException) as context:
                auth_route._check_login_rate_limit(request, "Admin")

        self.assertEqual(context.exception.status_code, 429)
        audit.assert_called_once()
        action, actor, success, source_ip, metadata = audit.call_args.args
        self.assertEqual(action, "auth.login_rate_limited")
        self.assertEqual(actor, "admin")
        self.assertFalse(success)
        self.assertEqual(source_ip, "10.0.0.8")
        self.assertEqual(metadata["attempt_count"], auth_route._MAX_FAILED_ATTEMPTS)
        self.assertEqual(metadata["limit"], auth_route._MAX_FAILED_ATTEMPTS)
        self.assertEqual(metadata["window_seconds"], 300)

    def test_change_password_wrong_old_password_writes_audit_event(self):
        class Client:
            host = "10.0.0.9"

        class Request:
            client = Client()

        class UserRepo:
            def get_by_username(self, username):
                return User(
                    id=1,
                    username=username,
                    password_hash=bcrypt.hashpw(b"correct-old", bcrypt.gensalt()).decode("utf-8"),
                    role=UserRole.ADMIN,
                    is_active=True,
                )

        with patch.object(auth_route, "write_audit_event") as audit:
            with self.assertRaises(HTTPException) as context:
                auth_route.change_password(
                    ChangePasswordRequest(old_password="wrong-old", new_password="new-strong-password"),
                    Request(),
                    {"sub": "admin"},
                    UserRepo(),
                )

        self.assertEqual(context.exception.status_code, 400)
        audit.assert_called_once_with(
            "auth.change_password",
            "admin",
            False,
            "10.0.0.9",
            {"reason": "old_password_mismatch"},
        )


if __name__ == "__main__":
    unittest.main()
