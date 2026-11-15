# E11–E12 同伴操作手册（A12）

截至 2026-11-15，A 侧代码在 [PR #14](https://github.com/mechadrug/devops-1020-a12/pull/14)，E7、E8–E10、E11–E12 的 CI 均通过。课程服务器为 `118.31.65.25`；个人仓库位于 `/root/devops-students/231880397/buildchecker`，原始证据归档位于 `/root/devops-submissions/231880397/E11-E12-231880397-server-20261115.tar.gz`。服务器 API 使用 **8081**，实验包手册里的示例端口 **8080** 需要相应替换。

## A 组同伴：审阅与个人任务

1. 在 PR #14 审阅代码、报告、ADR 和请求清单；组长按课程流程合并。个人实验在各自仓库和分支进行，镜像按学号命名，`work/` 下使用独立目录。
2. E11-A 可参照 `work/e11-a-personal-231880397/`：基线完整图来自 BuildChecker 的 `strace`，目标增量发现与目标全量发现对照。记录完整 C0/C1 SHA、`refreshed`、`reused`、MD/RD 和差异原因。
3. 现有 E8 扫描器采用全局缓存键。本次源文件新增头文件指令时 `main.o`、`helper.o` 都刷新，`reused=[]`。请按实际输出记录，不要把它写成按目标复用。

## B 组同伴：完成独立实现与跨机联调

1. 在自己的服务器或独立工作目录跑 E11-B：DRAFT 实际构建并运行镜像，消费与目标提交一致的**固定 MD 报告**，由 MDFixer 生成补丁、验证、重检。保存构建日志、固定报告、补丁、`validation.json` 和失败案例。
2. E12 使用 A 侧本轮 `incremental-check.json` 及其 SHA256，核对报告内外层 `commit` 均为目标提交，再交给 B 侧修复。保存修复输入、补丁、复验结果。若要验收 B 组**独立代码**，请提供 B 侧镜像或执行入口及产物格式；当前 A 侧 API 调用的是实验包内置适配器。
3. 从另一台机器建立 SSH 转发（将账号替换成自己的课程账号，**不要在群里发送密码**）：

   ```bash
   ssh -N -L 18081:127.0.0.1:8081 <课程账号>@118.31.65.25
   ```

   在另一个终端检查：

   ```bash
   curl -fsS http://127.0.0.1:18081/health
   ```

   若服务停止，由 A 侧在上述个人仓库先检查 `curl http://127.0.0.1:8081/health`，确认端口空闲后执行 `python3 run_e11e12.py serve --port 8081`。8081 只绑定服务器回环地址，无需开放公网端口。
4. 将请求里的 `repo`、`candidate` 等路径设为 **API 服务器上的 `/course/data/` 路径**，使用完整 base/target SHA。文件应先上传到 A 侧服务器的 `data/` 独立子目录；本机路径对 API 无效。每次新实验使用新的 `idempotency_key`。以 `POST /v1/jobs` 提交，`GET /v1/jobs/<job_id>` 轮询，`GET /v1/jobs/<job_id>/artifacts` 取清单，`GET /v1/jobs/<job_id>/files/candidate.patch` 下载补丁并核对 `X-Content-SHA256`。完整命令见实验包 `02_操作手册/02_E12接口联调.md`，远程访问时把示例 `127.0.0.1:8080` 换为本机 `127.0.0.1:18081`。

## 项目数据与提交证据

- 当前 `data/real-project` 是从 A12 既有 `fixtures/md-rd` 派生的双源教学规模项目；来源、适配步骤、完整提交号见 `requests/real-dataset.json`。若教师要求组内独立维护的其他实际项目，请提供仓库地址、C0/C1 完整 SHA、候选 Dockerfile；当前扫描接口要求 `main.c`、`helper.c`、`config.h` 和显式 Make 规则，其他结构需先适配。
- 联调记录至少包含请求 JSON、输入 SHA、`job_id`、`trace_id`、各阶段 `commit`、产物 URI/SHA256、补丁、验证日志与最终结果。相同幂等键及相同输入应返回同一任务；同键改输入应返回 409。
- 分工完成后，请在各自 PR 或报告中给出证据路径，并与 A 侧 PR #14 关联。完整课堂说明见实验包 `02_操作手册/00_公共准备.md`、`01_E11轨道内集成.md`、`02_E12接口联调.md`、`03_真实项目接入与验收.md`、`04_GitHub提交与CI.md`。
