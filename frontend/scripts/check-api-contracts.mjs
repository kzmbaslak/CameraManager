import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

const root = process.cwd()

const generatedTypesCheck = spawnSync(
  'node',
  ['scripts/generate-openapi-types.mjs', '--check'],
  { cwd: root, encoding: 'utf8' },
)
if (generatedTypesCheck.status !== 0) {
  throw new Error(
    `generated OpenAPI types check failed\n${generatedTypesCheck.stdout ?? ''}${generatedTypesCheck.stderr ?? ''}`,
  )
}

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8')
}

function assertContains(source, needle, label) {
  if (!source.includes(needle)) {
    throw new Error(`${label}: expected to find ${needle}`)
  }
}

function assertMatches(source, pattern, label) {
  if (!pattern.test(source)) {
    throw new Error(`${label}: expected pattern ${pattern}`)
  }
}

const alarmsApi = read('src/api/alarms.ts')
const camerasApi = read('src/api/cameras.ts')
const recordingsApi = read('src/api/recordings.ts')
const recordingsPage = read('src/pages/RecordingsPage.tsx')
const appRouter = read('src/router/index.tsx')
const sidebar = read('src/components/layout/Sidebar.tsx')
const camerasPage = read('src/pages/CamerasPage.tsx')
const cameraFullscreenModal = read('src/components/camera/CameraFullscreenModal.tsx')
const frontendApiTypes = read('src/types/api.ts')
const alarmsPage = read('src/pages/AlarmsPage.tsx')
const permissionsHook = read('src/hooks/usePermissions.ts')
const generatedOpenApiTypes = read('src/types/openapi.generated.ts')
const backendAlarmRoutes = read('../backend/src/presentation/api/routes/alarms.py')
const backendCameraSchema = read('../backend/src/presentation/api/schemas/camera_schema.py')
const backendDependencies = read('../backend/src/presentation/api/dependencies.py')
const backendRecordingRoutes = read('../backend/src/presentation/api/routes/recordings.py')

