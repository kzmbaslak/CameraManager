// Backend API şemalarına karşılık gelen TypeScript tipleri

// Backend CameraStatus enum değerleri lowercase
export type CameraStatus = 'active' | 'inactive' | 'error'

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
}

export type AlarmType = 'human_detected' | 'motion_detected' | 'camera_offline'
export type AlarmStatus = 'new' | 'acknowledged' | 'resolved'

export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface Alarm {
  id: number
  camera_id: number
  alarm_type: AlarmType
  status: AlarmStatus
  confidence: number | null
  bounding_box: BoundingBox | null
  snapshot_path: string | null
  message: string | null
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

// WebSocket stream mesaj formatı
export interface StreamMessage {
  frame?: string           // geriye dönük uyumluluk için Base64 JPEG; yeni akış binary JPEG kullanır
  alarm_triggered: boolean
  alarm_id: number | null
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

export interface CameraStreamDiagnostics {
  camera_id: number
  producer_running: boolean
  subscriber_count: number
  active_profile: string
  ai_task_running: boolean
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
