import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const cssPath = path.join(rootDir, 'src', 'index.css')
const css = fs.readFileSync(cssPath, 'utf8')

function extractBlock(selector) {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = css.match(new RegExp(`${escaped}\\s*\\{([\\s\\S]*?)\\}`))
  if (!match) throw new Error(`${selector} block not found.`)
  return match[1]
}

function extractTokens(selector) {
  const block = extractBlock(selector)
  return Object.fromEntries(
    [...block.matchAll(/--([a-z0-9-]+):\s*([^;]+);/gi)].map((match) => [match[1], match[2].trim()]),
  )
}

function hexToRgb(hex) {
  const normalized = hex.replace('#', '').trim()
  if (!/^[0-9a-f]{6}$/i.test(normalized)) {
    throw new Error(`Unsupported color value: ${hex}`)
  }
  return {
    r: Number.parseInt(normalized.slice(0, 2), 16) / 255,
    g: Number.parseInt(normalized.slice(2, 4), 16) / 255,
    b: Number.parseInt(normalized.slice(4, 6), 16) / 255,
  }
}

function channel(value) {
  return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
}

function luminance(color) {
  const rgb = hexToRgb(color)
  return 0.2126 * channel(rgb.r) + 0.7152 * channel(rgb.g) + 0.0722 * channel(rgb.b)
}

function contrast(foreground, background) {
  const light = Math.max(luminance(foreground), luminance(background))
  const dark = Math.min(luminance(foreground), luminance(background))
  return (light + 0.05) / (dark + 0.05)
}

const checks = [
  ['text-primary', 'bg-primary', 4.5],
  ['text-primary', 'bg-card', 4.5],
  ['text-primary', 'bg-secondary', 4.5],
  ['text-secondary', 'bg-primary', 4.5],
  ['text-secondary', 'bg-card', 4.5],
  ['accent', 'bg-card', 3],
  ['danger', 'bg-card', 3],
  ['success', 'bg-card', 3],
  ['warning', 'bg-card', 3],
]

const themes = [
  ['dark', extractTokens(':root')],
  ['light', { ...extractTokens(':root'), ...extractTokens(":root[data-theme='light']") }],
]

const failures = []
for (const [themeName, tokens] of themes) {
  for (const [fgToken, bgToken, minimum] of checks) {
    const fg = tokens[fgToken]
    const bg = tokens[bgToken]
    const ratio = contrast(fg, bg)
    if (ratio < minimum) {
      failures.push(`${themeName}: ${fgToken} on ${bgToken} = ${ratio.toFixed(2)} < ${minimum}`)
    }
  }
}

if (failures.length > 0) {
  console.error(`Theme contrast check failed:\n${failures.join('\n')}`)
  process.exit(1)
}

console.log(`Theme contrast check passed for ${themes.length} themes and ${checks.length} token pairs.`)
