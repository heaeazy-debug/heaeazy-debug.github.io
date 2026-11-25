#!/usr/bin/env python3
"""현황판 3페이지에서 그날 데이터를 뽑아 history/YYYY-MM-DD.json + history/index.json을 만든다.

사용법
  python3 tools/snapshot.py                # 오늘(KST) 날짜로 현재 페이지 상태를 저장
  python3 tools/snapshot.py 2026-11-25     # 날짜 지정
  python3 tools/snapshot.py 2026-11-22 --from-dir .oldsnap/2026-11-22
                                          # 다른 폴더의 index.html·jobs.html·meals.html에서 추출

원칙
  - 수치는 페이지에 적힌 값을 그대로 옮긴다(계산해서 새 숫자를 만들지 않는다).
  - 이미 저장된 JSON이 있으면 사람이 쓴 summary·notes는 보존하고 수치만 갱신한다.
  - index.json은 history/*.json의 date·summary로 다시 만든다(최신 날짜가 맨 앞).
"""
import json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIST = os.path.join(ROOT, "history")
DATA = os.path.join(ROOT, "data")
FLIGHT_HIST = os.path.join(DATA, "flights_history.json")

# ── 아주 작은 JS 리터럴 파서 (const NAME = [ ... ]; 를 읽는다) ──────────
class JS:
    def __init__(self, s):
        self.s, self.i = s, 0

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n,":
            self.i += 1

    def value(self):
        self.ws()
        c = self.s[self.i]
        if c == "[":
            return self.array()
        if c == "{":
            return self.obj()
        if c in "\"'":
            return self.string()
        if c == "`":
            return self.template()
        m = re.match(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            n = m.group(0)
            return float(n) if "." in n else int(n)
        m = re.match(r"[A-Za-z_$][\w$]*", self.s[self.i:])
        if m:
            self.i += len(m.group(0))
            w = m.group(0)
            return {"true": True, "false": False, "null": None, "undefined": None}.get(w)

    def string(self):
        q = self.s[self.i]; self.i += 1; out = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "\\":
                nxt = self.s[self.i + 1]
                out.append({"n": "\n", "t": "\t", "r": "\r"}.get(nxt, nxt))
                self.i += 2
                continue
            if c == q:
                self.i += 1
                return "".join(out)
            out.append(c); self.i += 1
        return "".join(out)

    def template(self):
        self.i += 1; out = []
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "\\":
                out.append(self.s[self.i + 1]); self.i += 2; continue
            if c == "`":
                self.i += 1; break
            out.append(c); self.i += 1
        return "".join(out)

    def array(self):
        self.i += 1; out = []
        while True:
            self.ws()
            if self.s[self.i] == "]":
                self.i += 1; return out
            out.append(self.value())

    def obj(self):
        self.i += 1; out = {}
        while True:
            self.ws()
            if self.s[self.i] == "}":
                self.i += 1; return out
            c = self.s[self.i]
            if c in "\"'":
                k = self.string()
            elif c == "`":
                k = self.template()
            else:
                m = re.match(r"[A-Za-z_$][\w$]*", self.s[self.i:])
                k = m.group(0); self.i += len(k)
            self.ws()
            if self.s[self.i] == ":":
                self.i += 1
            out[k] = self.value()


def js_var(src, name):
    m = re.search(r"\b(?:const|let|var)\s+" + re.escape(name) + r"\s*=\s*", src)
    if not m:
        return None
    return JS(src[m.end():]).value()


# ── HTML 도우미 ───────────────────────────────────────────────────────
def inner(html, id_):
    m = re.search(r'<(\w+)[^>]*\bid="' + re.escape(id_) + r'"[^>]*>', html)
    if not m:
        return ""
    tag, i = m.group(1), m.end()
    depth, j = 1, i
    pat = re.compile(r"<(/?)" + tag + r"\b[^>]*>", re.I)
    while depth:
        mm = pat.search(html, j)
        if not mm:
            return html[i:]
        depth += -1 if mm.group(1) else 1
        j = mm.end()
    return html[i:j - len(mm.group(0))]


def text(h):
    h = re.sub(r"<br\s*/?>", " ", h or "")
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r"\s+", " ", h).strip()


def num(h):
    t = text(h).replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", t)
    if not m:
        return None
    v = m.group(0)
    return float(v) if "." in v else int(v)


def info_blocks(html):
    out = []
    for m in re.finditer(r'<div class="info">(.*?)</ul>', html, re.S):
        body = m.group(1)
        t = re.search(r"<b>(.*?)</b>", body, re.S)
        items = [text(li) for li in re.findall(r"<li>(.*?)</li>", body, re.S)]
        if items:
            out.append({"title": text(t.group(1)) if t else "", "items": items})
    return out


