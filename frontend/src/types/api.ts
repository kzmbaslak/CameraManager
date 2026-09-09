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

export type SecurityPostureFinding = OpenApiSchemas['SecurityPostureFindingResponse']
export type SetupCheck = OpenApiSchemas['SetupCheckResponse']
export type SecurityPosture = OpenApiSchemas['SecurityPostureResponse']
export type SecurityPermissions = OpenApiSchemas['SecurityPermissionsResponse']
export type SetupStatus = OpenApiSchemas['SetupStatusResponse']

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
