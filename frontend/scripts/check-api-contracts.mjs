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

function assertNotMatches(source, pattern, label) {
  if (pattern.test(source)) {
    throw new Error(`${label}: unexpected pattern ${pattern}`)
  }
}

const alarmsApi = read('src/api/alarms.ts')
const camerasApi = read('src/api/cameras.ts')
const recordingsApi = read('src/api/recordings.ts')
const recordingsPage = read('src/pages/RecordingsPage.tsx')
const settingsPage = read('src/pages/SettingsPage.tsx')
const systemSettingsStore = read('src/stores/systemSettingsStore.ts')
const dashboardPage = read('src/pages/DashboardPage.tsx')
const appRouter = read('src/router/index.tsx')
const sidebar = read('src/components/layout/Sidebar.tsx')
const camerasPage = read('src/pages/CamerasPage.tsx')
const nvrPage = read('src/pages/NVRPage.tsx')
const cameraCard = read('src/components/camera/CameraCard.tsx')
const cameraFullscreenModal = read('src/components/camera/CameraFullscreenModal.tsx')
const authStore = read('src/stores/authStore.ts')
const cameraStreamRegistry = read('src/hooks/cameraStreamRegistry.ts')
const frontendApiTypes = read('src/types/api.ts')
const alarmsPage = read('src/pages/AlarmsPage.tsx')
const alarmNotificationPanel = read('src/components/alarm/AlarmNotificationPanel.tsx')
const alarmRow = read('src/components/alarm/AlarmRow.tsx')
const permissionsHook = read('src/hooks/usePermissions.ts')
const generatedOpenApiTypes = read('src/types/openapi.generated.ts')
const backendAlarmRoutes = read('../backend/src/presentation/api/routes/alarms.py')
const backendCameraSchema = read('../backend/src/presentation/api/schemas/camera_schema.py')
const backendDependencies = read('../backend/src/presentation/api/dependencies.py')
const backendRecordingRoutes = read('../backend/src/presentation/api/routes/recordings.py')
const backendApiRoot = read('../backend/src/presentation/api/__init__.py')
const backendMain = read('../backend/main.py')

