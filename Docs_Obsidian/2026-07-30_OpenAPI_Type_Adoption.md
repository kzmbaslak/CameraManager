# 2026-07-30 OpenAPI Type Adoption

- Frontend `api.ts` enum, `BoundingBox`, `CameraCreate` ve bazi kamera request tiplerini `OpenApiSchemas[...]` kaynagina baglamaya basladi.
- NVR create ve scan request tipleri de generated OpenAPI semalarindan beslenir.
- `camerasApi` toplu AI payload tipi `CameraBulkAiSettingsRequest` generated semasini kullanir.
- Contract testi manuel tiplerin generated OpenAPI sema haritasini kullanmaya devam ettigini denetler.
