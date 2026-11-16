# E11–E12 个人实验报告：王备中 231880138

日期 2026-11-16；A12 / A 轨。仓库 https://github.com/mechadrug/devops-1020-a12 ，个人分支 `codex/e11-e12-231880138`。实验目录 `/root/231880138/e11-e12/buildchecker`，仓库内 Git 身份 `231880138 <231880138@localhost>`。

公共基线为丁宏业 PR14 合并提交 `e89ff2ab8cf1dcd852bd2ed60e4bce529b1ef554`；本人已提交正式 [Review](https://github.com/mechadrug/devops-1020-a12/pull/14#pullrequestreview-5916572240)，按授权合并该 PR 后开展独立运行。实际测试与实验源码 SHA 是 `1232e2d0d964281c899a855aa3d3ccecfd2c29f4`。后续文档提交、个人 PR、CI 与合并 SHA 在课程 ZIP 的 `SUBMISSION.md` 和 GitHub 记录中补全；它们与下表受测项目内部提交分开记录。

## 个人贡献与环境

保留丁宏业的运行入口、pipeline、server、DRAFT 适配器及原 11 项契约测试。本人新增 `labs/e11e12/test_contract_231880138.py` 中两项契约测试：真实同长度、有效 JSON 内容被改动后必须按原 SHA 拒绝；Store 重启后将 QUEUED/RUNNING 持久状态标为 FAILED/SERVER_RESTARTED，同时保留已完成任务的 job/trace 和幂等结果，冲突请求仍拒绝。没有改写公共组件算法。Windows 本地与 Linux 个人镜像中均 **13 tests OK**；原始 Linux 日志 `work/contract-tests.log`。

原样执行 `python3 run_e11e12.py build` 成功，镜像 `course-e11e12:231880138`，ID `sha256:32e192f709badf97d39f075b7a7e1ab7b727d3e1711cf1d9a2d8ec26eabad508`。宿主 Ubuntu 22.04.5 / x86_64，Docker 29.1.3；工具链、镜像 inspect、环境与构建日志在 `work/`。宿主 3.5 GiB 内存低于 doctor 的 4 GiB 门槛，doctor 退出 1，报告如实保留；实验与功能测试通过。

## E11：BuildChecker → EChecker

本人的 `prepare` 生成课堂 C0 `245244c418fcd04a41cea2da9c44323b1596117a` 和 C1 `dd208265ff71d7e7327526eb7d12090583657732`。C1 在 main.c 增加 extra.h 的 include。第一次 E11-A 使用真实 strace 全量图作为 C0 缓存 actual，目标增量报告新增 MISSING(main.o,extra.h)，与目标 full-check 的对象目标发现集合一致。

随后在本人样例 Git 仓库创建个人 C2 `faf1b8b9cff085847cd070ec1a1a2bc507bafc77`，只将 helper.c 的 `return 0` 改为 `return 0+0`，没有改 include、文件集合、配方或配置。第二次请求 base=C1、target=C2，路径 `work/e11-a-personal-231880138-20261116-155543`。独立预期及实际均为 `reused=['main.o','helper.o']`、`refreshed=[]`、`added=[]`、`resolved=[]`；main.o 的 config.h/extra.h 两项 MD 和 unused.h 的 RD 保持不变，目标真实全量发现一致。图复用不意味着源代码没有变化，也不意味着 Make 必然完全不执行。

| 本人独立运行 | 被测项目 base → target 完整 SHA | job_id | 结果 |
| --- | --- | --- | --- |
| e11-a-baseline-231880138 | `245244c418fcd04a41cea2da9c44323b1596117a` → `dd208265ff71d7e7327526eb7d12090583657732` | `job-59cf4afe5da14e269fccd13167eb2cb1` | SUCCEEDED |
| e11-a-personal-231880138 | `dd208265ff71d7e7327526eb7d12090583657732` → `faf1b8b9cff085847cd070ec1a1a2bc507bafc77` | `job-8aa5a02154674402945670d5bb671418` | SUCCEEDED |
| e12-personal-231880138 | `245244c418fcd04a41cea2da9c44323b1596117a` → `faf1b8b9cff085847cd070ec1a1a2bc507bafc77` | `job-2e0dca8dd52e4ec1a0a3fdeb3450f879` | SUCCEEDED |
| e12-group-project-231880138 | `614c99434b7774f271f95d0db4726ddfc96db1c5` → `106a2402eb85e6ccf5ce71a03ff8196bbbcad4a0` | `job-6ed43bb12b23481c92c00c46318e79e8` | SUCCEEDED |

各目录保留 `baseline-full/` 真实 trace、Make 数据库与图，`baseline-cache.json` 中 actual 来自动态对象目标投影，`incremental-report.json` 和 `target-full/` 提供对照。`personal-verification.json` 是额外逐产物校验结果；不是替代原始证据。

## E12：实际报告衔接与修复复验

个人 C0→C2 请求在 `work/e12-personal-231880138-20261116-155544` 独立执行。draft、full-check、incremental-check、repair、recheck 五阶段全部成功；MDFixer 消费本轮生成的 incremental-check 产物，消费前校验 SHA 和目标 commit，未替换为 E11-B 的固定报告。请求沿用模板时仍带有 fixed_report 字段，但 mode=e12 的执行路径不读取它；repair.data.input_report 实际指向本轮 incremental-check.json 的 URI 与摘要。DRAFT 首次构建精确复现 MISSING_MAKE，依赖安装候选构建及禁网容器输出 1 成功；这一步使用课程已有候选回放，没有模型 API 调用。

补丁只补 main.o 所缺 config.h、extra.h 声明。`validation.json` 的 patch_applies/build/test/header_change/no_missing 全为 true，最终动态报告无 MISSING，仍保留 unused.h 的 REDUNDANT。每份阶段封装的 schema 为 e11e12-1、status 为 SUCCEEDED；封装层共用本轮 job_id/trace_id，full-check 属于 base，其他阶段属于 target。DRAFT 自身嵌套 trace 是组件运行 ID，封装层 trace 才是联调统一身份。

本次再次验证了所有结果清单中的 URI、文件字节数和 SHA256，并验证阶段封装 job/trace 与 commit 对应。保留所有 request.json、result.json、封装报告、图、补丁、验证及 Docker 构建/运行日志。

## API 实测及故障负例

组内既有 `127.0.0.1:8081/health` 返回 e11e12-1/ok；本人在独立仓库挂载上启动 `127.0.0.1:8082` 的同一 API，提交个人 C0→C2 E12 请求。真实 job_id `job-a3bf9a0608434ae8995b99dc7b7bc223`、trace_id `trace-fa3972ba6c6b4dddb1b1453329431f83`，状态 SUCCEEDED。

- 同键同输入重复 POST 返回同一 job_id，未创建第二次构建。
- 同键改 target 得到 HTTP 409 / IDEMPOTENCY_CONFLICT。
- GET 轮询和产物清单成功；下载 candidate.patch 的响应头、内容与清单 SHA256 均为 `88074f66c291dcad1344c48f6a2b9ddd42d235d9d0415c85fb33310c5b7cb2af`。
- 停止并重新启动本人 API 后，已完成任务仍可查询；trace 和 SUCCEEDED 状态保留，重复 POST 仍返回相同完成任务。
- 使用实际 incremental-check 的副本修改外层 commit，得到 STALE_REPORT；对同长度 JSON 改内容但继续使用原摘要，得到 ARTIFACT_HASH_MISMATCH。原封装和源码未被负例修改。证据在 `work/contract-negatives/`。

请求、首次/重复/冲突响应、轮询轨迹、下载头、补丁与重启记录在 `work/api-client/`，服务端完整产物在 `work/api-jobs/job-a3bf9a0608434ae8995b99dc7b7bc223/evidence`。个人 API 测试后停止，共享 8081 服务保持可用。这是在同一服务器上完成的编排 API 与四组件适配器验证，没有冒写成 B 组同学在另一台机器上的真实参与记录。

## 组内数据来源与接入范围

本人另外只读克隆丁宏业提供的 `data/real-project` 到本人的 `data/group-real-project`，在 `work/e12-group-project-231880138-20261116-155747` 独立执行 E12。其来源是 A12 仓库 `fixtures/md-rd`，源完整 SHA `7fc3b303ba78df50239d4d406513f257a0beee39`；丁宏业将其适配为当前双源 C/Make 接口，创建 C0 `614c99434b7774f271f95d0db4726ddfc96db1c5`、C1 `106a2402eb85e6ccf5ce71a03ff8196bbbcad4a0`，C1 在 helper.c 加 extra.h。本人未声称创造这套数据，也没有使用丁宏业的运行日志作为本人证据。

本次组内适配数据运行同样五阶段成功，目标新增 helper.o→extra.h 的 MD，修复后无 MD。原来源说明保存在 `data/group-real-source.json`。课堂生成数据与组内适配数据分开标注，完整内部提交历史以 `data/course-history.bundle`、`data/group-history.bundle` 保存并执行了 git bundle verify；`.git` 不进入课程 ZIP。

该数据是本组维护的教学规模 fixture 适配，不能写成外部生产项目验证。当前 scan/snapshot 仍受 main.c/helper.c/config.h、显式 Make 规则及输出 1/头文件变化后输出 2 的教学配置限制；未验证额外外部复杂仓库。若教师要求另一个真实项目，需要指定仓库和完整提交并扩展映射后另行验收。

## 命令、证据和交付

执行顺序：run_e11e12.py build → test → prepare → 两个 E11-A 请求 → 个人 E12 → 组内适配项目 E12 → API 提交/下载/重启验证。可重复执行的实际组织脚本随包保存在 `reproduction/run_personal.py`，每条命令、退出码及日志位于 `work/console/`、`work/personal-console.log` 和各 *.command.json。`data/` 与个人文档 `requests/` 下的 JSON 使用真实完整提交 SHA；源码/镜像身份在 `work/source-ref.json`、`work/environment-image.json`。

本人的新增代码、请求及说明通过独立分支和 PR 提交，CI 将同时保留 E7、E8–E10 和 E11–E12 工作流。最终 run、artifact、PR 合并记录放在课程包 SUBMISSION.md；数据与大型 work 随该个人 ZIP 归档。AI 辅助边界见 AI_USAGE.md。
