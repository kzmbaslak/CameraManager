// Backend API şemalarına karşılık gelen TypeScript tipleri

// Backend CameraStatus enum değerleri lowercase
export type CameraStatus = 'active' | 'inactive' | 'error'

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
  brand: string | null
  model: string | null
  nvr_id: number | null
  created_at: string | null
  updated_at: string | null
}

export interface CameraCreate {
  name: string
  host: string
  rtsp_port?: number
  auto_rtsp_ports?: boolean
  rtsp_path?: string
  onvif_port?: number
  username?: string
  password?: string
  brand?: string
  model?: string
  ai_confidence_threshold?: number
  ai_iou_threshold?: number
  ai_alarm_cooldown_seconds?: number
  ai_frame_stride?: number
  ai_inference_width?: number
  ai_active_start?: string | null
  ai_active_end?: string | null
  ai_roi_polygon?: string | null
}

export type AlarmType = 'human_detected' | 'motion_detected' | 'camera_offline'
export type AlarmStatus = 'new' | 'acknowledged' | 'resolved'
export type AlarmSeverity = 'low' | 'medium' | 'high' | 'critical'

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

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

export interface NVR {
  id: number
  name: string
  host: string
  onvif_port: number
  username: string | null
  brand: string | null
  model: string | null
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface NVRCreate {
  name: string
  host: string
  onvif_port?: number
  username?: string
  password?: string
  brand?: string
  model?: string
}

export interface NVRChannelInfo {
  profile_token: string
  profile_name: string
  manufacturer: string | null
  model: string | null
  rtsp_url: string
  source: 'onvif' | 'rtsp_fallback' | string
  diagnostic: string | null
}

export interface NVRProbeDiagnostics {
  source: 'onvif' | 'rtsp_fallback' | 'none' | string
  onvif_ok: boolean
  fallback_used: boolean
  device_manufacturer: string | null
  device_model: string | null
  profile_count: number
  stream_uri_count: number
  onvif_error: string | null
  fallback_error: string | null
  channels: NVRChannelInfo[]
}

export interface User {
  id: number
  username: string
  role: string
  is_active: boolean
}

export interface UserCreate {
  username: string
  password: string
  role: string
}

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
}

export interface CameraScanRequest {
  ip_range: string
  rtsp_port?: number
  auto_rtsp_ports?: boolean
  username?: string
  password?: string
}

export interface CameraScanResult {
  ip: string
  port: number
  path: string
  brand: string
  desc: string
  url: string
}

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

export interface CameraRtspPreviewRequest {
  camera_id?: number
  name?: string
  host?: string
  rtsp_port?: number
  rtsp_path?: string
  username?: string
  password?: string
}

export interface CameraOnvifPreviewRequest {
  camera_id?: number
  host?: string
  onvif_port?: number
  username?: string
  password?: string
}

export interface CameraOnvifPreviewResponse {
  camera_id: number
  host: string
  onvif_port: number
  ok: boolean
  manufacturer: string | null
  model: string | null
  serial_number: string | null
  firmware_version: string | null
  profile_count: number
  stream_uri_count: number
  first_stream_uri_masked: string | null
  message: string
}

export interface CameraStreamDiagnostics {
  camera_id: number
  producer_running: boolean
  subscriber_count: number
  active_profile: string
  ai_task_running: boolean
  ai_provider: string | null
  ai_frame_stride: number
  ai_inference_width: number
  cached_frame_available: boolean
  last_broadcast_age_seconds: number | null
  last_frame_age_seconds: number | null
  open_attempts: number
  open_failures: number
  failure_count: number
  retry_cooldown_seconds: number
  warmup_reads: number
  open_timeout_ms: number
  read_timeout_ms: number
  last_success_at: string | null
  last_failure_at: string | null
  last_broadcast_at: string | null
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
  https_enabled: boolean
  secure_cookie_auth: boolean
  audit_chain_secret_configured: boolean
  audit_webhook_configured: boolean
  setup_checks: SetupCheck[]
  stream_token_transport: string
  stream_token_ttl_seconds: number
  findings: SecurityPostureFinding[]
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

export interface NVRScanRequest {
  ip_range: string
  rtsp_port?: number
  username?: string
  password?: string
}

export interface NVRScanResponse {
  host: string
  port: number
  brand: string
  model: string
}
