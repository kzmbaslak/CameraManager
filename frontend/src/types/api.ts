// Backend API şemalarına karşılık gelen TypeScript tipleri
import type { OpenApiSchemas } from './openapi.generated'
export type { OpenApiSchemas } from './openapi.generated'

// Backend CameraStatus enum değerleri lowercase
export type CameraStatus = OpenApiSchemas['CameraStatus']

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type Camera = OpenApiSchemas['CameraResponse']

export type CameraCreate = OpenApiSchemas['CameraCreate']

export type AlarmType = OpenApiSchemas['AlarmType']
export type AlarmStatus = OpenApiSchemas['AlarmStatus']
export type AlarmSeverity = OpenApiSchemas['AlarmSeverity']

export type BoundingBox = OpenApiSchemas['BoundingBoxSchema']

export interface Detection {
  label: string
  confidence: number
  bounding_box: BoundingBox
}

export type Alarm = OpenApiSchemas['AlarmResponse']

export type AlarmTrainingFeedbackItem = OpenApiSchemas['AlarmTrainingFeedbackItem']
export type AlarmEvidenceFileItem = OpenApiSchemas['AlarmEvidenceFileItem']
export type AlarmEvidenceManifest = OpenApiSchemas['AlarmEvidenceManifest']
export type AlarmThresholdSuggestionItem = OpenApiSchemas['AlarmThresholdSuggestionItem']
export type AlarmThresholdSuggestionApplyItem = OpenApiSchemas['AlarmThresholdSuggestionApplyItem']
export type AlarmThresholdSuggestionApplyResponse = OpenApiSchemas['AlarmThresholdSuggestionApplyResponse']

export type NVR = OpenApiSchemas['NVRResponse']

export type NVRCreate = OpenApiSchemas['NVRCreate']

export type NVRChannelInfo = OpenApiSchemas['NVRChannelInfo']
export type NVRProbeDiagnostics = OpenApiSchemas['NVRProbeDiagnostics']

export type User = OpenApiSchemas['UserResponse']

export type UserCreate = OpenApiSchemas['UserCreate']
export type UserRole = OpenApiSchemas['UserRole']

export type LoginResponse = OpenApiSchemas['TokenResponse']

export type StreamTokenResponse = OpenApiSchemas['CameraStreamTokenResponse']

// WebSocket stream mesaj formatı
export interface StreamMessage {
  frame?: string           // geriye dönük uyumluluk için Base64 JPEG; yeni akış binary JPEG kullanır
  alarm_triggered: boolean
  alarm_id: number | null
  detections?: Detection[]
  frame_width?: number | null
  frame_height?: number | null
  detected_at?: string | null
  ai_inference_ms?: number | null
}

export type CameraScanRequest = OpenApiSchemas['CameraScanRequest']

export type CameraScanResult = OpenApiSchemas['CameraScanResult']

export type CameraRtspDiagnostics = OpenApiSchemas['CameraRtspDiagnostics']

export type CameraPtzDirection =
  | 'up'
  | 'down'
  | 'left'
  | 'right'
  | 'up_left'
  | 'up_right'
  | 'down_left'
  | 'down_right'
  | 'zoom_in'
  | 'zoom_out'
  | 'stop'

export type CameraPtzMoveRequest = OpenApiSchemas['CameraPtzMoveRequest']
export type CameraPtzGotoPresetRequest = OpenApiSchemas['CameraPtzGotoPresetRequest']

export type CameraPtzMoveResponse = OpenApiSchemas['CameraPtzMoveResponse']
export type CameraPtzPresetItem = OpenApiSchemas['CameraPtzPresetItem']
export type CameraPtzPresetListResponse = OpenApiSchemas['CameraPtzPresetListResponse']
export type CameraPtzGotoPresetResponse = OpenApiSchemas['CameraPtzGotoPresetResponse']
export type CameraPtzHomeResponse = OpenApiSchemas['CameraPtzHomeResponse']

export type CameraPtzPatrolRequest = OpenApiSchemas['CameraPtzPatrolRequest']

export type CameraPtzPatrolResponse = OpenApiSchemas['CameraPtzPatrolResponse']

