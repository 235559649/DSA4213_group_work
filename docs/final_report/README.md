# DSA4213 Group 25 — Final Report 骨架

直接上传整个文件夹到 Overleaf（或本地 `latexmk -pdf main.tex`）即可编译。
红色 `[TODO: ...]` 是待写内容；每个 `.tex` 文件开头的注释写明了负责人、页数预算、对应的 PPT slide 和必须交代的要点。

## 分工（按仓库里的 1–5 号角色）

| 人 | 文件 | 页数 |
|---|---|---|
| 1 号 Agent 集成 | `03_setup.tex`、`07_repro.tex`、`figures/architecture.pdf`（slide 3 导出）、Appendix A.1；补 GitHub README 和运行材料 | ~1.1 |
| 2 号 索引/结构 | `04_design.tex` 的 4.1–4.3、Appendix A.2 | ~1.0 |
| 3 号 BM25/提示 + 总编 | `01_problem.tex`、`02_related.tex`、`00_admin_summary.tex`、`08_conclusion.tex`；统一术语、压页数 | ~2.0 |
| 4 号 失败反馈 D | `04_design.tex` 的 4.4、`06_analysis.tex`（成本段除外）、Appendix A.6 | ~1.6 |
| 5 号 评估 | `05_results.tex`、`06_analysis.tex` 的 Costs 段、Appendix A.3–A.5 | ~2.3 |

## 规则

1. 每人只改自己的文件，不要动 `main.tex` 的字号、页边距和行距设置。
2. 表格里的数字目前抄自 PPT，5 号负责对照 `run_comparison.py` 和评估报告的输出逐一核对。
3. 交叉核对的配对：1↔2，3↔4，5↔总编。
4. 主文（从开头到 Contribution Statement 之前）严格不超过 8 页，超出的内容移到 Appendix。
5. 提交前必须完成：
   - `grep -rn "todo" sections/` 结果为空；
   - 删掉 `main.tex` 里的 `\nocite{*}`；
   - Contribution Statement 由 5 人一起填写，比例总和为 100。
