# 预实验报告索引

> 精简提交版：报告结论与数值不变。完整轨迹、排名、D 事件和官方测试全文位于独立证据包；标为“归档文件”的链接提供包内路径与哈希。下载后复算方法见 [完整证据说明](../docs/FULL_EVIDENCE.md)。

三份报告均为 Markdown，不生成 HTML。它们描述开发阶段结果，不是正式留出集验证。

| 报告 | 范围 | 核心观察 |
|---|---|---|
| [01 原始八题](01_original_eight_tasks.md) | 原五题 + 原三题；32 个入选运行 | A/B/C/D 为 5/8、4/8、4/8、4/8，定位改进尚未带来总体优势 |
| [02 三题 D 演进](02_three_task_d_evolution.md) | 原三题 ABCD + 第一次仅 D + 第二次 ABCD | D 成功数 1/3 → 1/3 → 0/3；证据捕捉改善与最终修复质量分开判断 |
| [03 四题提示策略](03_four_task_prompt_policy.md) | 最新四题 ABCD 对齐历史同四题 | A/B 从 2/4 降为 1/4，C/D 从 1/4 升为 2/4；成功总量未净增 |

第二、三份报告复用了第一份中的题目；总计仍是 8 道不同题。第一次 D 修复没有同期 A/B/C。跨版本共用系统提示和 D 机制也发生变化，不能把全部变化归因于单一因素。

D 耗时在第二、三份报告中分别列出初始定位、反馈处理、事件级处理和总运行时间。原始实验缺失的新字段保持未知。每份报告均保留逐题轨迹讨论和证据入口。

已复算的全量结果见 [analysis.json](../results/analysis.json)、[run_summary.csv](../results/run_summary.csv)、[feedback_events.csv](../results/feedback_events.csv)。全部运行身份见 [evidence/INDEX.md](../evidence/INDEX.md)。
