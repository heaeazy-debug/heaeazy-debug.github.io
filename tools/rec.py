#!/usr/bin/env python3
"""flights.html의 FLIGHTS에서 '추천 노선' 1개를 계산해 KPI 1번 카드 HTML을 찍는다.

사용법
  python3 tools/rec.py          # 추천 노선·점수표·붙여넣을 카드 HTML
  python3 tools/rec.py --check  # 지금 flights.html 카드가 계산값과 같은지만 확인(다르면 exit 1)

규칙
  · 추천 후보는 '메리트 있는 노선'만이다 — 목표가 이하(gap ≤ 0) 또는 목표가 +15% 이내(gap ≤ 0.15,
    flights.html badgeOf의 '특가 근접'과 같은 기준). 그 후보 안에서 아래 점수 1위를 추천으로 띄운다.
  · 메리트 노선이 하나도 없으면 억지로 고르지 않고 '추천 없음'을 찍는다(어느 카드에도 '추천' 배지를 붙이지 않는다).

식은 flights.html의 recPick()·depBand()와 같다. 한쪽을 고치면 다른 쪽도 고친다.
  점수 = 40 × 목표가 근접도 + 30 × 가격 + 30 × 출발 시간대
  · 목표가 근접도 = clamp((2.5 - price/cut) / 1.5, 0, 1)   (목표가와 같으면 만점, 2.5배면 0)
  · 가격          = 최저가 / 그 노선 가격
  · 출발 시간대   = dep(그 값으로 탈 수 있는 가장 나은 출발 시각)로 아래 구간표
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from snapshot import js_var, inner, text  # 같은 파일에서 쓰는 파서 재사용

W = {"near": 40, "price": 30, "time": 30}
MERIT_GAP = 0.15          # 목표가 +15% 이내 = '특가 근접'(flights.html badgeOf와 같은 기준)
NONE_V = "추천 없음"


def dep_band(t):
    m = re.search(r"(\d{1,2}):(\d{2})", str(t or ""))
    if not m:
        return .8
    h = int(m.group(1)) + int(m.group(2)) / 60
    if h < 6.5:
        return .35
    if h < 8:
        return .6
    if h < 11:
        return .95
    if h < 20:
        return 1
    if h < 22:
        return .85
    return .5


def judge(f):
    """노선 하나의 특가 판정 — flights.html badgeOf()와 같은 기준."""
    gap = (f["price"] - f["cut"]) / (f["cut"] or 1)
    if gap <= 0:
        return "지금 예매"
    if gap <= MERIT_GAP:
        return "특가 근접"
    return "대기"


def has_merit(f):
    return f["price"] <= f["cut"] * (1 + MERIT_GAP)


def pick(flights):
    """메리트 있는 노선 중 점수 1위. 메리트가 없으면 {'none': True, ...}."""
    ms = [f for f in flights if isinstance(f.get("price"), (int, float)) and (f.get("cut") or 0) > 0]
    if not ms:
        return None, []
    min_p = min(f["price"] for f in ms)
    rows = []
    for f in ms:
        r = f["price"] / f["cut"]
        near = max(0, min(1, (2.5 - r) / 1.5))
        score = W["near"] * near + W["price"] * (min_p / f["price"]) + W["time"] * dep_band(f.get("dep"))
        rows.append({"f": f, "r": r, "score": score,
                     "near": W["near"] * near, "price": W["price"] * (min_p / f["price"]),
                     "time": W["time"] * dep_band(f.get("dep"))})
    rows.sort(key=lambda x: (-x["score"], x["f"]["price"]))

    cand = [r for r in rows if has_merit(r["f"])]
    if not cand:
        return {"route": None, "none": True, "count": len(ms),
                "cheapest": min(ms, key=lambda f: f["price"])}, rows

    top = cand[0]
    cheapest = min(cand, key=lambda r: r["f"]["price"])
    nearest = min(cand, key=lambda r: r["r"])
    why = ("메리트 유일" if len(cand) == 1
           else f"메리트 {len(cand)}노선 중 최저가" if cheapest["f"]["id"] == top["f"]["id"]
           else "목표가 근접 1위" if nearest["f"]["id"] == top["f"]["id"] else "가성비 1위")
    return {"route": top["f"], "score": top["score"], "row": top, "why": why}, rows


def label(f):
    lab = f.get("label") or f"{f.get('from', '')} → {f.get('to', '')}"
    return re.sub(r"\s*→\s*", "→", lab)


def none_parts(rec):
    """추천 없음 카드의 (큰 값, 보조 줄)."""
    return NONE_V, f"{rec['count']}노선 모두 목표가 위 · 대기 권장"


def kpi_parts(rec):
    f = rec["route"]
    carrier = f.get("carrier") or ""
    sub1 = label(f) + (f" · {carrier}" if carrier else "")
    sub2 = f"{f.get('dep', '')} 출발 · {rec['why']}"
    return f"{f['price']:,}", sub1, sub2


def kpi_html(rec):
    if rec.get("none"):
        big, sub = none_parts(rec)
        return (f'<div class="card"><div class="k">추천 노선</div>'
                f'<div class="v" id="vRec">{big}</div>'
                f'<div class="s" id="vRecSub">{sub}</div></div>')
    big, sub1, sub2 = kpi_parts(rec)
    return (f'<div class="card"><div class="k">추천 노선</div>'
            f'<div class="v c-blue" id="vRec">{big}<small>원</small></div>'
            f'<div class="s" id="vRecSub">{sub1}<br>{sub2}</div></div>')


def score_table(rows):
    out = ["점수표"]
    for i, r in enumerate(rows, 1):
        x = r["f"]
        out.append(f" {i}. {label(x):<12} {x['price']:>9,}원  목표가 {r['r']:.2f}배  "
                   f"출발 {str(x.get('dep', '—')):>5}  →  {r['score']:5.1f}  {judge(x)}")
    return "\n".join(out)


def main():
    path = os.path.join(ROOT, "flights.html")
    html = open(path, encoding="utf-8").read()
    flights = js_var(html, "FLIGHTS") or []
    rec, rows = pick(flights)
    if not rec:
        print("실측 노선 없음 — 추천 계산 불가")
        return 1

    if rec.get("none"):
        big, sub = none_parts(rec)
        want_s = re.sub(r"\s+", " ", sub)
        c = rec["cheapest"]
        line = (f"{big} — {rec['count']}노선 모두 목표가 위(목표가 +{int(MERIT_GAP * 100)}% 이내 메리트 0개). "
                f"최저 {label(c)} {c['price']:,}원")
        if "--check" in sys.argv:
            got_v, got_s = text(inner(html, "vRec")), text(inner(html, "vRecSub"))
            ok = got_v == big and got_s == want_s
            print(line)
            print("카드 일치" if ok else "카드 불일치 — tools/rec.py 출력 HTML로 교체 필요")
            print(f"  지금 카드: {got_v} / {got_s}")
            print(f"  계산값  : {big} / {want_s}")
            return 0 if ok else 1
        print(line)
        print(score_table(rows))
        print("\n붙여넣을 카드 HTML (flights.html KPI 1번)")
        print("    " + kpi_html(rec))
        return 0

    f = rec["route"]
    if "--check" in sys.argv:
        big, sub1, sub2 = kpi_parts(rec)
        got_big = text(inner(html, "vRec"))
        got_sub = text(inner(html, "vRecSub"))
        ok = got_big == f"{big}원" and got_sub == re.sub(r"\s+", " ", f"{sub1} {sub2}")
        print(f"추천: {label(f)} {f['price']:,}원 · {rec['why']}")
        print("카드 일치" if ok else "카드 불일치 — tools/rec.py 출력 HTML로 교체 필요")
        print(f"  지금 카드: {got_big} / {got_sub}")
        print(f"  계산값  : {big}원 / {sub1} {sub2}")
        return 0 if ok else 1

    print(f"추천 노선: {label(f)} · {f.get('carrier', '')} {f.get('dep', '')} 출발 · {rec['why']} — {f['price']:,}원 (2인 왕복)")
    r0 = rec["row"]
    print(f"점수 {rec['score']:.1f}  (목표가 {r0['near']:.1f} + 가격 {r0['price']:.1f} + 시간대 {r0['time']:.1f})")
    print()
    print(score_table(rows))
    print("\n붙여넣을 카드 HTML (flights.html KPI 1번)")
    print("    " + kpi_html(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
