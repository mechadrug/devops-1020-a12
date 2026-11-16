# E11–E12 A 组同伴操作手册（A12）

截至 2026-11-15，A 组代码在 [PR #14](https://github.com/mechadrug/devops-1020-a12/pull/14)，E7、E8–E10、E11–E12 的 CI 已通过。我的服务器仓库位于 `/root/devops-students/231880397/buildchecker`，完整原始证据在 `/root/devops-submissions/231880397/E11-E12-231880397-server-20261115.tar.gz`。A 侧任务 API 使用服务器回环地址 `127.0.0.1:8081`，实验包手册默认写的是 8080。

## 组长或审阅同学

1. 审阅 PR #14 的 `run_e11e12.py`、`labs/e11e12/`、工作流，以及 `docs/students/231880397/e11-e12/` 下的报告、契约和 ADR。确认本组的提交范围后按课程流程合并。
2. 检查服务器归档中的 `work/e11-a-231880397/`、`work/e11-a-personal-231880397/`、`work/e12-231880397/` 和 `work/e12-real-231880397/`。重点核对基线真实 `strace` 图、目标增量与全量发现一致、报告 commit、job_id/trace_id 和 artifact SHA256。
3. 我的项目数据来自 A12 既有 `fixtures/md-rd`，适配成双源 C/Make 教学规模项目；来源和两个完整提交 SHA 写在 `requests/real-dataset.json`。如果老师要求另一个组内实际项目，请确定仓库地址、C0/C1 完整 SHA 和候选 Dockerfile，再交给负责接入的同学。

## 需要完成个人 A 组实验的同学

在**自己的**仓库、分支、镜像标签和 `work/` 目录操作。先取得合并后的 E11–E12 代码；不要切换或修改 `/root/devops-students/231880397/buildchecker` 的个人分支。`run_e11e12.py` 要求本仓库的 `git config --local user.name` 为自己的数字学号。

```bash
cd /root/devops-students/<你的学号>/buildchecker
git config --local user.name <你的学号>
python3 run_e11e12.py build
python3 run_e11e12.py test
python3 run_e11e12.py prepare
python3 run_e11e12.py run --request data/integration-sample/e11-a.json --out work/e11-a-<你的学号>-01
```

`prepare` 仅在该仓库首次创建样例时执行；已有 `data/integration-sample` 时直接复用。`--out` 必须是新的目录。查看 `result.json`、`baseline-full/actual-graph.json`、`baseline-cache.json`、`incremental-report.json`、`target-full/findings.json`，确认 `SUCCEEDED` 且增量/全量发现相同。

随后自行创建一个目标提交，更新请求 JSON 的完整 base/target SHA，用新的 `work/` 目录再次运行 E11-A。报告写明哪些目标 `refreshed`、哪些 `reused`、新增或消失的 MD/RD 及原因。当前 E8 扫描器使用全局缓存键；我增加头文件指令的案例中两个目标均刷新、`reused=[]`，应按实际输出如实记录。

E12 的 A 组交付是基线全量图、目标增量图和当前 MD/RD 报告。将报告的 schema、commit、job_id、trace_id、artifact URI/SHA256 与目标提交核对，再交给联调同学消费。对接 API 时从课程服务器本机先检查 `curl -fsS http://127.0.0.1:8081/health`；API 仅绑定回环地址，跨机访问按实验包 `02_操作手册/02_E12接口联调.md` 建立 SSH 转发，并将示例服务端口 8080 改成 8081。

## 每人的提交材料

- 个人分支和 PR、完整 C0/C1 SHA、请求 JSON、数据来源说明。
- E11-A 的 `result.json`、全量图与原始日志、增量报告、全量对照、刷新/复用解释。
- E12 A 侧报告及其版本、job_id/trace_id、产物 URI/SHA256；若参与联调，附上请求、状态和最终验收记录。
- 个人报告和至少一项与本人改动对应的适配或契约测试。大型 `data/`、`work/` 证据单独归档，PR 中写明归档位置。

完整课堂步骤见实验包 `02_操作手册/00_公共准备.md`、`01_E11轨道内集成.md`、`02_E12接口联调.md`、`03_真实项目接入与验收.md`、`04_GitHub提交与CI.md`。
