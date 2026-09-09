# 2026-09-09 System Response Schemas

- Backend `/health`, `/health/ready`, `/security/posture`, `/security/permissions` ve `/setup/status` endpoint'leri Pydantic response modeli kullanir.
- Sistem saglik, kurulum ve guvenlik durusu tipleri `system_schema.py` altinda tutulur; frontend tarafinda manuel interface yerine generated OpenAPI semalari kullanilir.
- Contract testi sistem response modellerinin OpenAPI'ya dahil oldugunu ve kritik security posture alanlarinin generated tiplerde bulundugunu denetler.
