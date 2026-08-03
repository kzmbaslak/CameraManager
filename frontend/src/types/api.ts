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

export interface Camera {
  id: number
  name: string
  host: string
  rtsp_port: number
  rtsp_path: string
  onvif_port: number
  username: string | null
  password_updated_at: string | null
  status: CameraStatus
  motion_detection_enabled: boolean
  ai_detection_enabled: boolean
  ai_confidence_threshold: number
  ai_iou_threshold: number
  ai_alarm_cooldown_seconds: number
  ai_frame_stride: number
  ai_inference_width: number
  ai_active_start: string | null
  ai_active_end: string | null
  ai_roi_polygon: string | null
  continuous_recording_enabled: boolean
  brand: string | null
  model: string | null
  nvr_id: number | null
  site: string | null
  building: string | null
  floor: string | null
  zone: string | null
  onvif_ptz_supported: boolean | null
  onvif_capabilities_checked_at: string | null
  created_at: string | null
  updated_at: string | null
}

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

export interface Alarm {
  id: number
  camera_id: number
  alarm_type: AlarmType
  status: AlarmStatus
  confidence: number | null
  bounding_box: BoundingBox | null
  snapshot_path: string | null
  snapshot_sha256: string | null
  snapshot_annotated_path: string | null
  snapshot_annotated_sha256: string | null
  message: string | null
  severity: AlarmSeverity
  false_positive: boolean
  assigned_to: string | null
  operator_note: string | null
  resolution_reason: string | null
  created_at: string | null
  acknowledged_at: string | null
  resolved_at: string | null
}

export interface AlarmTrainingFeedbackItem {
  alarm_id: number
  camera_id: number
  created_at: string | null
  confidence: number | null
  bounding_box: BoundingBox | null
  false_positive: boolean
  severity: AlarmSeverity
  operator_note: string | null
  resolution_reason: string | null
  snapshot_sha256: string | null
  snapshot_annotated_sha256: string | null
}

export interface AlarmEvidenceFileItem {
  variant: string
  available: boolean
  filename: string | null
  sha256: string | null
  size_bytes: number | null
  status: string
}

export interface AlarmEvidenceManifest {
  alarm_id: number
  camera_id: number
  alarm_type: AlarmType
  status: AlarmStatus
  severity: AlarmSeverity
  false_positive: boolean
  confidence: number | null
  bounding_box: BoundingBox | null
  created_at: string | null
  acknowledged_at: string | null
  resolved_at: string | null
  generated_at: string
  files: AlarmEvidenceFileItem[]
}

export interface AlarmThresholdSuggestionItem {
  camera_id: number
  sample_count: number
  false_positive_count: number
  false_positive_rate: number
  average_confidence: number | null
  suggested_confidence_threshold: number | null
  recommendation: string
}

export interface AlarmThresholdSuggestionApplyItem {
  camera_id: number
  previous_confidence_threshold: number
  applied_confidence_threshold: number
  sample_count: number
  false_positive_rate: number
}

export interface AlarmThresholdSuggestionApplyResponse {
  applied_count: number
  skipped_count: number
  items: AlarmThresholdSuggestionApplyItem[]
}

