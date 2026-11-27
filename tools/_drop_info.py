import io, re

def drop_blocks(path, anchors):
    """anchors: list of unique text found inside an info block to delete."""
    lines = io.open(path, encoding="utf-8").read().split("\n")
    for a in anchors:
        idx = None
        for i, l in enumerate(lines):
            if a in l and not l.strip().startswith("if(") and "out +=" not in l and ".map(" not in l:
                idx = i
                break
        if idx is None:
            print("MISS", path, a)
            continue
        # 위로 올라가 <div class="info"> 찾기
        s = idx
        while s >= 0 and '<div class="info"' not in lines[s]:
            s -= 1
        if s < 0:
            print("NOOPEN", path, a)
            continue
        # 아래로 내려가 짝 </div> 찾기
        e = s
        while e < len(lines) and lines[e].strip() != "</div>":
            e += 1
        # 앞의 빈 줄까지
        if s > 0 and lines[s - 1].strip() == "":
            s -= 1
        del lines[s:e + 1]
    io.open(path, "w", encoding="utf-8").write("\n".join(lines))
    print("cleaned", path)

# index.html — 집계 기준 / 신청·응모 기준 / 짠테크 기준 / 공모주 원칙 / 공모주 기준
drop_blocks("index.html", ["<b>집계 기준</b>", "<b>신청·응모 기준</b>",
                           "<b>체험단 당첨 가치 71,720원</b> = 오르골 33,900 + 디베이저 2ml 10,400(무신사)",
                           "<b>공모주 원칙</b>", "철회 4건은 각 공시일 기준(마지막 에이엔에이치스트럭쳐"])
# jobs.html — 기준
drop_blocks("jobs.html", ['id="jobsInfo"'])
# flights.html — 기준 · 유의
drop_blocks("flights.html", ["<b>기준 · 유의</b>"])
# meals.html — 메모
drop_blocks("meals.html", ["<b>메모</b>"])
