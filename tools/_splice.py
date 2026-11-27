import sys
p = sys.argv[1]
newpath = sys.argv[2]
start_marker = sys.argv[3] if len(sys.argv) > 3 else "const BRIEF = {"
end_marker = sys.argv[4] if len(sys.argv) > 4 else "function esc("
s = open(p, encoding="utf-8").read()
new = open(newpath, encoding="utf-8").read().rstrip() + "\n"
i = s.index(start_marker)
j = s.index(end_marker)
s2 = s[:i] + new + "\n" + s[j:]
open(p, "w", encoding="utf-8").write(s2)
print("spliced", p, len(s), "->", len(s2))
