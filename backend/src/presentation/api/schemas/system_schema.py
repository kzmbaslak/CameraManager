"""Sistem saglik, kurulum ve guvenlik durusu response semalari."""

from typing import Literal

from pydantic import BaseModel


Severity = Literal["critical", "high", "medium", "low", "info"]


class HealthResponse(BaseModel):
    status: str


class ReadinessCheckResponse(BaseModel):
    key: str
    ok: bool
    severity: Severity | str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded"] | str
    ready: bool
    blocking_issue_count: int
    warning_count: int
    checks: list[ReadinessCheckResponse]


class SetupCheckResponse(BaseModel):
    key: str
    ok: bool
    severity: Severity | str
    message: str


class SecurityPostureFindingResponse(BaseModel):
    severity: Literal["critical", "high", "medium", "low"] | str
    message: str


class SecurityPostureResponse(BaseModel):
    status: Literal["hardened", "attention"] | str
    jwt_secret_configured: bool
    camera_encryption_key_configured: bool
    cors_origins_configured: bool
    trusted_hosts_configured: bool
    https_enabled: bool
    secure_cookie_auth: bool
    audit_chain_secret_configured: bool
    audit_webhook_configured: bool
    alarm_report_webhook_configured: bool
    alarm_report_email_configured: bool
    app_log_rotation_configured: bool
    app_log_json_format: bool
    app_log_sensitive_query_masking: bool
    device_password_rotation_days: int
    device_password_rotation_compliant: bool
    device_password_total_count: int
    device_total_count: int
    device_without_password_count: int
    camera_without_password_count: int
    nvr_without_password_count: int
    camera_default_rtsp_port_count: int
    camera_default_onvif_port_count: int
    nvr_default_onvif_port_count: int
    device_default_onvif_port_count: int
    camera_onvif_capability_unknown_count: int
    camera_ptz_supported_count: int
    overdue_device_password_count: int
    missing_device_password_rotation_count: int
    overdue_camera_password_count: int
    overdue_nvr_password_count: int
    security_headers_enabled: bool
    content_security_policy_enabled: bool
    setup_checks: list[SetupCheckResponse]
    stream_token_transport: str
    stream_token_ttl_seconds: int
    active_failed_login_key_count: int
    active_failed_login_attempt_count: int
    max_failed_login_attempts_for_key: int
    failed_login_limit: int
    failed_login_window_seconds: int
    recording_storage_dir_configured: bool
    recording_retention_days: int
    recording_max_storage_mb: int
    recording_prune_interval_minutes: int
    recording_event_pre_seconds: float
    recording_event_post_seconds: float
    recording_continuous_enabled: bool
    continuous_recording_excluded_camera_count: int
    recording_continuous_segment_seconds: int
    recording_continuous_fps: float
    recording_continuous_active_start: str | None = None
    recording_continuous_active_end: str | None = None
    findings: list[SecurityPostureFindingResponse]


class SecurityPermissionsResponse(BaseModel):
    role: str | None = None
    permissions: list[str]


class SetupStatusResponse(BaseModel):
    ready: bool
    checks: list[SetupCheckResponse]
