# AI 使用说明（231880398 胡凌岳，E8-E10 A 轨）

## 使用的工具/场景
- 使用 AI 助手协助梳理 E8/E9/E10 A 轨手册步骤、组织服务器命令、定位 `lab.py/run_lab.py` 的实际 API（如 `demo`/`run_lab` 调用方式），并起草个人测试与提交文档结构。

## 人工确认与修改
- 所有实验命令均在本人服务器环境实际执行；`OUT`、`BASELINE_PASS/BUILDCHECKER_BASELINE_PASS/REUSE_PASS/C1~C3` 结果、`gate.json`/`results.csv`、BuildChecker `findings.json` 证据均来自真实运行输出并经本人核对。
- 3 个个人独立测试（2A/2C/2E）依据手册示例编写并在容器内运行 `unittest` 验证（**10 tests OK**），未凭空填报通过结果。
- 未修改与本次实验无关的服务端实现；未提交 `work/` 以外的非必要产物（按课程归档/`.gitignore` 要求处理）。

## 未采纳/风险控制
- 对 AI 给出的接口猜测（如错误的 `CASES` 导入）已通过查阅 `lab.py/run_lab.py` 与实际运行纠正；结论以可复现证据与门禁结果为准。
