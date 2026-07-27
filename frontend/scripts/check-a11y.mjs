import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const rootDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const srcDir = path.join(rootDir, 'src')

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  return entries.flatMap((entry) => {
    const fullPath = path.join(dir, entry.name)
    if (entry.isDirectory()) return walk(fullPath)
    return entry.isFile() && fullPath.endsWith('.tsx') ? [fullPath] : []
  })
}

function lineNumber(source, index) {
  return source.slice(0, index).split('\n').length
}

function hasAccessibleName(attributes, children = '') {
  return /\baria-label=|\baria-labelledby=|\btitle=/.test(attributes) || /[A-Za-zÇĞİÖŞÜçğıöşü0-9]/.test(children)
}

function isInsideLabel(source, index) {
  const lastOpen = source.lastIndexOf('<label', index)
  const lastClose = source.lastIndexOf('</label>', index)
  return lastOpen > lastClose
}

function report(failures, file, source, index, message) {
  const relative = path.relative(rootDir, file).replaceAll(path.sep, '/')
  failures.push(`${relative}:${lineNumber(source, index)} ${message}`)
}

function findOpeningTagEnd(source, start) {
  let quote = null
  let braceDepth = 0
  for (let index = start; index < source.length; index += 1) {
    const char = source[index]
    if (quote) {
      if (char === quote && source[index - 1] !== '\\') quote = null
      continue
    }
    if (char === '"' || char === "'" || char === '`') {
      quote = char
      continue
    }
    if (char === '{') {
      braceDepth += 1
      continue
    }
    if (char === '}') {
      braceDepth = Math.max(0, braceDepth - 1)
      continue
    }
    if (char === '>' && braceDepth === 0) return index
  }
  return -1
}

function openingTags(source, tagName) {
  const tags = []
  const pattern = new RegExp(`<${tagName}\\b`, 'g')
  for (const match of source.matchAll(pattern)) {
    const end = findOpeningTagEnd(source, match.index)
    if (end < 0) continue
    tags.push({
      index: match.index,
      attributes: source.slice(match.index + tagName.length + 1, end),
      end,
    })
  }
  return tags
}

const failures = []
for (const file of walk(srcDir)) {
  const source = fs.readFileSync(file, 'utf8')

  for (const match of source.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
    const [, attributes, children] = match
    if (!hasAccessibleName(attributes, children)) {
      report(failures, file, source, match.index, '<button> erisilebilir ad icermeli.')
    }
  }

  for (const tag of openingTags(source, 'img')) {
    const { attributes } = tag
    if (!/\balt=/.test(attributes)) {
      report(failures, file, source, tag.index, '<img> alt metni icermeli.')
    }
  }

  for (const tagName of ['input', 'select', 'textarea']) {
    for (const tag of openingTags(source, tagName)) {
      const hasId = /\bid=/.test(tag.attributes)
      const hasAria = /\baria-label=|\baria-labelledby=/.test(tag.attributes)
      if (!hasId && !hasAria && !isInsideLabel(source, tag.index)) {
        report(failures, file, source, tag.index, `<${tagName}> id, aria-label veya aria-labelledby icermeli.`)
      }
    }
  }

  for (const match of source.matchAll(/role=["']dialog["']/g)) {
    const openTagStart = source.lastIndexOf('<', match.index)
    const openTagEnd = source.indexOf('>', match.index)
    const attributes = source.slice(openTagStart, openTagEnd)
    if (!/\baria-modal=/.test(attributes) || !/\baria-labelledby=|\baria-label=/.test(attributes)) {
      report(failures, file, source, match.index, 'dialog role aria-modal ve erisilebilir ad icermeli.')
    }
  }
}

if (failures.length > 0) {
  console.error(`Accessibility static check failed:\n${failures.join('\n')}`)
  process.exit(1)
}

console.log('Accessibility static check passed.')
