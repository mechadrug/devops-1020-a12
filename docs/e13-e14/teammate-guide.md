# A12 E13–E14 组员操作与提交说明

主责：王备中 231880138。共同 PR：[PR18](https://github.com/mechadrug/devops-1020-a12/pull/18)。当前状态为候选待发布，B12 真实回执、同伴审查/合并及最终标签尚未齐；不能写成已发布 v0.9-rc。

## 先做审查

李玄同、丁宏业、胡凌岳任一位先检查 PR18 的三项修复：外部 fixed-MD SHA、非 root UID/GID、长任务健康检查；同时检查 B12_SOURCE.json、实际产物和已知限制。通过 Files changed → Review changes 提交具体正式 Review。发现问题写明文件、预期与实际，主责修复后再确认。暂不自行合并或创建标签，先与主责对齐 B12 签收和最终 CI。

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
python3 run_e11e12.py prepare
python3 labs/e13e14/prepare_a12_project.py
```

已有目录时先保留现场并确认当前 SHA，不重新 clone 覆盖，不重复 prepare。若 GitHub 不可达，可从主责课程包 reproduction/A12-e13-e14-source.bundle 克隆，随后设置 origin 为实际 A12 URL。prepare_a12_project 重建的是王备中维护的共享 A12 项目历史，它不是执行同学自己的开发贡献；必须注明提供者。

保存本人一项检测回归，并增加一项有实际价值的适配/契约测试或修复，记录本人贡献。不要仅改学号或机械复制主责测试。

```bash
mkdir -p work
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

公共 C1–C8、教师三项目和主责故障恢复可以作为注明来源的组级证据引用，不能冒充本人独立运行。若课程要求每人完整运行，则按教师手册在本人目录另做完整矩阵；不要复制王备中的 work 改名。B12 提供的 Reading Window bundle、候选和出处位于其仓库 evidence/E11-E12/241276010/real-project，或主责证据包 data/b12-project；目标保持原完整 SHA。

## 个人 PR 与网站 ZIP

在本人分支提交本人测试/修复和 docs/students/<学号>/e13-e14/ 下的报告、ADR、AI_USAGE，写实际完整 SHA、命令、结果与证据路径。推送后创建 PR，等待真实 CI 和同伴审查。未执行的项目写未执行，引用公共证据时列明执行者。

网站沿用每人一包：A12-E13-E14-231880224.zip、A12-E13-E14-231880397.zip、A12-E13-E14-231880398.zip。包括与本人报告对应的源码快照/完整 SHA、本人原始 work、请求、个人报告/贡献说明、本人 PR/CI；公共组级材料可共享并注明主责。排除 .git、真实 .env、密码/令牌与无关临时文件；允许为可重现输入保留 .bundle 历史包。检查可解压、产物 SHA 和密钥扫描，不把共同源码或别人的成功日志当成个人执行证明。

## 主责还需收齐的材料

1. B12 用 A12-E13-交给B12.zip 实际执行后的完整 OUT 归档和执行者身份、B 完整源码 SHA、该 SHA 的 CI 链接；同时请其签收我们对 Reading Window 的检测结果。
2. PR18 的同伴正式 Review，修复意见处理后再核对最终 CI。
3. 门禁齐备后确定已合并的集成 SHA，由获准人员创建且不移动 v0.9-rc，补 Release Notes 和最终 ZIP。

目前没有授权任何人借此文档跳过门禁、直接 push main 或覆盖已有标签。共享云机的旧 doctor 内存检查仍不通过，报告应保留该事实。
