# 2026-07-30 OpenAPI Type Adoption

- Frontend `api.ts` enum, `BoundingBox`, `CameraCreate` ve bazi kamera request tiplerini `OpenApiSchemas[...]` kaynagina baglamaya basladi.
- NVR create ve scan request tipleri de generated OpenAPI semalarindan beslenir.
- NVR kanal import payload tipi generated OpenAPI semasindan beslenir.
- Kamera, NVR ve kullanici update payload tipleri generated OpenAPI semalarindan beslenir.
- Alarm update, alarm resolve ve threshold uygulama payload tipleri generated OpenAPI semalarindan beslenir.
- Auth login ve change-password payload tipleri generated OpenAPI semalarindan beslenir; frontend auth API artik change-password endpoint'ini de kapsar.
- User create tipi generated OpenAPI semasina baglandi.
- User role tipi generated OpenAPI enum'una baglandi; Settings rol secimi backend enum degerleriyle tip seviyesinde hizalidir.
- `camerasApi` toplu AI payload tipi `CameraBulkAiSettingsRequest` generated semasini kullanir.
- Contract testi manuel tiplerin generated OpenAPI sema haritasini kullanmaya devam ettigini denetler.
