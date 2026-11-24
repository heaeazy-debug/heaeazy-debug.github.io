# 현황판 날짜별 기록(아카이브) 갱신 안내

매일 08:00·18:00 브리핑에서 **다섯 페이지(today.html·index.html·jobs.html·meals.html·flights.html)를 고친 뒤 아래 3줄만 하면** 그날 기록이 남는다.

```bash
cd build/apply-dashboard
python3 tools/snapshot.py            # 오늘 날짜(한국 시간)로 history/YYYY-MM-DD.json + history/index.json 생성
git add -A && git commit -m "현황판 $(date +%m/%d) 갱신" && git push
```

## 구조

| 파일 | 내용 |
| --- | --- |
| `index.html` · `jobs.html` · `meals.html` · `flights.html` · `today.html` | 항상 **최신** 화면. 이 다섯 파일이 그날 숫자의 원본이다. |
| `history/YYYY-MM-DD.json` | 그날 스냅샷(부수익·이직·식단·항공권·오늘 브리핑). 페이지 상단 `📅 기록 보기`가 이 파일을 읽는다. |
| `history/index.json` | 저장된 날짜 목록 + 그날 한 줄 요약. `tools/snapshot.py`가 자동으로 다시 만든다. |
| `tools/snapshot.py` | 세 페이지에서 수치·카드·공모주 일정·이직·식단을 뽑아 JSON으로 저장. |

## 절차

1. **페이지를 먼저 고친다.** `index.html`의 `CHANNELS`·`REMAIN`·`STOCK`, KPI 숫자와 기준 문장, `jobs.html`의 `JOBS`·`ETC`, `meals.html`의 `WEEK_PREV`·`WEEK_CUR`·`SHOP`, `flights.html`의 `FLIGHTS`, `today.html`의 `BRIEF`가 원본이다.
2. `python3 tools/snapshot.py` 실행 → `history/<오늘>.json`과 `history/index.json`이 갱신된다(항공권 `flights`·오늘 브리핑 `today` 포함).
   - 이미 파일이 있으면 사람이 쓴 `summary`(한 줄 요약)는 보존되고 수치만 새로 읽는다.
   - 날짜를 직접 지정하려면 `python3 tools/snapshot.py 2026-11-25`.
3. `history/YYYY-MM-DD.json`의 `summary` 한 줄만 손으로 다듬는다(그날 한 줄 요약, 기록 선택기에 그대로 보인다).
4. 공모주 `withdrawn`(철회 종목)과 서술형 메모처럼 페이지에 구조로 없는 값은 필요할 때 JSON에 직접 채운다.
5. 커밋·푸시 → GitHub Pages 반영(1분 내).

## 확인

- `https://heaeazy-debug.github.io/` → 상단 `📅 기록 보기`에서 날짜를 바꾸면 과거 화면이 뜨고 `과거 기록 열람 중 · [최신으로]` 배너가 보인다.
- 과거 화면은 `?d=2026-11-23`처럼 주소로도 열린다.
- `history/index.json`의 첫 항목이 항상 최신이고, 그 날짜가 "최신" 화면이다.
- 파일을 직접 열면(오프라인) 기록 목록을 못 읽어 최신 화면만 보인다 — 정상 동작.

## 주의

- 공개 페이지다. 이름·연락처·이메일·회사명은 페이지에도 기록 JSON에도 넣지 않는다. 전화번호는 끝 4자리만.
- 기록 JSON은 그날 화면을 그대로 복사한 것이라, 나중에 숫자를 고쳐도 **과거 기록은 그대로** 남는다(그게 목적이다).
