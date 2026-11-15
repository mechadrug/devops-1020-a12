# 231880398 E11–E12 个人交付

分支：`student/231880398/e11-e12`，基于 PR #14 head `381a46b`。

## 复现与复核

`data/` 和 `work/` 被 `.gitignore` 忽略，仓库本身不包含个人 C2 和真实项目的 Git 历史。`prepare` 会按当前时间和提交者生成**新的** C0/C1，不能直接匹配本交付中的固定 SHA。

**方式 A：使用交付归档复核（推荐）**

先解压 `A12-E11-E12-231880398-evidence-20261116.tar.gz` 到仓库根目录，恢复 `data/` 和 `work/`；然后**不要执行 `prepare`**：

```bash
cd ~/a12-398-e11e12
tar -xzf /path/to/A12-E11-E12-231880398-evidence-20261116.tar.gz
git config --local user.name 231880398
python3 run_e11e12.py build
python3 run_e11e12.py test
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e11-a-sample.json \
  --out work/e11-a-replay-231880398
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e11-b-success.json \
  --out work/e11-b-replay-231880398
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e11-a-personal.json \
  --out work/e11-a-personal-replay-231880398
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e12-real.json \
  --out work/e12-real-replay-231880398
```

**方式 B：从空工作区体验课堂样例**

```bash
cd ~/a12-398-e11e12
git config --local user.name 231880398
python3 run_e11e12.py build
python3 run_e11e12.py test
python3 run_e11e12.py prepare
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e11-a-sample.json \
  --out work/e11-a-sample-231880398
```

个人 C2 和真实项目 request 固定了交付时的 base/target SHA；若要在方式 B 中重跑，需要按 `requests/real-dataset.json` 的来源说明重建真实项目，并在课堂 C1 上按报告所述让 `helper.c` 引入 `config.h` 生成 C2，然后把 request 中的 base/target SHA 更新为新提交。

API：

```bash
python3 run_e11e12.py serve --port 8082
curl -fsS http://127.0.0.1:8082/health
```

`serve` 必须通过 `run_e11e12.py` 启动：它把仓库挂载到容器的 `/course`，request 中的 `/course/data/...` 才会通过路径校验。直接在宿主机运行 `labs/e11e12/server.py` 会因 `/course/data` 不在仓库 `data/` 下而拒绝请求。

## 文件

- `report.md`：实验过程、结果、失败与限制。
- `ADR.md`：关键取舍。
- `contract.md`：接口契约核对。
- `integration.csv`：所有运行记录。
- `requests/`：课堂样例、个人 C2、E11-B 成功/过期报告、真实项目、API 提交/冲突请求。
- `labs/e11e12/test_231880398.py`：独立服务器重启契约测试。
- `labs/e11e12/projects/231880398-real/`：真实项目源码快照。

## 备注

- `work/` 和 `data/` 被 `.gitignore` 忽略，原始证据需要单独打包。
- 课堂样例与真实项目都使用同一个候选 Dockerfile；真实项目额外包含 `extra.h` 和 `Dockerfile.broken`。
- E11-B 成功路径和旧报告拒绝路径都已记录；旧报告的 `STALE_REPORT` 是预期契约行为。
- 未做 A/B 跨主机交换；真实项目是课程 fixture 派生，且与 231880397 使用同一来源 fixture（提交和故障注入独立），外部生产项目验收标准待教师/助教确认。
