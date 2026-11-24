# A12 E13–E14 组员操作与提交说明

主责：王备中 231880138。共同 PR：[PR18](https://github.com/mechadrug/devops-1020-a12/pull/18)。2026-11-24 更新：B12 徐泽宇真实回包已核验，李玄同正式 Review 已批准；仍待 B12 对 A 检测结果的确认、B 对应 CI、获准合并及最终标签。当前候选待发布，不能写成已发布 v0.9-rc。

## 已有审查与组员当前任务

李玄同已完成 [正式批准审查](https://github.com/mechadrug/devops-1020-a12/pull/18#pullrequestreview-6018226183)，无需其他成员为凑人数重复审查 PR18。三人现在均可从当前主责分支开展本人实验，不必等待另外两人回复。各自完成下文的个人运行、有效测试/修复、报告和个人 PR；个人 PR 仍需真实 CI 与同伴审查。若发现公共代码问题，附输入、完整 SHA、预期/实际及日志反馈主责。暂不自行合并 PR18 或创建标签，先对齐剩余组间签收与最终 CI。

## 在本人目录运行

学号：李玄同 231880224；丁宏业 231880397；胡凌岳 231880398。不要在别人的目录切换分支或停止容器。服务器仅 3.5 GiB 内存，四服务请预约顺序运行。

以下全部在课程 Linux 服务器执行。先把 SID 改为本人学号；不要保留 231880138 冒充本人。

```bash
SID=231880224
mkdir -p /root/$SID/e13-e14
cd /root/$SID/e13-e14
git clone --branch codex/e13-e14-231880138 git@github.com:mechadrug/devops-1020-a12.git buildchecker
cd buildchecker
git switch -c codex/e13-e14-$SID
git config --local user.name "$SID"
git config --local user.email "$SID@localhost"
git rev-parse HEAD
git status --short
python3 run_e11e12.py build
python3 run_e11e12.py test
PYTHONPATH=labs/e13e14 python3 -B -m unittest discover -s labs/e13e14/tests -p 'test*.py' -v
python3 run_e11e12.py prepare
python3 labs/e13e14/prepare_a12_project.py
```

已有目录时先保留现场并确认当前 SHA，不重新 clone 覆盖，不重复 prepare。若 GitHub 不可达，可从主责课程包 reproduction/A12-e13-e14-source.bundle 克隆，随后设置 origin 为实际 A12 URL。prepare_a12_project 重建的是王备中维护的共享 A12 项目历史，它不是执行同学自己的开发贡献；必须注明提供者。

先保存 git rev-parse HEAD 到本人 work/source-sha.txt，实验使用的 SHA 与后续个人测试/报告提交 SHA 分开记录。保存本人一项检测回归，并增加一项有实际价值的适配/契约测试或修复，记录本人贡献。不要仅改学号或机械复制主责测试。

```bash
mkdir -p work
git rev-parse HEAD > work/source-sha.txt
python3 run_e11e12.py run --request data/e13-a12-policy/request-e11-a.json --out work/e13-personal-A-01 > work/e13-personal-A-01.console.log 2>&1
```

## 四服务个人验证

选择本人端口：李 18181–18184，丁 18281–18284，胡 18381–18384。下例为李，其他两人同时改四个端口。必须与宿主编排脚本使用同一组环境变量。

```bash
export E14_ROOT=$PWD
export E14_IMAGE=$(docker image inspect "course-e11e12:$SID" --format '{{.Id}}')
export E14_UID=$(id -u) E14_GID=$(id -g) E14_DOCKER_GID=$(stat -c %g /var/run/docker.sock)
export E14_BUILDCHECKER_PORT=18181 E14_ECHECKER_PORT=18182 E14_DRAFT_PORT=18183 E14_MDFIXER_PORT=18184
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" config --quiet
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" up -d --wait
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" ps --format json > work/e14-personal-before.json
python3 labs/e13e14/orchestrate.py --request data/e13-a12-policy/request-e12.json --out work/e14-personal-01 > work/e14-personal-01.console.log 2>&1
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" logs --no-color > work/e14-personal-services.log
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" up -d --wait
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" ps --format json > work/e14-personal-after.json
docker compose -f labs/e13e14/compose.yaml -p "e14-$SID" down
python3 labs/e13e14/scan_runtime_logs.py work/e14-personal-01 work/e14-personal-services.log
```

每次使用新输出目录。五阶段均成功、同一 job/trace、报告目标提交一致、repair 使用当次报告摘要、accepted=true、最终无 MD，四角色日志确有本人 job，才能写通过。失败时保留原目录、日志和退出码，用新目录复测；只关闭本人 Compose 项目。

公共 C1–C8、教师三项目、主责故障恢复，以及徐泽宇提供的 B12 回包可以作为注明来源的组级证据引用，不能冒充本人独立运行。若课程要求每人完整运行，则按教师手册在本人目录另做完整矩阵；不要复制王备中的 work 改名。B12 提供的 Reading Window bundle、候选和出处位于其仓库 evidence/E11-E12/241276010/real-project，或主责证据包 data/b12-project；目标保持原完整 SHA。

## 个人 PR 与网站 ZIP

在本人分支提交本人测试/修复和 docs/students/<学号>/e13-e14/ 下的报告、ADR、AI_USAGE，写实际完整 SHA、命令、结果与证据路径。推送后创建 PR，等待真实 CI 和同伴审查。未执行的项目写未执行，引用公共证据时列明执行者。

网站沿用每人一包：A12-E13-E14-231880224.zip、A12-E13-E14-231880397.zip、A12-E13-E14-231880398.zip。包括与本人报告对应的源码快照/完整 SHA、本人原始 work、请求、个人报告/贡献说明、本人 PR/CI；公共组级材料可共享并注明主责。排除 .git、真实 .env、密码/令牌与无关临时文件；允许为可重现输入保留 .bundle 历史包。检查可解压、产物 SHA 和密钥扫描，不把共同源码或别人的成功日志当成个人执行证明。

## 主责还需收齐的材料

1. 已收到 `B12_E13_to_A12.tar.gz`：执行者徐泽宇 241276010，B 工具 `1fc3728c2d10e840f502c5f30716e69b31a551ca`；A policy target `9c312e412e6c3efb3dbed3b3fd4db50afccfb52e` 成功消费，8 项行为测试通过。主责已核对原交接包与 685 个清单引用，旧 work 中的 PENDING 不回写。B C2/C3 是构建后拒绝，与 A 的提前拒绝时机不同。
2. 仍请 B12 给出该执行 SHA 的真实 CI，并确认接收我们对 Reading Window target `1cb95780bce185c11570ca0bc2096fd9ca687ac9` 的检测结果；主责已准备 `A12-E13-回传B12-检测结果与核验.zip`。组员无需各自重复联系 B 或索取服务器密码。
3. 李玄同 Review 已完成。主责更新交接文档后核对新 CI；门禁齐备并获准合并后记录集成 SHA，复核合并后 CI，再由获准人员创建且不移动 v0.9-rc，补 Release Notes 和最终 ZIP。

目前没有授权任何人借此文档跳过门禁、直接 push main 或覆盖已有标签。共享云机的旧 doctor 内存检查仍不通过，报告应保留该事实。
