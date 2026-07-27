import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()

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
const backendAlarmRoutes = read('../backend/src/presentation/api/routes/alarms.py')
const backendDependencies = read('../backend/src/presentation/api/dependencies.py')

assertContains(alarmsApi, '/alarms/threshold-suggestions', 'alarm threshold suggestion endpoint')
assertContains(alarmsApi, '/alarms/threshold-suggestions/apply', 'alarm threshold apply endpoint')
assertContains(alarmsPage, 'canExportEvidence &&', 'threshold suggestions visibility is permission-gated')
assertContains(alarmsPage, 'canEditCameras &&', 'threshold apply action is camera-edit gated')
assertContains(alarmsPage, 'applyThresholdSuggestions.mutate', 'threshold apply UI action')

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
