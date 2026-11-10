# AI 使用记录

工具/模型/日期：Claude Code（Haiku 4.5），2026-11-10。

输入上下文与问题：本人按 A12 组 A 轨道完成 E8—E10。输入为课程材料 `DevOps_E8_E10_20261031` 的公共准备、E8/E9/E10 A 组手册、提交与排错、个人测试示例，以及仓库中的 `labs/e8e10/lab.py`、`test_profile.py`、`run_lab.py`、CI workflow。需要完成：在 A12 服务器运行三阶段实验、保存证据、增加个人测试与 E10 自主测量、填写报告并提交 PR。

模型建议：

1. 按手册逐步执行 E8/E9/E10，不重复运行一键入口；每步保留 `steps/` 日志与 JSON。
2. 在 `test_profile.py` 增加三个独立测试类：声明清理复用、间接头文件链失效、`-O0`→`-O1` 五次对照；类名带学号以避免与组员类冲突。
3. 新增 `student_231880224.py` 作为 E10 配置变化测量模块，输出 CSV、性能汇总、gate 和最终 BuildChecker 证据。
4. 报告按模板填写真实 OUT、内部提交、镜像 ID、30 行矩阵和中位数。

采纳/拒绝及理由：

- 采纳 1：实际执行路径与手册一致，所有断言均为手册的独立预期，未把实现输出直接抄成预期。
- 采纳 2：三个测试覆盖 E8/E9/E10 各一例，输入在示例基础上做了自己的变化（声明同时补缺删冗、头文件链两级、独立 fixture 的 flags 场景）。
- 采纳 3：个人模块与组员 138 的“删除间接头文件”场景不同，选择“声明修复后配置变化”，避免重复，并便于隔离配置失效。
- 拒绝：未修改参考实现 `lab.py` 的算法，未采用按边哈希等超出教学范围的方案；未照抄他人日志或证据。
- 人工修改：第一次运行 `test_flags_change_refresh_matches_full_five_times` 时预期误写为“仅 RD unused.h”，实际独立 fixture 仍有 MD config.h；按独立分析把断言修正为两项发现后通过，没有放宽断言或修改实现来迁就结果。

实际验证命令/输入/结果：

- `docker run ... python3 -m unittest discover -s labs/e8e10 -p test_profile.py -v` → `Ran 16 tests`、`OK`、退出 0（`work/unit-tests-20261110-213251.log`）。
- E8：`BASELINE_PASS`、`BUILDCHECKER_BASELINE_PASS`、`REUSE_PASS`（`work/e8-A-manual.ooGeN8`）。
- E9：`C1_REUSE_PASS`、`C2_REFRESH_PASS`、`C3_RESOLVED_PASS`（`work/e9-A-manual.LPHqPw`）。
- E10：`MATRIX_PASS {'unchanged':5,'body':5,'include':5,'declaration':5,'flags':5,'header':5}`、`DYNAMIC_CROSSCHECK_AND_MATRIX_PASS`（`work/e10-A-manual.lj6lAY`）；个人 `FLAGS_AFTER_REPAIR_PASS`（`work/e10-A-manual.8B8p1j`）。
- GitHub Actions 与 PR 证据在推送后补充。

边界说明：参考实现、手册与固定样例来自课程实验包；本人贡献是个人测试、个人测量模块、真实运行产生的证据与本文档。AI 协助执行命令和起草文本，服务器凭据与 GitHub 授权由本人提供并完成授权。
