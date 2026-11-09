"""Pull the per-run 'model calls before the first reference-file view' table
out of the Role 5 analysis page 06_exploration.html and write it as CSV.
Each cell in that page is 'distinct source files viewed / calls before first view'."""
import csv, html, re, sys
src, out = sys.argv[1], sys.argv[2]
t = open(src, encoding="utf8").read()
t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
cell = r"(\d+) / (\d+|未看)"
rows = re.findall(r"((?:django|sympy|sphinx|pytest)-\d+) " + " ".join([cell] * 4), t)
with open(out, "w", newline="", encoding="utf8") as f:
    w = csv.writer(f)
    w.writerow(["task", "condition", "source_files_viewed", "calls_before_first_view"])
    for r in rows:
        for i, cond in enumerate("ABCD"):
            v = r[2 + 2 * i]
            w.writerow([r[0], cond, r[1 + 2 * i], "" if v == "未看" else v])
print(len(rows), "tasks")