export type CameraRtspPreviewRequest = OpenApiSchemas['CameraRtspPreviewRequest']

export type CameraOnvifPreviewRequest = OpenApiSchemas['CameraOnvifPreviewRequest']

export type CameraOnvifProfileInfo = OpenApiSchemas['CameraOnvifProfileInfo']
export type CameraOnvifPreviewResponse = OpenApiSchemas['CameraOnvifPreviewResponse']

export type CameraStreamDiagnostics = OpenApiSchemas['CameraStreamDiagnostics']
export type CameraStreamMetric = OpenApiSchemas['CameraStreamMetricResponse']
export type CameraStreamMetricSummary = OpenApiSchemas['CameraStreamMetricSummaryResponse']

export type CameraHealthSample = OpenApiSchemas['CameraHealthSampleResponse']
export type CameraHealthSummary = OpenApiSchemas['CameraHealthSummaryResponse']
export type CameraHealthListItem = OpenApiSchemas['CameraHealthListItemResponse']

export type RecordingSegment = OpenApiSchemas['RecordingSegmentResponse']
export type RecordingSegmentListResponse = OpenApiSchemas['RecordingSegmentListResponse']
export type RecordingMetadata = OpenApiSchemas['RecordingMetadataResponse']
export type RecordingPruneResult = OpenApiSchemas['RecordingPruneResponse']

export interface SecurityPostureFinding {
  severity: 'critical' | 'high' | 'medium' | 'low' | string
  message: string
}

export interface SetupCheck {
  key: string
  ok: boolean
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info' | string
  message: string
}

export interface SecurityPosture {
  status: 'hardened' | 'attention' | string
  jwt_secret_configured: boolean
  camera_encryption_key_configured: boolean
  cors_origins_configured: boolean
  trusted_hosts_configured: boolean
  https_enabled: boolean
  secure_cookie_auth: boolean
  audit_chain_secret_configured: boolean
  audit_webhook_configured: boolean
  alarm_report_webhook_configured: boolean
  alarm_report_email_configured: boolean
  app_log_rotation_configured: boolean
  app_log_json_format: boolean
  app_log_sensitive_query_masking: boolean
  device_password_rotation_days: number
  device_password_rotation_compliant: boolean
  device_password_total_count: number
  device_total_count: number
  device_without_password_count: number
  camera_without_password_count: number
  nvr_without_password_count: number
  camera_default_rtsp_port_count: number
  camera_default_onvif_port_count: number
  nvr_default_onvif_port_count: number
  device_default_onvif_port_count: number
  camera_onvif_capability_unknown_count: number
  camera_ptz_supported_count: number
  overdue_device_password_count: number
  missing_device_password_rotation_count: number
  overdue_camera_password_count: number
  overdue_nvr_password_count: number
  security_headers_enabled: boolean
  content_security_policy_enabled: boolean
  setup_checks: SetupCheck[]
  stream_token_transport: string
  stream_token_ttl_seconds: number
  active_failed_login_key_count: number
  active_failed_login_attempt_count: number
  max_failed_login_attempts_for_key: number
  failed_login_limit: number
  failed_login_window_seconds: number
  recording_storage_dir_configured: boolean
  recording_retention_days: number
  recording_max_storage_mb: number
  recording_prune_interval_minutes: number
  recording_event_pre_seconds: number
  recording_event_post_seconds: number
  recording_continuous_enabled: boolean
  continuous_recording_excluded_camera_count: number
  recording_continuous_segment_seconds: number
  recording_continuous_fps: number
  recording_continuous_active_start: string | null
  recording_continuous_active_end: string | null
  findings: SecurityPostureFinding[]
}

export interface SecurityPermissions {
  role: string | null
  permissions: string[]
}

export interface SetupStatus {
  ready: boolean
  checks: SetupCheck[]
}

export interface AuditEvent {
  timestamp: string
  action: string
  actor: string | null
  success: boolean
  source_ip: string | null
  metadata: Record<string, unknown>
  previous_hash?: string | null
  event_hash?: string | null
  hash_algorithm?: string | null
}

export type NVRScanRequest = OpenApiSchemas['NVRScanRequest']

export type NVRScanResponse = OpenApiSchemas['NVRScanResponse']
