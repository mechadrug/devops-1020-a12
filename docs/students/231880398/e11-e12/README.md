# 231880398 E11–E12 个人交付

分支：`student/231880398/e11-e12`，基于 PR #14 head `381a46b`。

## 快速复核

```bash
cd ~/a12-398-e11e12
git config --local user.name 231880398
python3 run_e11e12.py build
python3 run_e11e12.py test
python3 run_e11e12.py prepare
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e11-a-personal.json \
  --out work/e11-a-personal-231880398
python3 run_e11e12.py run \
  --request docs/students/231880398/e11-e12/requests/e12-real.json \
  --out work/e12-real-231880398
```

API：

```bash
python3 run_e11e12.py serve --port 8082
curl -fsS http://127.0.0.1:8082/health
```

## 文件

- `report.md`：实验过程、结果、失败与限制。
- `ADR.md`：关键取舍。
- `contract.md`：接口契约核对。
- `integration.csv`：所有运行记录。
- `requests/`：个人 C2、真实项目、API 提交/冲突请求。
- `labs/e11e12/test_231880398.py`：独立服务器重启契约测试。
- `labs/e11e12/projects/231880398-real/`：真实项目源码快照。

## 备注

- `work/` 和 `data/` 被 `.gitignore` 忽略，原始证据需要单独打包。
- 课堂样例与真实项目都使用同一个候选 Dockerfile；真实项目额外包含 `extra.h` 和 `Dockerfile.broken`。
- 未做 A/B 跨主机交换；真实项目是课程 fixture 派生，外部生产项目验收标准待教师/助教确认。
