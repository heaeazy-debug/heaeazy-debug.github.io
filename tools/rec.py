#!/usr/bin/env python3
"""flights.html의 FLIGHTS에서 '추천 노선' 1개를 계산해 KPI 1번 카드 HTML을 찍는다.

사용법
  python3 tools/rec.py          # 추천 노선·점수표·붙여넣을 카드 HTML
  python3 tools/rec.py --check  # 지금 flights.html 카드가 계산값과 같은지만 확인(다르면 exit 1)

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


def pick(flights):
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
    top = rows[0]
    cheapest = min(ms, key=lambda f: f["price"])
    nearest = min(rows, key=lambda x: x["r"])
    why = (f"{len(ms)}노선 최저가" if cheapest["id"] == top["f"]["id"]
           else "목표가 근접 1위" if nearest["f"]["id"] == top["f"]["id"] else "가성비 1위")
    return {"route": top["f"], "score": top["score"], "why": why}, rows


def label(f):
    lab = f.get("label") or f"{f.get('from', '')} → {f.get('to', '')}"
    return re.sub(r"\s*→\s*", "→", lab)


def kpi_parts(rec):
    f = rec["route"]
    carrier = f.get("carrier") or ""
    sub1 = label(f) + (f" · {carrier}" if carrier else "")
    sub2 = f"{f.get('dep', '')} 출발 · {rec['why']}"
    return f"{f['price']:,}", sub1, sub2


def kpi_html(rec):
    big, sub1, sub2 = kpi_parts(rec)
    return (f'<div class="card"><div class="k">추천 노선</div>'
            f'<div class="v c-blue" id="vRec">{big}<small>원</small></div>'
            f'<div class="s" id="vRecSub">{sub1}<br>{sub2}</div></div>')


def main():
    path = os.path.join(ROOT, "flights.html")
    html = open(path, encoding="utf-8").read()
    flights = js_var(html, "FLIGHTS") or []
    rec, rows = pick(flights)
    if not rec:
        print("실측 노선 없음 — 추천 계산 불가")
        return 1
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
    print(f"점수 {rec['score']:.1f}  (목표가 {rows[0]['near']:.1f} + 가격 {rows[0]['price']:.1f} + 시간대 {rows[0]['time']:.1f})")
    print("\n점수표")
    for i, r in enumerate(rows, 1):
        x = r["f"]
        print(f" {i}. {label(x):<12} {x['price']:>9,}원  목표가 {r['r']:.2f}배  "
              f"출발 {str(x.get('dep', '—')):>5}  →  {r['score']:5.1f}")
    print("\n붙여넣을 카드 HTML (flights.html KPI 1번)")
    print("    " + kpi_html(rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