def sum_notes(html):
    return [text(x) for x in re.findall(r'<div class="sum-note">(.*?)</div>', html, re.S)]


def money_cards(html):
    out = []
    for m in re.finditer(r'<div class="k">(.*?)</div>\s*<div class="v[^"]*">(.*?)</div>\s*<div class="s">(.*?)</div>', html, re.S):
        k, v, s = text(m.group(1)), m.group(2), text(m.group(3))
        vv = text(v)
        if k and vv:
            out.append({"k": k, "v": vv, "s": s})
    return out


def labeled_cards(html, labels):
    """<div class="k">라벨</div><div class="v...">값<small>단위</small></div><div class="s">설명</div>"""
    res = {}
    for lab in labels:
        m = re.search(r'<div class="k">\s*' + re.escape(lab) + r'\s*</div>\s*<div class="v[^"]*">(.*?)</div>\s*<div class="s">(.*?)</div>', html, re.S)
        if m:
            res[lab] = {"v": text(m.group(1)), "s": text(m.group(2))}
    return res


# ── 페이지별 추출 ────────────────────────────────────────────────────
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def parse_bonus(html):
    clean = strip_scripts(html)
    ch = js_var(html, "CHANNELS") or []
    remain = js_var(html, "REMAIN") or []
    rzero = js_var(html, "REMAIN_ZERO") or []
    stock = js_var(html, "STOCK") or []
    stock_today = js_var(html, "STOCK_TODAY")
    money_view = inner(clean, "viewMoney") or clean

    kpi = {}
    for key, id_ in [("total", "vTotal"), ("done", "vDone"), ("win", "vWin"), ("rate", "vRate"),
                     ("wait", "vWait"), ("wait13", "sWait13"), ("soon", "sSoon"), ("today", "sToday"),
                     ("contest", "sContest"), ("web", "sWeb"), ("remain", "rTotal"),
                     ("remainWeb", "rWeb"), ("remainApp", "rApp")]:
        h = inner(clean, id_)
        if h:
            kpi[key] = h.replace("<small>", "").replace("</small>", "").strip()
            if key in ("rate",):
                kpi[key] = kpi[key].replace("%", "")

    basis = re.search(r'class="basis">(.*?)</div>', clean, re.S)
    headline = [text(x) for x in re.findall(r'<div class="sumline">(.*?)</div>', clean, re.S)]
    return {
        "basis": text(basis.group(1)) if basis else "",
        "kpi": kpi,
        "kpiText": labeled_cards(clean, ["총 제출", "발표 완료", "당첨", "당첨률", "발표 대기", "대표 할 일",
                                        "남은 신청 가능 (신청 대기)"]),
        "channels": ch,
        "remain": remain,
        "remainZero": rzero,
        "stock": {"today": stock_today, "events": stock,
                  "headline": headline, "notes": info_blocks(inner(clean, "viewStock"))},
        "money": [m for m in money_cards(money_view) if len(m["v"]) <= 14][:6],
        "notes": info_blocks(inner(clean, "viewContest")),
        "moneyNotes": info_blocks(inner(clean, "viewMoney")),
        "sumNotes": sum_notes(clean),
    }


def parse_flights(html):
    """flights.html — 추적 조건·KPI·노선별 실측(FLIGHTS)·유의"""
    clean = strip_scripts(html)
    flights = js_var(html, "FLIGHTS") or []
    basis = re.search(r'class="basis">(.*?)</div>', clean, re.S)
    kpi = {}
    for key, id_ in [("best", "vBest"), ("merit", "vMerit"), ("routes", "vRoutes"), ("diff", "vDiff")]:
        h = inner(clean, id_)
        if h:
            kpi[key] = text(h)
    cond = [text(c) for c in re.findall(r'<span class="chip[^"]*">(.*?)</span>', clean, re.S)]
    infos = info_blocks(clean)
    return {
        "basis": text(basis.group(1)) if basis else "",
        "conditions": cond,
        "kpi": kpi,
        "count": len(flights),
        "routesList": flights,
        "notes": infos[-1]["items"] if infos else [],
    }


