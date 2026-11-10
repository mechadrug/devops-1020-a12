# 决策记录（ADR）

## 背景与约束

本实验用受限的 C/Make 样例验证增量依赖检查：只支持 `main.o`、`helper.o` 两个对象目标，Makefile 为显式规则，实际依赖由 `gcc -MM` 采集，报错时不接受任意/绝对路径；A 轨道还要求以真实 BuildChecker 的 strace 结果作为历史图来源，并把它投影到对象目标后与 `gcc -MM` 断言一致。服务器为四人共用，时间与内存有限，实验需要可重复、可解释且不依赖每次 clean build。

## 选择与替代方案

**选择：整键保守失效。** `scan` 把以下内容组成 `key`：所有本地 `.c/.h` 文件的预处理指令行、Makefile 中以 TAB 开头的全部配方行、`CFLAGS`、编译器版本字符串。`key` 完全相等且目标在历史 `actual` 中时，直接复用该目标的 `actual`；否则对目标执行 `gcc -MM` 重新采集。每次 scan 都重新解析当前声明图并重算 MD/RD，复用只跳过依赖采集，不跳过发现比较。报告通过 commit SHA 绑定输入，patch/validate 前核对 `STALE_REPORT`。

替代方案及取舍：

1. **按 mtime 判断**：实现简单，但文件系统时间戳不能反映预处理指令或编译配置的变化，复制/检出后时间戳也会失真，易漏边，拒绝。
2. **每次全量 `gcc -MM`**：结果最稳，但失去历史图复用，无法体现增量机制，也不符合 E8/E9 的观察目标，仅作为 E10 每行的对照路径保留。
3. **按依赖边哈希复用**：能减少 include/header 场景的过度刷新，但需要额外维护边级历史和 Make 展开，超出教学实现范围；作为扩展计划，不在本次提交中实现。
4. **报告不绑定 commit**：可直接重放旧报告，验证语义失效；因此保留 `STALE_REPORT` 拒绝，并由 `test_old_report_rejected` 覆盖。

A 轨道的历史图身份绑定在 `actual-graph.json` 与 `baseline_source` 上，基线不是伪造的静态表，而是本次 BuildChecker 实际 trace 的投影。

## 代价与覆盖范围

- 代价：任一本地头文件指令变化、配方变化、`CFLAGS` 变化或编译器版本变化都会刷新所有对象目标。E10 中 include/header/flags 的 `refreshed` 均为 2，增量耗时与全量接近（full/inc 约 0.97–0.99），这是保守策略的真实代价；不做数字美化。
- 覆盖：显式规则、变量展开（最多 8 层）、`-O0/-O1/-O0 -DMODE=1`；不覆盖模式规则、自动变量、系统头文件、并行构建；不支持的配置抛 `ValueError`，由 `test_unsupported_configuration_rejected` 覆盖。
- 安全：补丁依赖名只允许 `[\w./-]+`，拒绝绝对路径和 `..`，由 `test_unsafe_dependency_rejected` 覆盖。

## 验证命令与实际证据

- E8：`BASELINE_PASS`、`BUILDCHECKER_BASELINE_PASS`、`REUSE_PASS`；trace `t.14:579` 读取 config.h，`make-db.txt` 第 1044 行声明缺少 config.h。
- E9：C1 复用两目标且复用后 `scan` 仍重算发现；C2 两目标刷新并新增 MISSING extra.h；C3 两目标复用且消除两项 MD，RD unused.h 保留。
- E10：六场景 ×5 共 30 行，`actual/declared/findings` 与全量逐项相等；`gate.json` 为 `passed=true, rows=30`；最终 BuildChecker 对象目标投影只剩 RD unused.h。
- 本人扩展：`student_231880224.py` 在声明修复后只改 `-O0`→`-O1`，五次 `reuse=0, refreshed=2`，中位数 0.0099217 s / 0.0099886 s，full/inc=1.007；最终 BuildChecker `SUCCEEDED` 且只有 RD unused.h。
- 单元测试：`Ran 16 tests`、`OK`（日志 `work/unit-tests-20261110-213251.log`）。
