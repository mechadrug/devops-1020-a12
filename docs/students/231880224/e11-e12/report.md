# E11–E12 个人实验报告：A12 / 231880224

日期：2026-11-17。运行位置：A12 课程服务器 `/root/devops-students/231880224/buildchecker`；分支 `student/231880224/e11-e12`；镜像 `course-e11e12:231880224`。GitHub：https://github.com/mechadrug/devops-1020-a12 （PR #16，e7-a / e8e10 / e11e12 三项 CI 均通过）。本人承担 A 组 BuildChecker→EChecker，并在同一服务器完成 B 侧适配验证与 E12 联调。

## 来源与两个数据集

- 课堂样例由本次服务器 `prepare` 生成，C0 `f56e07874badab9ef4934123b3021e5cd3ad23d4`，C1 `8865d524287e4a938cd027df0cefe5a8b8cf68ba`；`dataset.json` 标记为 `course-generated`。
- 独立项目由 A12 仓库既有 `labs/e11e12/environment/fixtures/md-rd`（单源 C/Make）适配为文档要求的双源、显式 Make 规则项目。基线 `c7e2cb763472b8294f6cf5e34a1ff13850ce2a6d`，目标 `ae089b62da3f8c591742c056b6cce50cec487e82`；目标提交在 `helper.c` 引入 `extra.h`，而 `helper.o` 规则未声明该依赖。此项目是从组内 fixture 派生的教学规模项目，**不是外部生产项目**；来源与适配步骤见 `requests/real-dataset.json`，目标源码在 `labs/e11e12/projects/231880224-real/`，完整 Git 历史在证据归档 `data/real-project`。

## 运行与观察

| 案例 | 结果 | 要点 |
|---|---|---|
| E11-A 课堂 C0→C1 | SUCCEEDED | 基线真实 strace 图进入历史缓存；增量/全量发现集合一致；新增 main.o→extra.h 缺失 |
| E11-A 个人 C1→C2 | SUCCEEDED | C2 `8201ec12f0802d64ac5df607d00c69e9be4d20cb` 新增 main.o→extra2.h 缺失；增量/全量一致 |
| E11-B 固定 MD | SUCCEEDED | 初始构建 MISSING_MAKE，候选构建与镜像运行成功，补丁 accepted，复验无 MD |
| E11-B 旧报告 | FAILED / `STALE_REPORT` | 将报告 commit 改回 C0 后拒绝消费 |
| E12 课堂数据 | SUCCEEDED | draft→full-check→incremental-check→repair→recheck，同一 job/trace |
| E12 个人项目 | SUCCEEDED | 目标 `ae089b6…`；修复 helper.o→extra.h 后复验通过 |

个人 C2 检查结果：`added=[['MISSING','main.o','extra2.h']]`。E8–E10 的 `scan` 使用**全局预处理指令键**，任一源文件指令变化都会让两个目标刷新，本轮 `refreshed=['main.o','helper.o']`、`reused=[]`。这是保守失效策略，无错误复用，代价是增量收益在源文件改动时退化为全量。

个人项目增量同样 `refreshed=['main.o','helper.o']`、`reused=[]`，新增 `[['MISSING','helper.o','extra.h']]`；补丁 `artifact://job-ddf4f28e595d475c96650b952edfe5dc/candidate.patch`，SHA256 `015c58132a9221c11807c61ddab58b3a053f5edb5ac3cb1c33008eb235308ccc`；`recheck.json` 中 patch_applies/build/test/header_change/no_missing 全部为 true。

## API 与契约

API 仅在服务器 `127.0.0.1:8082` 暴露（8081 已被同组 231880397 的服务占用）。提交任务 `job-da73a64edfcb4f3181bf145dd7056f3c`、trace `trace-6da31fecf3904603b669639399b98015`，状态 SUCCEEDED。相同幂等键与请求返回同一 job_id；同键不同 target 返回 HTTP 409 `IDEMPOTENCY_CONFLICT`。下载 candidate.patch 后，响应头 `X-Content-SHA256`、文件内容与清单 SHA256 均为 `88074f66c291dcad1344c48f6a2b9ddd42d235d9d0415c85fb33310c5b7cb2af`。

新增契约/回归测试 `labs/e11e12/test_e11a_incremental.py`：未变化的工作树全部复用、新增头文件指令后全部刷新并记录新增缺失依赖。`run_e11e12.py test` 共 13 项全部通过。

## 交付与限制

- 代码：`run_e11e12.py`、`labs/e11e12/`（含新增测试与个人项目源码）、`.github/workflows/e11e12.yml`，保留 E8–E10 原有文件。
- 证据：`work/e11-a-231880224-01`、`work/e11-a-231880224-02`、`work/e11-b-231880224-01`、`work/e11-b-231880224-stale`、`work/e12-231880224-01`、`work/e12-real-231880224-01`、`work/api-client-231880224`；归档位于 `/root/devops-submissions/231880224/`。
- 限制：派生项目仍为教学规模；E8 全局缓存键使源文件指令变化时全量刷新；如课堂要求外部真实仓库，需由组内提供完整提交并扩展目标映射。
