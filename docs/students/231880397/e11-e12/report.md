# E11–E12 个人实验报告：A12 / 231880397

日期：2026-11-15。运行位置：A12 课程服务器 `/root/devops-students/231880397/buildchecker`；分支 `student/231880397/e11-e12`。个人主要承担 A 组 BuildChecker→EChecker，另在同一服务器验证 B 侧适配器及 E12 联调。所有运行证据在 `/root/devops-submissions/231880397/` 的归档中；仓库 `work/` 保留原始文件。

## 来源与两个数据集

- 课堂样例由本次服务器 `prepare` 生成，C0 `eb97f526e7172c7d960845b7da692c343180e65b`，C1 `9c5c8b4cce1e4768f15a604960bda24f0dd09fcf`。该数据集标记为 `course-generated`。
- 独立项目由 A12 仓库 `fixtures/md-rd`（源提交 `7fc3b30`）改成文档要求的双源显式 Make 规则。服务器新建 Git 仓库，基线 `614c99434b7774f271f95d0db4726ddfc96db1c5`，目标 `106a2402eb85e6ccf5ce71a03ff8196bbbcad4a0`；目标提交在 `helper.c` 引入 `extra.h`，而 `helper.o` 规则未声明它。此项目是从组内既有 fixture 适配出的教学规模项目，**不是外部生产项目**；来源和适配步骤见 `requests/real-dataset.json`。目标源码在 `labs/e11e12/projects/231880397-real/`，完整 Git 历史在证据归档 `data/real-project`。

## 运行与观察

|案例|结果|要点|
|---|---|---|
|E11-A 课堂 C0→C1|SUCCEEDED|基线真实 strace 图进入历史缓存，目标增量/全量发现集合一致；新增 main.o→extra.h 缺失|
|E11-A 个人 C1→C2|SUCCEEDED|C2 `f74bbd4b3fd4df0b6962b9738e0b2fd33e2392c7` 新增 helper.o→extra.h 缺失；增量/全量一致|
|E11-B 固定 MD|SUCCEEDED|候选构建和镜像运行成功，补丁 accepted，复验无 MD|
|E11-B 旧报告|FAILED / `STALE_REPORT`|改错报告 commit 后拒绝消费|
|E12 课堂数据|SUCCEEDED|draft→full-check→incremental-check→repair→recheck 同一 job/trace|
|E12 A12 项目适配|SUCCEEDED|真实提交目标：106a2402eb85e6ccf5ce71a03ff8196bbbcad4a0；修复并复验通过|

个人 C2 检查结果：新增发现 `[['MISSING', 'helper.o', 'extra.h']]`。目前 E8–E10 的 `scan` 使用**全局预处理指令键**；helper.c 指令变化会使 main.o 和 helper.o 都刷新，本轮 `refreshed=['main.o', 'helper.o']`、`reused=[]`。这属于保守失效策略，无错误复用，但性能仍可优化。

A12 项目增量新增 `[['MISSING', 'helper.o', 'extra.h']]`，修复补丁 `artifact://job-807926302286463db8079b8028f39a7d/candidate.patch`，SHA256 `eed1bd41afa6bc0cdfed985a3c1f33f25814a4af3563e0b715d5a374f35ff92d`。修复后的重新检测报告 `work/e12-real-231880397/recheck.json`，验证项 patch_applies/build/test/header_change/no_missing 全部为 true。初次 E11-B 因默认 Debian 软件源下载超时而 FAILED；将候选源改为与环境镜像一致的清华镜像后重跑成功，失败和成功日志均保留。

## API 与契约

API 仅在服务器 `127.0.0.1:8081` 暴露。提交任务 `job-075c2e21a41847988c737e2418c5009e`、trace `trace-a8a963b3d0ce4b968b6619262240d083`，状态 SUCCEEDED。相同幂等键与请求返回同一 job_id；同键不同 target 返回 HTTP 409。下载 candidate.patch 后，响应头、文件内容和清单 SHA256 均为 `88074f66c291dcad1344c48f6a2b9ddd42d235d9d0415c85fb33310c5b7cb2af`。新增契约测试检查外层 commit 正确而报告 data.commit 过旧时返回 `STALE_REPORT`；服务器 11 项测试通过。

## 交付与限制

- 代码：`run_e11e12.py`、`labs/e11e12/`、`.github/workflows/e11e12.yml`，保留 E8–E10。
- 原始结果、请求、Docker 构建日志、图、补丁、验证文件、API 记录及两个 Git 数据集在服务器归档。
- 两项目都满足当前双 C 源文件、显式 Make 规则的适配接口。A12 既有 fixture 是教学小项目，不能代表复杂真实仓库；若课堂要求外部项目，还需由组内提供对应仓库与提交并扩展目标映射。
