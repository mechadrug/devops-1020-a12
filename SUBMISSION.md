# A12 E5–E7 提交说明 — 李玄同 231880224

## 基本信息

| 项 | 值 |
| --- | --- |
| 姓名学号 | 李玄同 231880224 |
| 小组 / 轨道 | A12 / A（BuildChecker） |
| A12 服务器 | 118.31.65.25（Ubuntu 22.04.5 LTS，x86_64，2 vCPU / 3.5 GiB / 70.2 GiB 可用） |
| 本人工作目录 | `/root/231880224/e5-7/DevOps_1020_Student_Cloud/labs/A-buildchecker` |
| 仓库地址 | 待 CI 仓库确定后填写 |
| 被测代码提交 SHA | `809f7f6755de0847b2097fdcb631a53ca839cdcc` |
| 服务镜像 | `course1020-buildchecker:local` |
| 镜像 ID | `sha256:3447b9d175d351d020a23c548f1fbba6c51da8bc3adca87e48fab376e076aaa1` |
| 依赖锁文件 | `requirements-dev.lock`（sha256 `24f54d917487599d98e13c5733a75ca4a86652fa11cdccaf863c08e1cc66f5df`） |
| 工具版本清单 | `work/build-04/toolchain.lock`（sha256 `bc70f4e9e436d2567c88588171d7fd4575a614c442874baa089407106bbf9358`） |

## 执行命令与结果

在 A12 服务器本人目录执行：

```sh
cd /root/231880224/e5-7/DevOps_1020_Student_Cloud/labs/A-buildchecker
git config --local user.name "231880224"
git config --local user.email "231880224@localhost"

python3 scripts/lab_cloud.py build --out work/build-03 --build-timeout 1200   # 15 passed
python3 scripts/lab_cloud.py e5 --out work/e5-01                              # 输出 1，MD/RD
python3 scripts/lab_cloud.py e6 --out work/e6-before                          # exit 1，2 findings
python3 scripts/lab_cloud.py e6 --fixed --out work/e6-after                   # exit 0，findings=[]
python3 scripts/verify_e6_evidence.py \
  --before work/e6-before/evidence/findings.json \
  --after work/e6-after/evidence/findings.json                                # passed=true
python3 -m unittest discover -s tests/e7 -v                                   # 6 tests OK
python3 scripts/lab_cloud.py gate --out work/e7-01                            # 8/8 passed

# 加入自主扩展测试后
python3 scripts/lab_cloud.py build --out work/build-04 --build-timeout 1200   # 16 passed
python3 scripts/lab_cloud.py gate --out work/e7-02                            # 8/8 passed
```

## 结果摘要

| 阶段 | 结果 |
| --- | --- |
| E5 | 程序输出 `1`；Make 声明 `main.o: main.c unused.h`；`config.h` 在 `trace/t.17:580` 被 cc1 成功打开；MD=`main.o→config.h`，RD=`main.o→unused.h` |
| E6 修复前 | 退出码 1；MISSING(`main.o`,`config.h`) 证据 `t.14:579`；REDUNDANT(`main.o`,`unused.h`) 证据 `make-db.txt:1053` |
| E6 修复后 | 退出码 0；findings=[]；输入哈希仅 Makefile 变化；`verify_e6_evidence.py` passed=true |
| E7 | 独立判定 6 tests OK；门禁 8/8 passed；original-1/2/3 错误集合完全一致；fixed 为空；build-failed=FAILED/CHECK_FAILED；unsupported=FAILED/UNSUPPORTED；timeout=TIMED_OUT/TIMEOUT |
| 自主测试 | `test_parent_relative_paths_normalize_but_cannot_escape_project_root`；服务测试 15→16 |
| 容器清理 | 门禁结束后 `docker ps -a` 为空 |

## 环境适配与限制

- Docker Hub 域名被解析到不可达地址，固定 digest `python:3.13-slim@sha256:f82c...cbcd74` 经 DaoCloud 镜像源拉取。
- Debian 官方 apt 源约 11 KB/s；为不修改教学 Dockerfile，由同一 digest 生成临时基础层（apt 源换 USTC），构建时临时覆盖 `BASE_IMAGE`；构建后 Dockerfile 已恢复，提交中只有新增测试。
- `doctor` 的内存必需项不满足（3.5 GiB < 4）；CPU、磁盘为建议项警告；服务器为小组共用，未扩容。
- `work/build-01`、`work/build-02` 是网络故障的失败记录，不纳入提交证据。

## 证据目录

- `work/build-03/`：基线构建（15 passed）、镜像 inspect、`env.json`
- `work/build-04/`：加入自测后的构建（16 passed）、镜像 inspect、`toolchain.lock`
- `work/e5-01/evidence/`：`program-output.txt`、`make-db.txt`、`trace/`、`build-stderr.log`
- `work/e6-before/evidence/`、`work/e6-after/evidence/`：`findings.json`、`actual-graph.json`、`declared-graph.json`、`processes.json`、`make-db.txt`、`trace/`
- `work/e7-02/gate/`：`gate-result.json`、`results.csv`、`unit-tests/`、`original-1/2/3/`、`fixed/`、`build-failed/`、`unsupported/`、`timeout/`
- `docs/实验报告.md`、`docs/验收记录.csv`

## CI 与合并门禁

待补：正常 / 失败 / 恢复 run URL、artifact 相对路径、main 分支保护配置、拒绝合并日志、修复后 MERGED 记录。

## 说明

服务器运行由本人账号在本人学号目录完成；证据来自同一台 A12 服务器。提交内容不含 `.env`、Token、SSH 私钥或服务器密码。