export interface NVR {
  id: number
  name: string
  host: string
  onvif_port: number
  username: string | null
  password_updated_at: string | null
  brand: string | null
  model: string | null
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export type NVRCreate = OpenApiSchemas['NVRCreate']

export type NVRChannelInfo = OpenApiSchemas['NVRChannelInfo']
export type NVRProbeDiagnostics = OpenApiSchemas['NVRProbeDiagnostics']

export interface User {
  id: number
  username: string
  role: UserRole
  is_active: boolean
}

export type UserCreate = OpenApiSchemas['UserCreate']
export type UserRole = OpenApiSchemas['UserRole']

export interface LoginResponse {
  access_token: string
  token_type: string
  username: string
  role: string
}

export interface StreamTokenResponse {
  stream_token: string
  expires_in: number
}

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

export interface CameraRtspDiagnostics {
  camera_id: number
  name: string
  host: string
  rtsp_port: number
  rtsp_path: string
  nvr_id: number | null
  has_username: boolean
  public_url: string
  authenticated_url_masked: string
  tcp_open: boolean
  describe_ok: boolean
  frame_ok: boolean
  authenticated_frame_ok: boolean
  anonymous_frame_ok: boolean
  message: string
}

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

export interface CameraStreamDiagnostics {
  camera_id: number
  producer_running: boolean
  producer_started_at: string | null
  producer_uptime_seconds: number | null
  producer_start_count: number
  subscriber_count: number
  active_profile: string
  current_broadcast_fps: number | null
  ai_task_running: boolean
  ai_provider: string | null
  ai_frame_stride: number
  ai_inference_width: number
  last_ai_inference_ms: number | null
  average_ai_inference_ms: number | null
  host_cpu_load_percent: number | null
  host_memory_used_percent: number | null
  host_memory_available_mb: number | null
  cached_frame_available: boolean
  last_broadcast_age_seconds: number | null
  last_frame_age_seconds: number | null
  open_attempts: number
  open_failures: number
  reconnects: number
  failure_count: number
  retry_cooldown_seconds: number
  warmup_reads: number
  open_timeout_ms: number
  read_timeout_ms: number
  last_success_at: string | null
  last_failure_at: string | null
  last_broadcast_at: string | null
}

export interface CameraStreamMetric {
  id: number
  camera_id: number
  sampled_at: string
  producer_running: boolean
  subscriber_count: number
  current_broadcast_fps: number | null
  average_ai_inference_ms: number | null
  host_cpu_load_percent: number | null
  host_memory_used_percent: number | null
  reconnects: number
  open_failures: number
  failure_count: number
}

export interface CameraStreamMetricSummary {
  camera_id: number
  sample_count: number
  producer_running_count: number
  average_broadcast_fps: number | null
  minimum_broadcast_fps: number | null
  average_ai_inference_ms: number | null
  average_host_cpu_load_percent: number | null
  average_host_memory_used_percent: number | null
  latest_sampled_at: string | null
  latest_broadcast_fps: number | null
  latest_ai_inference_ms: number | null
  total_reconnects: number
  total_open_failures: number
  total_failure_count: number
  samples: CameraStreamMetric[]
}

export interface CameraHealthSample {
  id: number
  camera_id: number
  checked_at: string
  reachable: boolean
  status: string
  latency_ms: number | null
  failure_reason: string | null
}

export interface CameraHealthSummary {
  camera_id: number
  sample_count: number
  reachable_count: number
  unreachable_count: number
  availability_percent: number | null
  latest_checked_at: string | null
  latest_latency_ms: number | null
  latest_failure_reason: string | null
  samples: CameraHealthSample[]
}

export interface CameraHealthListItem {
  camera_id: number
  health_level: 'ok' | 'warning' | 'critical' | 'unknown' | string
  health_message: string
  sample_count: number
  reachable_count: number
  availability_percent: number | null
  latest_checked_at: string | null
  latest_reachable: boolean | null
  latest_status: string | null
  latest_latency_ms: number | null
  latest_failure_reason: string | null
}

export interface RecordingSegment {
  id: number
  camera_id: number
  started_at: string
  ended_at: string | null
  recording_type: string
  status: string
  filename: string
  duration_seconds: number | null
  file_sha256: string | null
  size_bytes: number | null
  codec: string | null
  width: number | null
  height: number | null
  fps: number | null
  alarm_id: number | null
  created_at: string | null
}

export interface RecordingSegmentListResponse {
  items: RecordingSegment[]
  total: number
  limit: number
}

export interface RecordingMetadata {
  segment_id: number
  camera_id: number
  alarm_id: number | null
  frame_width: number | null
  frame_height: number | null
  detected_at: string | null
  detections: Detection[]
}

export interface RecordingPruneResult {
  retention_days: number
  quota_mb: number
  removed_count: number
  removed_bytes: number
  deleted_db_count: number
  skipped_count: number
  removed_filenames: string[]
  skipped_reasons: string[]
}

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
