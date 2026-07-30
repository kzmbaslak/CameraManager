import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const frontendRoot = process.cwd()
const repoRoot = path.resolve(frontendRoot, '..')
const backendRoot = path.join(repoRoot, 'backend')
const outputPath = path.join(frontendRoot, 'src', 'types', 'openapi.generated.ts')
const checkOnly = process.argv.includes('--check')

function runOpenApiExport(schemaPath) {
  const pythonCandidates = [
    path.join(backendRoot, 'venv', 'Scripts', 'python.exe'),
    'python',
  ]
  const env = {
    ...process.env,
    CAMERA_ENCRYPTION_KEY:
      process.env.CAMERA_ENCRYPTION_KEY ?? 'MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=',
    JWT_SECRET_KEY: process.env.JWT_SECRET_KEY ?? '0123456789abcdef0123456789abcdef',
  }

  for (const python of pythonCandidates) {
    const result = spawnSync(
      python,
      ['scripts/export_openapi.py', '--output', schemaPath],
      { cwd: backendRoot, env, encoding: 'utf8' },
    )
    if (result.status === 0) {
      return
    }
    if (python !== pythonCandidates[pythonCandidates.length - 1]) {
      continue
    }
    throw new Error(
      `OpenAPI export failed.\nstdout:\n${result.stdout ?? ''}\nstderr:\n${result.stderr ?? ''}`,
    )
  }
}

function literal(value) {
  return JSON.stringify(value)
}

function refName(ref) {
  return ref.split('/').pop()
}

function renderUnion(values) {
  return values.length > 0 ? values.join(' | ') : 'never'
}

function renderSchemaType(schema) {
  if (!schema || typeof schema !== 'object') {
    return 'unknown'
  }

  if (schema.$ref) {
    return `OpenApiSchemas[${literal(refName(schema.$ref))}]`
  }

  if (Array.isArray(schema.enum)) {
    return renderUnion(schema.enum.map((item) => literal(item)))
  }

  if (schema.const !== undefined) {
    return literal(schema.const)
  }

  if (Array.isArray(schema.allOf) && schema.allOf.length > 0) {
    return schema.allOf.map((item) => `(${renderSchemaType(item)})`).join(' & ')
  }

  if (Array.isArray(schema.oneOf) && schema.oneOf.length > 0) {
    return renderUnion(schema.oneOf.map((item) => `(${renderSchemaType(item)})`))
  }

  if (Array.isArray(schema.anyOf) && schema.anyOf.length > 0) {
    return renderUnion(schema.anyOf.map((item) => `(${renderSchemaType(item)})`))
  }

  const type = Array.isArray(schema.type) ? schema.type : [schema.type].filter(Boolean)
  if (type.includes('null') && type.length > 1) {
    return renderUnion([
      renderSchemaType({ ...schema, type: type.filter((item) => item !== 'null') }),
      'null',
    ])
  }

  if (type.includes('array')) {
    return `Array<${renderSchemaType(schema.items)}>`
  }

  if (type.includes('object') || schema.properties) {
    const properties = schema.properties ?? {}
    const required = new Set(schema.required ?? [])
    const renderedProperties = Object.entries(properties).map(([propertyName, propertySchema]) => {
      const optional = required.has(propertyName) ? '' : '?'
      return `    ${literal(propertyName)}${optional}: ${renderSchemaType(propertySchema)}`
    })
    if (schema.additionalProperties && schema.additionalProperties !== false) {
      const valueType = schema.additionalProperties === true ? 'unknown' : renderSchemaType(schema.additionalProperties)
      renderedProperties.push(`    [key: string]: ${valueType}`)
    }
    return renderedProperties.length > 0 ? `{\n${renderedProperties.join('\n')}\n  }` : 'Record<string, unknown>'
  }

  if (type.includes('integer') || type.includes('number')) {
    return 'number'
  }
  if (type.includes('boolean')) {
    return 'boolean'
  }
  if (type.includes('string')) {
    return 'string'
  }
  if (type.includes('null')) {
    return 'null'
  }
  return 'unknown'
}

function renderSchemaTypes(schema) {
  const schemas = Object.entries(schema.components?.schemas ?? {})
    .sort(([left], [right]) => left.localeCompare(right))

  const schemaNameTypes = schemas
    .map(([schemaName]) => `  | ${literal(schemaName)}`)
    .join('\n')

  const schemaMapTypes = schemas
    .map(([schemaName, schemaDefinition]) => `  ${literal(schemaName)}: ${renderSchemaType(schemaDefinition)}`)
    .join('\n')

  return `export type OpenApiSchemaName =\n${schemaNameTypes || '  | never'}\n\n`
    + `export type OpenApiSchemas = {\n${schemaMapTypes}\n}\n`
}

function render(schema) {
  const operations = Object.entries(schema.paths ?? {})
    .flatMap(([routePath, methods]) => Object.entries(methods)
      .filter(([method]) => ['get', 'post', 'patch', 'delete', 'put'].includes(method))
      .map(([method, operation]) => ({
        method,
        path: routePath,
        operationId: operation.operationId ?? `${method}_${routePath}`,
      })))
    .sort((left, right) => `${left.path}:${left.method}`.localeCompare(`${right.path}:${right.method}`))

  const pathTypes = [...new Set(operations.map((operation) => operation.path))]
    .map((routePath) => `  | ${literal(routePath)}`)
    .join('\n')
  const methodTypes = [...new Set(operations.map((operation) => operation.method))]
    .map((method) => `  | ${literal(method)}`)
    .join('\n')
  const operationTypes = operations
    .map((operation) => (
      `  | { method: ${literal(operation.method)}; path: ${literal(operation.path)}; operationId: ${literal(operation.operationId)} }`
    ))
    .join('\n')

  return `// Generated by scripts/generate-openapi-types.mjs. Do not edit manually.\n\n`
    + `export const openApiOperations = ${JSON.stringify(operations, null, 2)} as const\n\n`
    + `export type OpenApiPath =\n${pathTypes}\n\n`
    + `export type OpenApiMethod =\n${methodTypes}\n\n`
    + `export type OpenApiOperation =\n${operationTypes}\n`
    + `\n${renderSchemaTypes(schema)}`
}

const schemaPath = path.join(os.tmpdir(), `kamera-openapi-${process.pid}.json`)

try {
  runOpenApiExport(schemaPath)
  const schema = JSON.parse(fs.readFileSync(schemaPath, 'utf8'))
  const nextContent = render(schema)
  const currentContent = fs.existsSync(outputPath) ? fs.readFileSync(outputPath, 'utf8') : ''

  if (checkOnly) {
    if (currentContent !== nextContent) {
      throw new Error('OpenAPI generated types are stale. Run npm run generate:api-types.')
    }
  } else {
    fs.writeFileSync(outputPath, nextContent, 'utf8')
    console.log(`Generated ${path.relative(frontendRoot, outputPath)}`)
  }
} finally {
  fs.rmSync(schemaPath, { force: true })
}
