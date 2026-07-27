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
const alarmsPage = read('src/pages/AlarmsPage.tsx')
const permissionsHook = read('src/hooks/usePermissions.ts')
const generatedOpenApiTypes = read('src/types/openapi.generated.ts')
const backendAlarmRoutes = read('../backend/src/presentation/api/routes/alarms.py')
const backendDependencies = read('../backend/src/presentation/api/dependencies.py')

assertContains(alarmsApi, '/alarms/threshold-suggestions', 'alarm threshold suggestion endpoint')
assertContains(alarmsApi, '/alarms/threshold-suggestions/apply', 'alarm threshold apply endpoint')
assertContains(alarmsApi, '/evidence-manifest', 'alarm evidence manifest endpoint')
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
assertContains(generatedOpenApiTypes, '/api/alarms/threshold-suggestions', 'generated OpenAPI threshold read path')
assertContains(generatedOpenApiTypes, '/api/alarms/threshold-suggestions/apply', 'generated OpenAPI threshold apply path')
assertContains(generatedOpenApiTypes, '/api/alarms/{alarm_id}/evidence-manifest', 'generated OpenAPI evidence manifest path')
assertContains(generatedOpenApiTypes, 'export type OpenApiOperation', 'generated OpenAPI operation union')

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