def flight_id(f):
    """노선 id — FLIGHTS의 id를 우선 쓰고, 없으면 '김해(PUS) → 후쿠오카(FUK)'에서 만든다."""
    if isinstance(f, dict) and f.get("id"):
        return str(f["id"])
    route = (f or {}).get("route", "") if isinstance(f, dict) else ""
    m = re.search(r"\(([A-Z]{3})\)\s*→\s*[^()]*\(([A-Z]{3})\)", route)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def append_flights_history(flights, stamp):
    """flights.html의 FLIGHTS에서 실측 노선만 골라 data/flights_history.json에 시각별로 쌓는다.

    같은 날 같은 값이면 새 줄을 만들지 않고 시각만 갱신한다(하루 두 번 브리핑 대응).
    """
    data = {"updated": "", "basis": {}, "note": "", "routes": {}}
    if os.path.exists(FLIGHT_HIST):
        try:
            with open(FLIGHT_HIST, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    routes = data.setdefault("routes", {})
    added = 0
    for f in flights or []:
        if not isinstance(f, dict) or f.get("state") == "wait":
            continue
        p = f.get("price")
        rid = flight_id(f)
        if not rid or not isinstance(p, int):
            continue
        entry = routes.setdefault(rid, {
            "label": f.get("label") or f.get("route") or rid,
            "origin": f.get("from", ""),
            "dest": f.get("to", ""),
            "points": [],
        })
        pts = entry.setdefault("points", [])
        day = stamp[:10]
        last = pts[-1] if pts else None
        if last and last.get("p") == p and str(last.get("t", ""))[:10] == day:
            last["t"] = stamp
            if f.get("carrier") and f.get("carrier") != "—":
                last["c"] = f["carrier"]
            continue
        rec = {"t": stamp, "p": p}
        if f.get("carrier") and f.get("carrier") != "—":
            rec["c"] = f["carrier"]
        pts.append(rec)
        added += 1
    for entry in routes.values():
        pts = entry.get("points") or []
        pts.sort(key=lambda x: str(x.get("t", "")))
        if len(pts) > 240:
            entry["points"] = pts[-240:]
    data["updated"] = stamp
    os.makedirs(DATA, exist_ok=True)
    with open(FLIGHT_HIST, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"flights_history: +{added} → {os.path.relpath(FLIGHT_HIST, ROOT)}")


def parse_today(html):
    """today.html — 8대 항목 브리핑(BRIEF) + KPI"""
    clean = strip_scripts(html)
    brief = js_var(html, "BRIEF") or {}
    basis = re.search(r'class="basis">(.*?)</div>', clean, re.S)
    kpi = {}
    for key, id_ in [("weather", "vTodayWeather"), ("schedule", "vTodaySched"),
                     ("air", "vTodayAir"), ("remain", "vTodayRemain")]:
        h = inner(clean, id_)
        if h:
            kpi[key] = text(h)
    infos = info_blocks(clean)
    return {
        "basis": text(basis.group(1)) if basis else "",
        "kpi": kpi,
        "brief": brief,
        "notes": infos[-1]["items"] if infos else [],
    }


def parse_jobs(html):
    clean = strip_scripts(html)
    jobs = js_var(html, "JOBS") or []
    etc = js_var(html, "ETC") or []
    basis = re.search(r'class="basis">(.*?)</div>', clean, re.S)
    cond = [text(c) for c in re.findall(r'<span class="chip[^"]*">(.*?)</span>', clean, re.S)]
    return {
        "basis": text(basis.group(1)) if basis else "",
        "conditions": cond,
        "kpi": labeled_cards(clean, ["추적 공고", "마감 임박", "요건 리스크"]),
        "tracked": len(jobs),
        "jobs": jobs,
        "excluded": etc,
        "notes": info_blocks(clean),
    }


def parse_meals(html):
    clean = strip_scripts(html)
    wk_prev = js_var(html, "WEEK_PREV") or []
    wk_cur = js_var(html, "WEEK_CUR") or []
    shop = js_var(html, "SHOP") or []
    adjust = js_var(html, "ADJUST") or []
    basis = re.search(r'class="basis">(.*?)</div>', clean, re.S)
    sumline = re.search(r'<div class="sumline"[^>]*>(.*?)</div>', clean, re.S)
    paid = re.search(r'<div class="pv">(.*?)</div>', clean, re.S)
    remain = re.search(r'<div class="rm-t">(.*?)</div>\s*<div class="rm-d">(.*?)</div>', clean, re.S)
    return {
        "basis": text(basis.group(1)) if basis else "",
        "weekPrev": wk_prev,
        "weekCur": wk_cur,
        "shop": shop,
        "adjust": adjust,
        "sumline": text(sumline.group(1)) if sumline else "",
        "paid": text(paid.group(1)) if paid else "",
        "remainTask": {"t": text(remain.group(1)), "d": text(remain.group(2))} if remain else None,
        "notes": info_blocks(clean),
    }


def weekday_kr(date):
    return "월화수목금토일"[datetime.date.fromisoformat(date).weekday()]


def today_file_name(src_dir):
    """오늘 브리핑 페이지는 today.html(또는 briefing.html) 중 있는 것을 쓴다."""
    for name in ("today.html", "briefing.html"):
        if os.path.exists(os.path.join(src_dir, name)):
            return name
    return "today.html"


def strip_scripts(html):
    return re.sub(r"<script>.*?</script>", "", html, flags=re.S)


def build(date, src_dir):
    idx = read(os.path.join(src_dir, "index.html"))
    jbs = read(os.path.join(src_dir, "jobs.html"))
    mls = read(os.path.join(src_dir, "meals.html"))
    flg_path = os.path.join(src_dir, "flights.html")
    tdy_path = os.path.join(today_file_name(src_dir))
    flg = read(flg_path) if os.path.exists(flg_path) else ""
    tdy = read(tdy_path) if os.path.exists(tdy_path) else ""
    snap = {
        "date": date,
        "dw": weekday_kr(date),
        "bonus": parse_bonus(idx),
        "jobs": parse_jobs(jbs),
        "meals": parse_meals(mls),
        "summary": "",
        "isLatest": False,
    }
    if flg:
        snap["flights"] = parse_flights(flg)
    if tdy:
        snap["today"] = parse_today(tdy)
    k = snap["bonus"]["kpi"]
    parts = []
    if k.get("total") is not None:
        parts.append(f"총 제출 {k['total']}건")
    if k.get("win") is not None:
        parts.append(f"당첨 {k['win']}")
    if k.get("done") is not None:
        parts.append(f"발표 완료 {k['done']}")
    if k.get("remain") is not None:
        parts.append(f"남은 신청 {k['remain']}")
    if snap["jobs"]["jobs"]:
        parts.append(f"이직 추적 {len(snap['jobs']['jobs'])}건")
    snap["summary"] = " · ".join(parts) or "기록"
    return snap


def main():
    args = [a for a in sys.argv[1:]]
    src_dir = ROOT
    if "--from-dir" in args:
        i = args.index("--from-dir")
        src_dir = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d")
    date = args[0] if args else today

    snap = build(date, src_dir)
    if snap.get("flights", {}).get("routesList") and src_dir == ROOT:
        stamp = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).replace(microsecond=0).isoformat()
        append_flights_history(snap["flights"]["routesList"], stamp)
    os.makedirs(HIST, exist_ok=True)
    path = os.path.join(HIST, f"{date}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            old = json.load(f)
        for keep in ("summary", "title", "createdNote"):
            if old.get(keep):
                snap[keep] = old[keep]
        # 페이지에 구조로 남지 않는 값은 기존 파일 것을 이어 쓴다
        ost = old.get("bonus", {}).get("stock", {})
        nst = snap["bonus"]["stock"]
        if ost.get("withdrawn"):
            nst["withdrawn"] = ost["withdrawn"]
        if ost.get("events") and not nst.get("events"):
            snap["bonus"]["stock"] = ost
        elif ost.get("headline") and not nst.get("headline"):
            nst["headline"] = ost["headline"]
        for k in ("paid", "paidLabel", "remainTask"):
            if old.get("meals", {}).get(k):
                snap["meals"][k] = old["meals"][k]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)

    sync_index()
    print(f"wrote {os.path.relpath(path, ROOT)}")


