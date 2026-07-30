import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const repoRoot = path.resolve(frontendRoot, '..')

const roots = [
  'Docs_Obsidian',
  'backend/src',
  'backend/scripts',
  'backend/tests',
  'frontend/src',
  'frontend/scripts',
]

const textExtensions = new Set([
  '.css',
  '.html',
  '.js',
  '.json',
  '.jsx',
  '.md',
  '.mjs',
  '.py',
  '.ts',
  '.tsx',
])

const ignoredDirectories = new Set([
  '.git',
  '.pytest_cache',
  '__pycache__',
  'dist',
  'node_modules',
  'venv',
])

const mojibakeFragments = [
  [0xc4, 0xb1],
  [0xc4, 0xb0],
  [0xc4, 0x9f],
  [0xc4, 0x9e],
  [0xc5, 0x9f],
  [0xc5, 0x9e],
  [0xc3, 0xa7],
  [0xc3, 0x87],
  [0xc3, 0xb6],
  [0xc3, 0x96],
  [0xc3, 0xbc],
  [0xc3, 0x9c],
  [0xc2],
  [0xe2, 0x80, 0x99],
  [0xe2, 0x80, 0x9c],
  [0xe2, 0x80, 0x9d],
  [0xe2, 0x80, 0x93],
  [0xe2, 0x80, 0x94],
].map((bytes) => Buffer.from(bytes).toString('latin1'))

const mojibakePattern = new RegExp(`(?:${[...mojibakeFragments, String.fromCharCode(0xfffd)]
  .map((fragment) => fragment.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  .join('|')})`)

function walk(dir) {
  if (!fs.existsSync(dir)) return []
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  return entries.flatMap((entry) => {
    if (ignoredDirectories.has(entry.name)) return []
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) return walk(fullPath)
    return entry.isFile() && textExtensions.has(path.extname(entry.name)) ? [fullPath] : []
  })
}

function lineNumber(source, index) {
  return source.slice(0, index).split('\n').length
}

const failures = []
for (const root of roots) {
  for (const file of walk(path.join(repoRoot, root))) {
    const source = fs.readFileSync(file, 'utf8')
    const match = source.match(mojibakePattern)
    if (!match || match.index == null) continue
    const relative = path.relative(repoRoot, file).replaceAll(path.sep, '/')
    failures.push(`${relative}:${lineNumber(source, match.index)} bozuk UTF-8/mojibake gorunuyor: ${match[0]}`)
  }
}

if (failures.length > 0) {
  throw new Error(`Encoding check failed:\n${failures.join('\n')}`)
}

console.log('Encoding check passed.')
