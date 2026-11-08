# ADR - E8-E10 A 轨（231880398 胡凌岳）

## 背景
在 C/Make + GCC 的显式规则档位下，维护 Make 声明依赖与真实构建依赖的一致性，并支持增量更新与修复对照。

## 决策
1. **历史图来源**：E8 以 GCC `-MM` 建立可复现基线，并用**真实 BuildChecker**（clean build + strace + Make 数据库）采集原始证据，将 `actual-graph.json` 投影到 `main.o/helper.o` 回写 `baseline`，证据可回溯（trace openat / make-db 声明）。
2. **增量策略**：以 `scan(p, old)` 的 `key/commit/目标` 复用未受影响目标的 `actual`；源码/配方/include 等影响依赖的变化触发刷新。C1 证明“仅表达式变化”可复用依赖图；C2/2C 证明 include 变化必须刷新。
3. **修复原则**：仅补齐缺失声明（MD）以恢复构建正确性；**不自动删除 RD**（如 `unused.h`）直至确认安全，避免引入隐性构建风险（C3 保留 RD）。
4. **有效性验证**：E10 采用 6 类变化 × 5 轮全量/增量对照，要求 `actual/declared/findings` 全等价并由 BuildChecker 最终交叉检查，`gate passed, mismatch_count=0`。

## 后果/权衡
- 复用减少重复分析，但失效条件必须保守（尤其预处理指令/传递 include，2E 覆盖）。
- 声明修复可降低漏编译风险；保留 RD 牺牲部分简洁性以换取安全。
- 当前限于教学档位（显式 Make 规则、受支持 flags/目标），超出档位应显式报 `UNSUPPORTED/ERROR`。