def sync_index():
    """history/*.json → history/index.json (최신 날짜 먼저)"""
    rows = []
    for fn in sorted(os.listdir(HIST), reverse=True):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", fn):
            continue
        with open(os.path.join(HIST, fn), encoding="utf-8") as f:
            s = json.load(f)
        d = s["date"]
        rows.append({
            "date": d,
            "dw": s.get("dw") or weekday_kr(d),
            "label": f"{d} ({s.get('dw') or weekday_kr(d)})",
            "summary": s.get("summary", ""),
            "isLatest": d == rows[0]["date"] if False else False,
            "hasBonus": bool(s.get("bonus", {}).get("channels")),
            "hasJobs": bool(s.get("jobs", {}).get("jobs")),
            "hasMeals": bool(s.get("meals", {}).get("weekCur")),
            "hasFlights": bool(s.get("flights", {}).get("routesList")),
            "hasToday": bool(s.get("today", {}).get("brief")),
        })
    rows.sort(key=lambda r: r["date"], reverse=True)
    if rows:
        rows[0]["isLatest"] = True
    out = {
        "updated": max(r["date"] for r in rows) if rows else "",
        "count": len(rows),
        "dates": rows,
    }
    with open(os.path.join(HIST, "index.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote history/index.json (" + ", ".join(r["date"] for r in rows) + ")")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sync-index":
        sync_index()
    else:
        main()
