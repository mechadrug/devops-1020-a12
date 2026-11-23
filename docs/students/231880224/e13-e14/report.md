# E13–E14 个人实验报告

李玄同 · 231880224 · A12 · A 轨道 · 2026-11-23

状态：本人合同测试、检测回归和四服务个人验证已完成；本报告不替代 B12 签收，也不把开放 PR 写成已合并。`v0.9-rc` 未创建。

## 身份与版本

- A12 集成仓库：https://github.com/mechadrug/devops-1020-a12
- 个人分支：`codex/e13-e14-231880224`，起点为 PR18 head `1aed82326eb6293df700882126aa81842fc332cb`
- 教学镜像：`course-e11e12:231880224`，实际 ID `sha256:b0b55b070170819975849f82470e9e434d5a2ccf2901bc754fceea586495d85f`（由本人目录重新执行 `run_e11e12.py build` 得到）
- A12 交换项目（主责维护、固定历史）：base `892e18910c27f2f1f5a105880c1f4e36c79f9494`，target `9c312e412e6c3efb3dbed3b3fd4db50afccfb52e`；`prepare_a12_project.py` 在本机重放后 SHA 与主责报告一致
- 组级集成代码由王备中 231880138 维护；本人只提交个人测试与个人文档，不冒写他人实现

## 本人贡献

新增 `labs/e13e14/tests/test_e13e14_231880224.py`，9 项合同测试，覆盖课堂基线未覆盖的边界：

1. 交接硬化（3 项）：产物 URI 用 `../` 逃逸 run 目录被拒绝；声明为其他 job 的产物被拒绝；重复 `incremental-check` 阶段被拒绝。
2. 传输摘要格式（2 项）：64 位大写 SHA 与带尾部空白的 SHA 均以 `INVALID_REQUEST` 拒绝，而不是被静默忽略。
3. 四服务部署契约（4 项）：四角色共享宿主 `${E14_UID}:${E14_GID}` 且带 `no-new-privileges`；只有 `draft` 挂载 Docker socket 和 `group_add`；四个端口均绑定 `127.0.0.1` 并共用健康检查；CPU/内存/PID 上限存在。

另完成本人检测回归和四服务个人验证，命令与结果见下。

## 执行记录

| 步骤 | 命令 | 实际结果 |
|---|---|---|
| 构建镜像 | `python3 run_e11e12.py build` | 退出 0，镜像 `course-e11e12:231880224` |
| 旧契约回归 | `python3 run_e11e12.py test` | 13 项全部通过 |
| 准备样例 | `python3 run_e11e12.py prepare` | 生成 `data/integration-sample` |
| 重建 A12 项目 | `python3 labs/e13e14/prepare_a12_project.py` | base/target 与主责报告一致 |
| E13 测试套件 | `python3 -m unittest discover -s labs/e13e14/tests -p 'test_*.py' -v` | 19 项通过（10 项基线 + 本人 9 项） |
| 个人检测回归 | `python3 run_e11e12.py run --request data/e13-a12-policy/request-e11-a.json --out work/e13-personal-A-01` | SUCCEEDED；job `job-498f59b9387340d3b04200480bf7d4bc`，trace `trace-f09516949cbd47069c01200b2119aa98`；93 个产物，哈希不一致 0 |
| 四服务启动 | `docker compose -f labs/e13e14/compose.yaml -p e14-231880224 up -d --wait` | 四角色全部 healthy；端口 18181–18184；UID/GID 0/0（服务器 root），Docker socket 组 121 |
| 五阶段 E2E | `python3 labs/e13e14/orchestrate.py --request data/e13-a12-policy/request-e12.json --out work/e14-personal-01` | SUCCEEDED；job `job-a6064ce2cd3847f7af622626061d243f`，trace `trace-02aa2a01ecd448a7ab6d1e9cf9771e83`；draft→full-check→incremental-check→repair→recheck 同一 job/trace；182 个产物哈希一致；补丁 `dacc722cb13eb548ff7580c66a2442c78e92b91159ce67c5de1f15e51276f830`，`accepted=true`，复检无 MISSING |
| 四角色日志 | `docker compose ... logs --no-color > work/e14-personal-services.log` | buildchecker 3 条、echecker 1 条、draft 1 条、mdfixer 1 条，均带本人 job |
| 日志扫描 | `python3 labs/e13e14/scan_runtime_logs.py work/e14-personal-01 work/e14-personal-services.log` | 退出 0；172 个文本文件，0 命中，0 错误 |
| 关闭项目 | `docker compose ... down` | 只删除 `e14-231880224` 容器与网络；共享 `127.0.0.1:8081/health` 仍为 HTTP 200 |

## 证据目录

- `work/e13-personal-A-01/`、`work/e13-personal-A-01.console.log`
- `work/e14-personal-01/`、`work/e14-personal-01.console.log`
- `work/e14-personal-before.json`、`work/e14-personal-after.json`
- `work/e14-personal-services.log`、`work/e14-personal-scan.txt`

## 组级证据引用（非本人独立执行）

- PR18 的同伴正式 Review 由本人提交：https://github.com/mechadrug/devops-1020-a12/pull/18#pullrequestreview-6018226183
- C1–C8 完整矩阵、教师三项目、B12 项目运行、受控故障与健康探针由主责 231880138 执行，证据在其课程包和 `docs/students/231880138/e13-e14/`；本人未复制或改名为个人结果
- B12 的 DRAFT/MDFixer 组件由主责按其固定提交接入；本人未冒用 B12 身份运行或签收

## 未完成与限制

- B12 本人执行/签收、其指定 SHA 的 CI 链接仍未提供；`integration.csv` 保持 `PENDING`
- PR18 审查时尚未合并，`v0.9-rc` 未创建；本人不创建或移动标签
- 分配主机 3.5 GiB 内存仍低于旧 doctor 的 4 GiB 阈值，本人未修改阈值或把环境自检写成通过
- 本人四服务使用课程固定样例；A/B 实际项目的四服务结果引用主责证据，不冒充本人运行

## 个人 PR 与 CI

PR：https://github.com/mechadrug/devops-1020-a12/pull/21

CI（提交 `e1e9d39` 的 push + pull_request 共 10 项检查全部成功）：

- E7：https://github.com/mechadrug/devops-1020-a12/actions/runs/45136494958
- E8–E10：https://github.com/mechadrug/devops-1020-a12/actions/runs/45136494988
- E11–E12：https://github.com/mechadrug/devops-1020-a12/actions/runs/45136494945
- E13–E14（contracts + four-services）：https://github.com/mechadrug/devops-1020-a12/actions/runs/45136494921

本报告后续文档提交不改变上述测试与运行结果；最终源码快照 SHA 以课程包 `provenance.json` 为准。
