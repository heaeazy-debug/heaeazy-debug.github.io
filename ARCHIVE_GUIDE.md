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
| `tools/rec.py` | `flights.html`의 `FLIGHTS`로 추천 노선 1개를 계산해 KPI 카드 HTML을 찍고(`--check`로 현재 카드와 대조). 메리트 있는 노선이 없으면 `추천 없음`을 찍는다. |

## 절차

1. **페이지를 먼저 고친다.** `index.html`의 `CHANNELS`·`REMAIN`·`STOCK`, KPI 숫자와 기준 문장, `jobs.html`의 `JOBS`·`ETC`, `meals.html`의 `WEEK_PREV`·`WEEK_CUR`·`SHOP`, `flights.html`의 `FLIGHTS`, `today.html`의 `BRIEF`가 원본이다.
   - 항공권은 최저가가 아니라 **추천 노선**이 맨 위다 — `FLIGHTS`의 `price`·`cut`·`dep`를 고친 뒤 `python3 tools/rec.py`가 찍은 HTML로 KPI 1번(`vRec`·`vRecSub`)을 맞추고 `python3 tools/rec.py --check`로 확인한다(`cut`=목표가, `dep`=그 값으로 탈 수 있는 가장 나은 출발 시각).
   - **추천 후보는 메리트 있는 노선(목표가 이하 또는 목표가 +15% 이내 = '특가 근접')뿐이다. 그런 노선이 하나도 없으면 억지로 고르지 않고 `추천 없음`으로 표시한다** — KPI 1번은 `추천 없음` / `N노선 모두 목표가 위 · 대기 권장`, 어느 노선 카드에도 `추천` 배지를 붙이지 않고, 목록은 `노선 · 가격순`으로 둔다. `today.html` 8번 항공권도 같은 기준으로 `추천 노선 …` 대신 `추천 없음 — N노선 모두 목표가 위 · 최저 … · 대기 권장`으로 적는다.
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

## 결정 버튼 · 메모 (응답 자동 저장)

`today.html` 맨 위 `오늘 마감 · 결정 필요` 박스는 항목별 **선택 버튼 + 메모 입력 + [저장]** 으로 응답을 받는다. 누른 내용은 `today.html`의 `FORM`(폼 ID·entry ID만 들어 있음)으로 Google Form에 바로 전송되고, `localStorage`(`apply-board-decide-YYYY-MM-DD`)에 그날 상태가 남아 새로고침해도 배지가 유지된다.

**같은 페이지를 매일 다시 만들 때 `BRIEF.decide.items`에 이 두 필드를 꼭 남긴다:**

| 필드 | 값 |
| --- | --- |
| `id` | 응답의 `item` 값(짧은 항목 식별명, 예: `무신사 디베이저 후기`) |
| `opts` | 그 항목에 맞는 버튼 이름 배열(예: `["등록 승인","수정","보류"]`) |

둘을 빼면 버튼은 `["확인","보류"]`, `item`은 항목 제목으로 나가니 항목마다 맞춰 적는다. `id`·`opts`가 없는 과거 기록 화면에는 버튼이 그려지지 않는다(읽기 전용).

응답 확인:

```bash
gog --account heaeazy@gmail.com forms responses list 17bVcBTLmfKeU4g4Y0BP0zrw6FnS0tKGXouFlcz-4EFI
```

`date`·`item`·`decision`·`memo` 네 칸으로 들어온다. `decision`은 누른 버튼 글자이거나, 버튼 없이 메모만 보내면 `메모`다.

## 주의

- 공개 페이지다. 이름·연락처·이메일·회사명은 페이지에도 기록 JSON에도 넣지 않는다. 전화번호는 끝 4자리만. 결정 버튼 코드에도 폼 ID·entry ID만 두고 계정 정보는 적지 않는다.
- 기록 JSON은 그날 화면을 그대로 복사한 것이라, 나중에 숫자를 고쳐도 **과거 기록은 그대로** 남는다(그게 목적이다).
