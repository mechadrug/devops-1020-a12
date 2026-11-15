# E11–E12 个人实验报告：A12 / 231880398

日期：2026-11-16。运行位置：本机 WSL2 Ubuntu 24.04（Docker 29.1.3、Python 3.12.3），仓库 `~/a12-398-e11e12`。个人分支 `student/231880398/e11-e12`，基于 PR #14 的 head `381a46b`；组内 `main` 当时仍为 `fe41d3d`，尚未合并 E11–E12 基线。本文只记录 231880398 自己的工作，不承担组长职责，也不复用 231880397 的运行证据。

## 来源与数据集

- 课堂样例：由本机 `python3 run_e11e12.py prepare` 生成，标记为 `course-generated`；C0 `f540209c8a2a53daa57a71f285147d2c9e3883a3`，C1 `9b5c2d50a05c369cd4b6f61b0b24f9c8738ae130`。
- 个人 C2：在课堂样例 C1 上让 `helper.c` 引入 `config.h`，形成新的 `helper.o → config.h` 缺失；C2 `f65ce437a15039681aa8120266ec7c314922f9fa`。
- 真实项目适配：A12 仓库 `fixtures/md-rd`（源提交 `7fc3b30`）改成文档要求的双源显式 Make 项目，由 231880398 在 `data/real-project-231880398` 独立建立 C0/C1。C0 `a0bdb095ee151d10f028fe9aae59cc6d9088a920`，C1 `b54258399c066b44432a165f8a614bc99e87a5b7`。C1 在 `helper.c` 引入 `config.h`，而 `helper.o` 规则漏写它。该项目是教学规模适配，不是外部生产项目；来源和适配步骤见 `requests/real-dataset.json`。
- 真实项目源码快照在 `labs/e11e12/projects/231880398-real/`；完整 Git 历史在证据归档的 `data/real-project-231880398`。

## E11 集成

现有 E8–E10 的 `labs/e8e10` 检查器没有重写；新增 `run_e11e12.py` 作为宿主入口，`labs/e11e12/pipeline.py` 负责阶段编排，`labs/e11e12/server.py` 提供 API，`labs/e11e12/test_231880398.py` 是个人独立契约测试。

字段映射：

| 层级 | 字段 | 约定 |
|---|---|---|
| 外层 envelope | `schema_version` | 固定 `e11e12-1` |
| 外层 envelope | `job_id` / `trace_id` | 同一任务同一链路贯穿五个阶段 |
| 外层 envelope | `kind` | `draft` / `full-check` / `incremental-check` / `repair` / `recheck` |
| 外层 envelope | `commit` | 该阶段对应的 base 或 target commit |
| 外层 envelope | `status` | `QUEUED` / `RUNNING` / `SUCCEEDED` / `FAILED` / `TIMED_OUT` |
| 外层 envelope | `data` | E8–E10 原始报告，内部仍为 `e8e10-1` |
| 外层 envelope | `artifacts` | `artifact://job-id/相对路径` + SHA256 + bytes |
| 内层 data | `data.schema_version` | `e8e10-1`，不冒充外层版本 |
| 内层 data | `data.commit` | 必须与外层 `commit` 一致 |

运行结果：

| 案例 | 结果 | 要点 |
|---|---|---|
| E11-A 课堂 C0→C1 | SUCCEEDED | `job-a8cfee4bd3cb48728bff9fac5dd63be3`；增量新增 `MISSING main.o → extra.h`；历史缓存来自真实 strace 基线 |
| E11-A 个人 C1→C2 | SUCCEEDED | `job-a98e203892344dfa8c95ecaa7c090cb8`；C2 新增 `MISSING helper.o → config.h` |
| E11-B 旧报告负向 | FAILED / `STALE_REPORT` | `job-e5a896c8482249d8ab44856612fa50c9`；故意把 fixed report 的 commit 改回 C0，被拒绝消费 |

个人 C2 的增量结果为 `added=[['MISSING','helper.o','config.h']]`，`resolved=[]`。当前 E8–E10 的 `scan` 使用**全局预处理指令键**，`helper.c` 指令变化会同时刷新 `main.o` 和 `helper.o`，因此 `refreshed=['main.o','helper.o']`、`reused=[]`。这是保守失效策略，没有错误复用；代价是增量粒度较粗，后续可按目标建立缓存键。

E11-B 没有作为成功实验记录；这里只保留旧报告拒绝路径，因为个人计划把 E11-B 视为可选附加项。该失败是预期的契约拒绝，不是环境故障。

## E12 五阶段

### 课堂固定样例（CLI）

`job-cf7dea8438944a9094100e01ff563c31`，`trace-baf80a458b6544d18148b47a065b7702`，C0→C1，状态 SUCCEEDED。阶段为：

| 阶段 | commit | 结果 |
|---|---|---|
| `draft` | target `9b5c2d50...` | 候选镜像构建并运行成功 |
| `full-check` | base `f540209c...` | 基线发现 `MISSING main.o→config.h`、`MISSING main.o→extra.h`、`REDUNDANT main.o→unused.h` |
| `incremental-check` | target `9b5c2d50...` | 增量新增 `MISSING main.o→extra.h` |
| `repair` | target | 生成 `candidate.patch`，SHA256 `88074f66c291dcad1344c48f6a2b9ddd42d235d9d0415c85fb33310c5b7cb2af` |
| `recheck` | target | `patch_applies/build/test/header_change/no_missing` 全部 true；仅保留 `REDUNDANT main.o→unused.h` |