assertContains(alarmsApi, '/alarms/threshold-suggestions', 'alarm threshold suggestion endpoint')
assertContains(alarmsApi, '/alarms/threshold-suggestions/apply', 'alarm threshold apply endpoint')
assertContains(alarmsApi, '/evidence-manifest', 'alarm evidence manifest endpoint')
assertContains(camerasApi, '/ptz/move', 'camera PTZ move endpoint')
assertContains(camerasApi, '/ptz/presets', 'camera PTZ preset list endpoint')
assertContains(camerasApi, '/ptz/presets/goto', 'camera PTZ goto preset endpoint')
assertContains(camerasApi, '/ptz/home', 'camera PTZ home endpoint')
assertContains(camerasApi, '/ptz/patrol', 'camera PTZ patrol endpoint')
assertContains(recordingsApi, '/recordings/', 'recording segment list endpoint')
assertContains(recordingsApi, '/recordings/${segmentId}/file', 'recording file endpoint')
assertContains(recordingsApi, '/recordings/maintenance/prune', 'recording prune endpoint')
assertContains(recordingsPage, 'recordingsApi.list', 'recording page list action')
assertContains(recordingsPage, 'recordingsApi.prune', 'recording page prune action')
assertContains(recordingsPage, 'recordingsApi.fileBlob', 'recording page file access action')
assertContains(recordingsPage, '<video', 'recording page playback preview')
assertContains(recordingsPage, 'canManageRecordings &&', 'recording page prune permission gate')
assertContains(appRouter, 'path="recordings"', 'recording route')
assertContains(sidebar, "to: '/recordings'", 'recording sidebar item')
assertContains(frontendApiTypes, 'RecordingSegmentListResponse', 'frontend recording list type')
assertContains(frontendApiTypes, 'RecordingPruneResult', 'frontend recording prune type')
assertContains(backendRecordingRoutes, 'Depends(get_recording_view_user)', 'backend recording list permission')
assertContains(backendRecordingRoutes, 'Depends(get_recording_manage_user)', 'backend recording prune permission')
assertContains(permissionsHook, 'canViewRecordings: isAdmin || isOperator', 'frontend recording view permission contract')
assertContains(permissionsHook, 'canManageRecordings: isAdmin', 'frontend recording manage permission contract')
assertContains(alarmsPage, 'canExportEvidence &&', 'threshold suggestions visibility is permission-gated')
assertContains(alarmsPage, 'canEditCameras &&', 'threshold apply action is camera-edit gated')
assertContains(alarmsPage, 'applyThresholdSuggestions.mutate', 'threshold apply UI action')
assertContains(alarmsPage, 'handleDownloadEvidenceManifest', 'evidence manifest UI action')
assertContains(backendAlarmRoutes, '"changes": [', 'threshold apply audit change list')
assertContains(
  backendAlarmRoutes,
  '"previous_confidence_threshold"',
  'threshold apply audit previous threshold',
)
assertContains(
  backendAlarmRoutes,
  '"applied_confidence_threshold"',
  'threshold apply audit applied threshold',
)
assertContains(backendAlarmRoutes, '_recording_evidence_file_items', 'alarm manifest recording evidence helper')
assertContains(backendAlarmRoutes, 'video_event_', 'alarm manifest recording evidence variant')
assertContains(generatedOpenApiTypes, '/api/alarms/threshold-suggestions', 'generated OpenAPI threshold read path')
assertContains(generatedOpenApiTypes, '/api/alarms/threshold-suggestions/apply', 'generated OpenAPI threshold apply path')
assertContains(generatedOpenApiTypes, '/api/alarms/{alarm_id}/evidence-manifest', 'generated OpenAPI evidence manifest path')
assertContains(generatedOpenApiTypes, 'export type OpenApiOperation', 'generated OpenAPI operation union')
assertContains(backendCameraSchema, 'site: Optional[str]', 'backend camera location site schema')
assertContains(backendCameraSchema, 'building: Optional[str]', 'backend camera location building schema')
assertContains(frontendApiTypes, 'site: string | null', 'frontend camera location site type')
assertContains(camerasPage, "key: 'location'", 'camera list location column')
assertContains(frontendApiTypes, 'CameraPtzDirection', 'frontend PTZ direction type')
assertContains(frontendApiTypes, 'CameraPtzPresetItem', 'frontend PTZ preset type')
assertContains(frontendApiTypes, 'CameraPtzHomeResponse', 'frontend PTZ home type')
assertContains(frontendApiTypes, 'CameraPtzPatrolRequest', 'frontend PTZ patrol request type')
assertContains(frontendApiTypes, 'onvif_ptz_supported: boolean | null', 'frontend PTZ capability cache type')
assertContains(cameraFullscreenModal, 'canControlPtz', 'frontend PTZ permission gate')
assertContains(cameraFullscreenModal, "camera?.onvif_ptz_supported === true", 'frontend PTZ capability gate')
assertContains(cameraFullscreenModal, 'ptzSpeedProfiles', 'frontend PTZ speed profiles')
assertContains(cameraFullscreenModal, 'duration_ms: profile.durationMs', 'frontend PTZ speed duration payload')
assertContains(cameraFullscreenModal, 'ptzHome', 'frontend PTZ home action')
assertContains(cameraFullscreenModal, 'ptzPatrol', 'frontend PTZ patrol action')
assertContains(backendCameraSchema, 'onvif_ptz_supported: Optional[bool]', 'backend PTZ capability schema')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/move', 'generated OpenAPI PTZ move path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/presets', 'generated OpenAPI PTZ preset path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/presets/goto', 'generated OpenAPI PTZ goto preset path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/home', 'generated OpenAPI PTZ home path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/patrol', 'generated OpenAPI PTZ patrol path')
assertContains(generatedOpenApiTypes, '/api/recordings/', 'generated OpenAPI recording list path')
assertContains(generatedOpenApiTypes, '/api/recordings/{segment_id}/file', 'generated OpenAPI recording file path')
assertContains(generatedOpenApiTypes, '/api/recordings/maintenance/prune', 'generated OpenAPI recording prune path')

assertMatches(
  backendAlarmRoutes,
  /get_threshold_suggestions[\s\S]*Depends\(get_evidence_export_user\)/,
  'backend threshold suggestion read permission',
)
assertMatches(
  backendAlarmRoutes,
  /apply_threshold_suggestions[\s\S]*Depends\(get_camera_manage_user\)/,
  'backend threshold suggestion apply permission',
)
assertMatches(
  backendDependencies,
  /"operator":\s*{[\s\S]*"camera\.manage"[\s\S]*"evidence\.export"[\s\S]*"alarm\.operate"[\s\S]*}/,
  'backend operator permission contract',
)
assertMatches(
  backendDependencies,
  /"operator":\s*{[\s\S]*"ptz\.control"[\s\S]*}/,
  'backend operator PTZ permission contract',
)
assertMatches(
  backendDependencies,
  /"operator":\s*{[\s\S]*"recording\.view"[\s\S]*}/,
  'backend operator recording permission contract',
)
assertMatches(
  backendDependencies,
  /"admin":\s*{[\s\S]*"recording\.manage"[\s\S]*}/,
  'backend admin recording manage permission contract',
)
assertMatches(
  backendDependencies,
  /"viewer":\s*{\s*"live\.view",?\s*}/,
  'backend viewer permission contract',
)
assertMatches(
  permissionsHook,
  /canEditCameras:\s*isAdmin\s*\|\|\s*isOperator/,
  'frontend camera edit permission contract',
)
assertMatches(
  permissionsHook,
  /canExportEvidence:\s*isAdmin\s*\|\|\s*isOperator/,
  'frontend evidence export permission contract',
)
assertMatches(
  permissionsHook,
  /canManageUsers:\s*isAdmin/,
  'frontend user management permission contract',
)

console.log('API contract check passed.')
