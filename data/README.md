# 스냅샷 도구 변경 메모 (2026-11-25)

## 무엇이 바뀌었나
- `tools/snapshot.py`에 `data/flights_history.json` 자동 누적이 붙었다.
- `python3 tools/snapshot.py`를 돌리면 다음 두 가지가 같이 갱신된다.
  1. `history/YYYY-MM-DD.json` (기존과 동일)
  2. `data/flights_history.json` → `flights.html`의 `FLIGHTS` 중 `state:"ok"`(실측된) 노선만 골라 시각별 가격 한 줄 추가

## 규칙
- 같은 날 같은 값이면 새 줄을 만들지 않고 `t`(시각)만 갱신한다 → 08:00·18:00 중 마지막 시각이 남는다.
- `state:"wait"`(18시 실측 예정) 노선은 값이 없으므로 쌓지 않는다.
- 노선 id는 `FLIGHTS[].id`(예: `PUS-FUK`)를 쓴다. id가 없으면 `route` 문자열 `김해(PUS) → 후쿠오카(FUK)`에서 만든다.
- 노선당 최대 240줄까지만 남긴다.
- `--from-dir`로 다른 폴더를 읽을 때는 누적하지 않는다(테스트·과거 재생성 보호).

## 페이지 쪽
- `flights.html`은 `data/flights_history.json`을 fetch해서 노선 카드의 스파크라인·전일 대비 증감을 그린다.
- 파일이 없거나 실패하면 카드에서 추이 줄만 빠지고 가격·가격 위치 바·배지는 그대로 나온다.
- 따라서 브리핑에서는 지금처럼 `flights.html`의 `FLIGHTS` 값만 최신 실측으로 고치고 `tools/snapshot.py`를 돌리면 추이가 자동으로 쌓인다.
