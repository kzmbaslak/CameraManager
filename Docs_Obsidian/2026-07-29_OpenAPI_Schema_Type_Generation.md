# 2026-07-29 OpenAPI Schema Type Generation

- Frontend OpenAPI generator artik endpoint/path tiplerine ek olarak backend `components.schemas` sozlesmesini `OpenApiSchemas` TypeScript haritasina donusturur.
- `OpenApiSchemas["CameraResponse"]`, `OpenApiSchemas["AlarmResponse"]` ve request semalari frontend tarafinda backend Pydantic modelleriyle ayni kaynaktan izlenebilir.
- Contract testi uretilmis sema tiplerinin stale kalmasini ve kritik kamera/alarm modellerinin kaybolmasini engeller.