assertContains(alarmsApi, '/alarms/threshold-suggestions', 'alarm threshold suggestion endpoint')
assertContains(alarmsApi, '/alarms/threshold-suggestions/apply', 'alarm threshold apply endpoint')
assertContains(alarmsApi, '/evidence-manifest', 'alarm evidence manifest endpoint')
assertContains(alarmsApi, '/evidence-report', 'alarm evidence report endpoint')
assertContains(camerasApi, '/ptz/move', 'camera PTZ move endpoint')
assertContains(camerasApi, '/ptz/presets', 'camera PTZ preset list endpoint')
assertContains(camerasApi, '/ptz/presets/goto', 'camera PTZ goto preset endpoint')
assertContains(camerasApi, '/ptz/home', 'camera PTZ home endpoint')
assertContains(camerasApi, '/ptz/patrol', 'camera PTZ patrol endpoint')
assertContains(recordingsApi, '/recordings/', 'recording segment list endpoint')
assertContains(recordingsApi, 'alarm_id?: number', 'recording alarm filter API parameter')
assertContains(recordingsApi, '/recordings/${segmentId}/file', 'recording file endpoint')
assertContains(recordingsApi, '/recordings/${segmentId}/metadata', 'recording metadata endpoint')
assertContains(recordingsApi, '/recordings/maintenance/prune', 'recording prune endpoint')
assertContains(recordingsPage, 'recordingsApi.list', 'recording page list action')
assertContains(recordingsPage, 'recordingsApi.prune', 'recording page prune action')
assertContains(recordingsPage, 'recordingsApi.fileBlob', 'recording page file access action')
assertContains(recordingsPage, 'recordingsApi.metadata', 'recording page metadata action')
assertContains(recordingsPage, 'useSearchParams', 'recording page URL filter support')
assertContains(recordingsPage, 'Alarm Filtresini Kaldir', 'recording page linked alarm filter clear action')
assertContains(recordingsPage, 'autoOpenedAlarmRef', 'recording page linked alarm auto-open guard')
assertContains(recordingsPage, 'Tamamlanmis ilk klip otomatik acilir', 'recording page linked alarm auto-open operator hint')
assertContains(recordingsPage, '<video', 'recording page playback preview')
assertContains(recordingsPage, 'BoundingBoxOverlay', 'recording page playback bbox overlay')
assertContains(recordingsPage, 'humanDetectionBoxesVisible', 'recording page bbox visibility setting')
assertContains(recordingsPage, 'PLAYBACK_SPEED_OPTIONS', 'recording page playback speed presets')
assertContains(recordingsPage, 'playbackRate = playbackSpeed', 'recording page playback speed binding')
assertContains(recordingsPage, 'detectionOffsetSeconds', 'recording page alarm moment offset helper')
assertContains(recordingsPage, 'Alarm ani', 'recording page alarm moment quick seek')
assertContains(recordingsPage, 'Olay Inceleme', 'recording page event investigation summary')
assertContains(recordingsPage, 'Kutu Sayisi', 'recording page detection count summary')
assertContains(recordingsPage, 'En Yuksek Guven', 'recording page max confidence summary')
assertContains(recordingsPage, 'Kanit Hash', 'recording page evidence hash summary')
assertContains(recordingsPage, 'Kamera Zaman Cizelgesi', 'recording page visual timeline')
assertContains(recordingsPage, 'segmentTimelineStyle', 'recording page timeline segment positioning')
assertContains(recordingsPage, 'canManageRecordings &&', 'recording page prune permission gate')
assertContains(appRouter, 'path="recordings"', 'recording route')
assertContains(sidebar, "to: '/recordings'", 'recording sidebar item')
assertContains(frontendApiTypes, 'RecordingSegmentListResponse', 'frontend recording list type')
assertContains(frontendApiTypes, 'RecordingMetadata', 'frontend recording metadata type')
assertContains(frontendApiTypes, 'RecordingPruneResult', 'frontend recording prune type')
assertContains(frontendApiTypes, 'recording_prune_interval_minutes', 'frontend recording automatic prune posture type')
assertContains(frontendApiTypes, 'recording_event_pre_seconds', 'frontend event recording pre/post posture type')
assertContains(frontendApiTypes, 'recording_continuous_enabled', 'frontend continuous recording posture type')
assertContains(frontendApiTypes, 'continuous_recording_enabled: boolean', 'frontend camera continuous recording policy type')
assertContains(frontendApiTypes, 'continuous_recording_excluded_camera_count', 'frontend continuous recording camera exclusion posture type')
assertContains(frontendApiTypes, 'recording_continuous_active_start', 'frontend continuous recording schedule posture type')
assertContains(frontendApiTypes, 'alarm_report_webhook_configured', 'frontend alarm report delivery posture type')
assertContains(frontendApiTypes, 'alarm_report_email_configured', 'frontend alarm report email delivery posture type')
assertContains(frontendApiTypes, 'device_without_password_count', 'frontend device hardening posture type')
assertContains(frontendApiTypes, 'camera_onvif_capability_unknown_count', 'frontend ONVIF hardening posture type')
assertContains(frontendApiTypes, 'device_default_onvif_port_count', 'frontend default ONVIF port posture type')
assertContains(frontendApiTypes, 'active_failed_login_attempt_count', 'frontend failed login posture type')
assertContains(frontendApiTypes, 'failed_login_window_seconds', 'frontend failed login window posture type')
assertContains(frontendApiTypes, 'profile_s_likely: boolean', 'frontend ONVIF Profile S indicator type')
assertContains(frontendApiTypes, 'event_subscription_likely: boolean', 'frontend ONVIF event subscription indicator type')
assertContains(backendRecordingRoutes, 'Depends(get_recording_view_user)', 'backend recording list permission')
assertContains(backendRecordingRoutes, 'alarm_id: Optional[int] = Query', 'backend recording alarm filter parameter')
assertContains(backendRecordingRoutes, 'list_alarm_segments(alarm_id)', 'backend recording alarm segment query')
assertContains(backendRecordingRoutes, 'Depends(get_recording_manage_user)', 'backend recording prune permission')
assertContains(backendDependencies, 'recording_retention_runner = RecordingRetentionRunner', 'backend recording retention runner singleton')
assertContains(backendMain, 'recording_retention_runner.start()', 'backend recording retention runner startup')
assertContains(backendMain, 'recording_retention_runner.stop()', 'backend recording retention runner shutdown')
assertContains(backendApiRoot, 'recording_prune_interval_minutes', 'backend recording automatic prune posture field')
assertContains(backendApiRoot, 'recording_event_pre_seconds', 'backend event recording pre/post posture field')
assertContains(backendApiRoot, 'recording_continuous_enabled', 'backend continuous recording posture field')
assertContains(backendApiRoot, 'continuous_recording_excluded_camera_count', 'backend continuous recording camera exclusion posture field')
assertContains(backendApiRoot, 'recording_continuous_active_start', 'backend continuous recording schedule posture field')
assertContains(backendApiRoot, 'alarm_report_webhook_configured', 'backend alarm report delivery posture field')
assertContains(backendApiRoot, 'alarm_report_email_configured', 'backend alarm report email delivery posture field')
assertContains(backendApiRoot, 'device_without_password_count', 'backend device hardening posture field')
assertContains(backendApiRoot, 'camera_onvif_capability_unknown_count', 'backend ONVIF hardening posture field')
assertContains(backendApiRoot, 'device_default_onvif_port_count', 'backend default ONVIF port posture field')
assertContains(backendApiRoot, 'failed_login_window_summary', 'backend failed login posture summary')
assertContains(permissionsHook, 'canViewRecordings: isAdmin || isOperator', 'frontend recording view permission contract')
assertContains(permissionsHook, 'canManageRecordings: isAdmin', 'frontend recording manage permission contract')
assertContains(alarmsPage, 'canExportEvidence &&', 'threshold suggestions visibility is permission-gated')
assertContains(alarmsPage, 'canEditCameras &&', 'threshold apply action is camera-edit gated')
assertContains(alarmsPage, 'applyThresholdSuggestions.mutate', 'threshold apply UI action')
assertContains(alarmsPage, 'handleDownloadEvidenceManifest', 'evidence manifest UI action')
assertContains(alarmsPage, 'handleDownloadEvidenceReport', 'evidence report UI action')
assertContains(alarmsPage, 'Kanit raporu indirildi', 'evidence report success toast')
assertContains(alarmsPage, 'Olay Kaydi', 'alarm detail recording shortcut')
assertContains(alarmsPage, '/recordings?alarm_id=', 'alarm detail recording URL shortcut')
assertContains(alarmsPage, 'Mudahale Sirasi', 'alarm detail operator procedure checklist')
assertContains(alarmsPage, 'kutulu kanit uzerinden insan konumunu dogrula', 'alarm detail bbox evidence verification step')
assertContains(alarmNotificationPanel, '30 sn Sessiz', 'alarm notification short mute action')
assertContains(alarmNotificationPanel, 'BoundingBoxOverlay', 'alarm notification bbox overlay')
assertContains(alarmNotificationPanel, 'humanDetectionBoxesVisible', 'alarm notification bbox visibility setting')
assertContains(alarmNotificationPanel, 'Mudahale Sirasi', 'alarm notification operator procedure checklist')
assertContains(alarmNotificationPanel, 'insan konumunu kutudan dogrula', 'alarm notification bbox verification step')
assertContains(alarmNotificationPanel, 'canOperateAlarms', 'alarm notification operation permission gate')
assertContains(alarmNotificationPanel, 'canOperateAlarms && notifications.length > 1', 'alarm notification bulk acknowledge permission gate')
assertContains(alarmNotificationPanel, "e.key === 's'", 'alarm notification short mute shortcut')
assertContains(alarmNotificationPanel, "e.key === 'm'", 'alarm notification long mute shortcut')
assertContains(alarmNotificationPanel, "canOperateAlarms) acknowledge.mutate", 'alarm notification acknowledge shortcut permission gate')
assertContains(alarmNotificationPanel, 'muteSoundFor(30 * 1000)', 'alarm notification short mute duration')
assertNotMatches(alarmRow, /Ä±|Ä°|Ã|Â|Å|âœ/, 'alarm row visible text must not contain mojibake sequences')
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
assertContains(generatedOpenApiTypes, '/api/alarms/{alarm_id}/evidence-report', 'generated OpenAPI evidence report path')
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
assertContains(cameraFullscreenModal, 'humanDetectionBoxesVisible', 'fullscreen bbox visibility setting')
assertContains(cameraFullscreenModal, 'canAcknowledgeAlarms ? expandedAlarmId ?? alarmId : null', 'fullscreen acknowledge permission gate')
assertContains(cameraFullscreenModal, 'canAcknowledgeAlarms && actionableAlarmId', 'fullscreen acknowledge shortcut permission gate')
assertContains(cameraCard, 'humanDetectionBoxesVisible', 'camera card bbox visibility setting')
assertContains(cameraCard, 'canAcknowledgeAlarms &&', 'camera card acknowledge permission gate')
assertContains(authStore, 'clearAllCameraStreams()', 'auth logout clears live stream connections')
assertContains(authStore, 'sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY)', 'auth logout removes persisted browser session')
assertContains(cameraStreamRegistry, 'export function clearAllCameraStreams', 'camera stream registry exposes global cleanup')
assertContains(cameraStreamRegistry, 'streams.clear()', 'camera stream cleanup clears registry')
assertContains(dashboardPage, 'canAcknowledgeAlarms &&', 'dashboard acknowledge permission gate')
assertContains(dashboardPage, 'canAcknowledgeAlarms={canAcknowledgeAlarms}', 'dashboard assist panel acknowledge permission prop')
assertContains(dashboardPage, 'active_failed_login_attempt_count', 'dashboard failed login posture display')
assertContains(dashboardPage, 'login deneme', 'dashboard failed login posture label')
assertContains(systemSettingsStore, 'humanDetectionBoxesVisible: true', 'system settings bbox visibility default')
assertContains(settingsPage, 'Insan Kutulari', 'settings page bbox visibility control')
assertContains(settingsPage, 'auditActionLabel', 'settings audit readable action labels')
assertContains(settingsPage, 'auth.login_rate_limited', 'settings audit login rate limit label')
assertContains(settingsPage, 'auditEventSummary', 'settings audit readable event summary')
assertContains(settingsPage, 'nvr.probe', 'settings audit NVR probe summary')
assertContains(settingsPage, 'AuditCategory', 'settings audit category filter type')
assertContains(settingsPage, 'Audit olay tipi filtresi', 'settings audit category filter control')
assertMatches(
  settingsPage,
  /<Badge variant="neutral" className="mb-2">İzleyici<\/Badge>[\s\S]*<li>✗ Alarm onaylama<\/li>/,
  'settings viewer role card denies alarm acknowledge',
)
assertNotMatches(
  settingsPage,
  /<Badge variant="neutral" className="mb-2">İzleyici<\/Badge>[\s\S]*<li>✓ Alarm onaylama<\/li>/,
  'settings viewer role card must not allow alarm acknowledge',
)
assertContains(read('../backend/src/application/services/camera_stream_manager.py'), '_save_continuous_recording_clip_sync', 'backend continuous recording writer')
assertContains(read('../backend/src/application/services/camera_stream_manager.py'), '_event_post_seconds', 'backend event recording post buffer')
assertContains(read('../backend/src/application/services/camera_stream_manager.py'), 'RECORDING_CONTINUOUS_ENABLED', 'backend continuous recording env gate')
assertContains(read('../backend/src/application/services/camera_stream_manager.py'), 'RECORDING_CONTINUOUS_ACTIVE_START', 'backend continuous recording schedule gate')
assertContains(read('../backend/src/presentation/api/routes/nvrs.py'), '"nvr.probe"', 'backend NVR probe audit event')
assertContains(read('../backend/src/presentation/api/routes/nvrs.py'), '_audit_nvr_probe(request, current_user, nvr_id, diagnostics)', 'backend NVR probe audit route binding')
assertContains(read('../backend/src/infrastructure/reports/alarm_report.py'), 'deliver_alarm_report_webhook', 'backend alarm report webhook delivery')
assertContains(read('../backend/src/infrastructure/reports/alarm_report.py'), 'deliver_alarm_report_email', 'backend alarm report email delivery')
assertContains(read('../backend/scripts/export_alarm_report.py'), '--skip-delivery', 'alarm report CLI delivery control')
assertContains(backendCameraSchema, 'onvif_ptz_supported: Optional[bool]', 'backend PTZ capability schema')
assertContains(backendCameraSchema, 'continuous_recording_enabled: bool', 'backend camera continuous recording policy schema')
assertContains(backendCameraSchema, 'profile_s_likely: bool', 'backend ONVIF Profile S indicator schema')
assertContains(backendCameraSchema, 'event_subscription_likely: bool', 'backend ONVIF event subscription indicator schema')
assertContains(camerasPage, "key: 'recording'", 'camera list recording policy column')
assertContains(camerasPage, 'Profile S', 'camera ONVIF Profile S compatibility UI')
assertContains(camerasPage, 'Event Sub', 'camera ONVIF event subscription UI')
assertContains(nvrPage, 'ONVIF Kontrol Listesi', 'NVR ONVIF troubleshooting checklist')
assertContains(nvrPage, 'analitik metadata NVR', 'NVR fallback metadata ownership explanation')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/move', 'generated OpenAPI PTZ move path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/presets', 'generated OpenAPI PTZ preset path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/presets/goto', 'generated OpenAPI PTZ goto preset path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/home', 'generated OpenAPI PTZ home path')
assertContains(generatedOpenApiTypes, '/api/cameras/{camera_id}/ptz/patrol', 'generated OpenAPI PTZ patrol path')
assertContains(generatedOpenApiTypes, '/api/recordings/', 'generated OpenAPI recording list path')
assertContains(generatedOpenApiTypes, '/api/recordings/{segment_id}/file', 'generated OpenAPI recording file path')
assertContains(generatedOpenApiTypes, '/api/recordings/{segment_id}/metadata', 'generated OpenAPI recording metadata path')
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
