import re
p = "/workspace/build/apply-dashboard/flights.html"
s = open(p, encoding="utf-8").read()

start = s.index('  <div class="grid">\n<div class="s">')
end = s.index('  <div class="filters"', start)
new = '''  <div class="grid">
    <div class="card"><div class="k">최저 2인 왕복</div><div class="v" id="vBest">265,200<small>원</small></div><div class="s">김해→제주 · 에어부산 06:50→07:55 직항</div></div>
    <div class="card"><div class="k">특가 근접</div><div class="v c-red" id="vMerit">0<small>개</small></div><div class="s">6노선 모두 목표가 위 · 제주 1인 13.3만~18.7만</div></div>
    <div class="card"><div class="k">실측 노선</div><div class="v" id="vRoutes">6<small>개</small></div><div class="s">대마도 항공 없음 · 배편만</div></div>
    <div class="card"><div class="k">어제 대비</div><div class="v c-orange" id="vDiff">+20,000</div><div class="s">김해→후쿠오카만 상승 · 제주 3노선 그대로</div></div>
  </div>

'''
s = s[:start] + new + s[end:]

reps = [
    ('class="basis">2026-11-27 17:44~17:50 실측 · 2027-03-05~07</div>',
     'class="basis">2026-11-28 08:00~08:15 실측 · 2027-03-05~07</div>'),
    ('out:"2027-03-05~07 · 김해(PUS) · 에어부산 직항 18:00→18:55 · 오전 570,776원에서 +11,824(+2.1%)"',
     'out:"2027-03-05~07 · 김해(PUS) · 에어부산 직항 18:00→18:55 · 어제보다 +20,000 (탭 582,600원)"'),
    ('out:"2027-03-05~07 · 청주(CJJ) · 제주항공 직항 19:15→20:25 · 최저가 탭 303,150원"',
     'out:"2027-03-05~07 · 청주(CJJ) · 제주항공 직항 19:15→20:25 · 최저가 탭 302,451원"'),
    ('state:"ok", price:799600, carrier:"Trinity"', 'state:"ok", price:885200, carrier:"Trinity"'),
    ('out:"2027-03-05~07 · 대구(TAE) · Trinity 직항 17:50→19:00 · 오전 값 그대로, 세 출발지 중 최고가"',
     'out:"2027-03-05~07 · 대구(TAE) · Trinity 직항 17:50→19:00 · 직항 2편뿐, 나머지는 인천경유 121만~135만"'),
    ('state:"ok", price:704800, carrier:"Aero K"', 'state:"ok", price:723400, carrier:"Aero K"'),
    ('out:"2027-03-05~07 · 청주(CJJ) · Aero K 직항 06:25→07:35 · 최저가 탭 704,800원, 특가 아님"',
     'out:"2027-03-05~07 · 청주(CJJ) · Aero K 직항 06:25→07:35 · 노출가만 -80,841, 탭은 704,560원"'),
    ('note:"항공 없음 → 부산항 배편. 2인 금~일 왕복 추정 52~55만 원(승선권 40만 + 유류·터미널·출국세). 2027년 3월 시간표·운임 미공개."',
     'note:"항공 없음 → 부산항 배편. 대아고속해운 27년 3월 예약 열림 · 2인 금~일 정규 추정 49~50만 원, 실견적 미조회."'),
    ('<footer>2026-11-27 17:44~17:50 실측 · 성인 2인 왕복·세금 포함 · 다음 실측 11/28 08:00 · 검색 비공개 페이지</footer>',
     '<footer>2026-11-28 08:00~08:15 실측 · 성인 2인 왕복·세금 포함 · 다음 실측 11/29 08:00 · 검색 비공개 페이지</footer>'),
]
for a, b in reps:
    if a in s:
        s = s.replace(a, b)
    else:
        print("MISS:", a[:60])
open(p, "w", encoding="utf-8").write(s)
print("done", len(s))