补丁实际内容是把 `main.o` 的显式依赖补成 `main.c unused.h config.h extra.h`。`recheck` 的 `source_unchanged=false` 是验证副本应用补丁后的状态，不代表原始 target 被改写；原始 target 仍保留在 `target-project/`。

### 课堂固定样例（API）

API 绑定 `127.0.0.1:8082`，健康检查返回 `{"status":"ok","schema_version":"e11e12-1"}`。提交 `job-e6038cf86e6446518dbf2f190de3a441`，`trace-2af979ec2c21462aaa2ad1c5f4ebe537`，提交时 QUEUED，轮询后 SUCCEEDED。五个阶段 artifact SHA256 与 `artifacts` 清单一致；下载 `candidate.patch` 得到 274 字节，响应头 `X-Content-SHA256` 与文件 SHA256 均为 `88074f66c291dcad1344c48f6a2b9ddd42d235d9d0415c85fb33310c5b7cb2af`。

负向记录：

| 请求 | 响应 | 证据 |
|---|---|---|
| 同幂等键、改 target | HTTP 409 `{"error":"IDEMPOTENCY_CONFLICT"}` | `work/api-e12-231880398/conflict.status` / `conflict.json` |
| 路径穿越 `%2e%2e/.../etc/passwd` | HTTP 404 `{"error":"NOT_FOUND"}` | `traversal.status` / `traversal.json` |
| 不存在的 job | HTTP 404 `{"error":"NOT_FOUND"}` | `notfound.status` / `notfound.json` |

### 真实项目适配（E12）

`job-a29d92aa67424b3f9f4667c06a23e325`，`trace-17695295d71540b18e87e5258b0c0d48`，C0 `a0bdb095...` → C1 `b5425839...`，状态 SUCCEEDED。五个阶段齐全；增量新增 `MISSING helper.o → config.h`；修复补丁为 318 字节，SHA256 `895896a35a8fd4fdae7639ced862e5eae0374c9b0375a3732df4e50c4d048491`；`recheck` 的 `patch_applies/build/test/header_change/no_missing` 全部 true，最终只剩 `REDUNDANT main.o → unused.h`。

第一次真实项目尝试 `job-842f7fac9dee49e2ac7487117174b7f8` 失败：`EXECUTION_FAILED`，原因是适配项目没有 `Dockerfile.broken`，而候选镜像模板需要复制它。补充 `extra.h` 和 `Dockerfile.broken` 后重新建立 C0/C1，第二次成功；两次输出都保留在 `work/e12-real-failed-231880398/` 与 `work/e12-real-231880398/`。

## 失败与处理

- 真实项目第一次 `EXECUTION_FAILED`：缺少 `Dockerfile.broken`；已在项目 C0/C1 中补齐，并重跑成功。
- E11-B 旧报告负向：`STALE_REPORT`；这是契约预期的拒绝，证明不能消费旧 commit 的报告。
- 曾用 E11-A 请求携带旧 fixed report 做尝试，流程仍然 SUCCEEDED，因为 E11-A 不消费 `fixed_report`；这说明 E11-A 与 E11-B 的输入边界不同，因此没有把该次运行当作失败证据，改由 E11-B 记录拒绝路径。
- API 同键改 target 返回 409、路径穿越返回 404，均为预期负向行为，已保存响应码和响应体。

## 测试

`python3 run_e11e12.py test` 在容器内运行，结果为 12 项通过：原有 11 项契约测试 + 个人 `test_231880398.py` 的服务器重启规则。个人测试检查 `QUEUED`/`RUNNING` 在重启后变为 `FAILED / SERVER_RESTARTED`，而 `SUCCEEDED` 任务仍可查询。

## 交付与限制

- 代码：`run_e11e12.py`、`labs/e11e12/`、`labs/e11e12/projects/231880398-real/`、个人测试 `labs/e11e12/test_231880398.py`。
- 文档与请求：`docs/students/231880398/e11-e12/`。
- 原始日志、缓存、strace、补丁、验证文件和两个 Git 数据集在 `work/` 与证据归档中。
- 未完成：A/B 跨主机交换、外部生产项目、E11-B 成功路径（可选）。真实项目仍是课程 fixture 派生，若课堂要求外部仓库，需要教师/助教确认后再补。
- 分支基于 PR #14，不是当时的 `main`；PR #14 合并后应在最新 `main` 上 rebase/合并并重跑 CI。

## 证据索引

| 内容 | 文件/URL |
|---|---|
| E11-A 课堂 | `work/e11-a-231880398-01/` |
| E11-A 个人 C2 | `work/e11-a-personal-231880398/` |
| E11-B 旧报告负向 | `work/e11-b-stale-231880398/` |
| E12 课堂 CLI | `work/e12-231880398/` |
| E12 课堂 API | `work/api-e12-231880398/` |
| E12 真实项目失败 | `work/e12-real-failed-231880398/` |
| E12 真实项目成功 | `work/e12-real-231880398/` |
| 完整数据集归档 | 证据压缩包中的 `data/` |
| API 提交与负向请求 | `docs/students/231880398/e11-e12/requests/` |
