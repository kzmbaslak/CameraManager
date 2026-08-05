# 2026-08-05 Recordings Query Stability

- Kayitlar sayfasinda `since` filtresi render sirasinda `dayjs()` ile yeniden uretildigi icin React Query key'i her render'da degisiyor ve `/api/recordings/` endpoint'i arka arkaya cagriliyordu.
- `rangeSince` artik `useMemo(() => dateRangeStart(range), [range])` ile yalnizca tarih araligi degistiginde hesaplanir.
- `queryParams` da memoize edilir; kamera, alarm, tarih araligi veya limit degismedikce sorgu anahtari sabit kalir.
- Contract testi `since` filtresinin stabil memo degerinden beslendigini denetler.
