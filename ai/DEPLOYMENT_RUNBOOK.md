# FixPilot 部署与更新运行手册

> 适用对象：FixPilot 维护者、接手项目的 AI、受授权的运维人员。
> 最后更新：2026-08-10（Asia/Shanghai）
> 状态：基于当前仓库代码编写的可执行基线。尚未根据某一台真实线上服务器实测；带有 `<...>` 的值必须由项目所有者在安全渠道提供，不能猜测或写入仓库。

## 0. `git push` 不等于上线

```text
本地代码 → git commit → git push 到 GitHub
                                ↓
                         线上服务器 git pull
                                ↓
                         重启 FixPilot 服务
                                ↓
                          健康检查与人工冒烟
```

GitHub 只保存代码。除非未来另行配置 CI/CD，线上服务器不会因为 `git push` 自动更新。

当前推荐形态：**GitHub + 一台 Linux 服务器 + systemd + Nginx + 单个 Uvicorn worker + SQLite**。它适合 FixPilot 现阶段的小规模邀请制 Beta，不引入 Docker、微服务或复杂编排。

## 1. 当前代码事实与不可违反的边界

| 项目 | 当前事实 | 部署要求 |
| --- | --- | --- |
| Web 服务 | FastAPI / Uvicorn；健康接口 `GET /api/health` | Uvicorn 监听 `127.0.0.1:8000`，Nginx 提供 HTTPS |
| 流式聊天 | SSE / 流式响应 | Nginx 必须 `proxy_buffering off`，否则回答会攒到最后才显示 |
| 数据库 | SQLite：`backend/fixpilot.db`，启用 WAL | 只运行 **1 个** Uvicorn worker；多 worker 可能产生 SQLite 写锁竞争 |
| 数据内容 | 账号、邀请码、会话、图片、偏好、用户自定义 API 配置 | 数据库与备份均属敏感数据，不得提交、公开下载或发到聊天中 |
| 运行配置 | `backend/.env` | 仅在服务器保存；不得提交、截图、粘贴到日志或交接文档 |
| 知识库 / 图片 | `file/` | 线上必须保留并由服务进程可读；它同样不在 Git 中 |

`.gitignore` 已排除 `backend/.env`、`backend/fixpilot.db`、`file/`、SQLite 的 `-wal/-shm` 文件。它们不是遗漏文件，不能为了“让线上和本地一致”而强行 `git add`。

## 2. 上线前必须确认的生产清单

以下信息保存在密码管理器或私有运维记录中，不写进本仓库：

```text
服务器地址：<server-host>
登录用户名：<deploy-user>
线上项目目录：<app-dir，例如 /srv/fixpilot>
虚拟环境目录：<venv-dir，例如 /srv/fixpilot/.venv>
systemd 服务名：<service-name，建议 fixpilot>
Nginx 站点配置：<nginx-site-file>
公网域名：<domain>
备份目录：<backup-dir>
```

没有这些信息时，AI 只能给命令模板，**不得假装已上线、猜目录、连接陌生服务器或触碰生产数据库**。

## 3. 首次部署：推荐做法

> 仅由拥有服务器权限的人执行。所有示例值都要替换；不要把真实密码、Token、API Key 放入 shell 历史或截图。

### 3.1 准备代码和 Python 环境

```bash
sudo mkdir -p /srv/fixpilot
sudo chown -R <deploy-user>:<deploy-user> /srv/fixpilot
git clone https://github.com/Tsang12140/FixPilot.git /srv/fixpilot
cd /srv/fixpilot
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

将生产所需的 `backend/.env`、完整 `file/` 目录，以及**经核验的数据库备份**通过安全方式复制到服务器。迁移已有用户时，先恢复数据库再启动。

生产 `.env` 至少应有：

```dotenv
DEEPSEEK_API_KEY=<platform-key>
DEEPSEEK_BASE_URL=<provider-base-url>
DEEPSEEK_MODEL=<provider-model-id>
TRANSCRIPT_PATH=<file-directory-under-project>
ADMIN_USERNAME=<admin-name>
ADMIN_PASSWORD=<strong-unique-password>
FIXPILOT_TOKEN_SECRET=<long-random-secret>
```

`FIXPILOT_TOKEN_SECRET` 必须长期稳定；更换它会使既有登录令牌失效。建议仅在服务器生成并保存到密码管理器：

```bash
openssl rand -hex 32
```

### 3.2 systemd 服务

创建 `/etc/systemd/system/fixpilot.service`，并按实际用户/路径替换：

```ini
[Unit]
Description=FixPilot FastAPI service
After=network.target

[Service]
User=<deploy-user>
Group=<deploy-user>
WorkingDirectory=/srv/fixpilot/backend
Environment=PYTHONUNBUFFERED=1
ExecStart=/srv/fixpilot/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fixpilot
sudo systemctl status fixpilot --no-pager
curl -fsS http://127.0.0.1:8000/api/health
```

### 3.3 Nginx 反向代理

Nginx 站点配置必须保留流式响应相关项：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

正式公网开放前必须设置 HTTPS、域名和防火墙；不要直接把 8000 端口暴露给公网。

## 4. 每次 `git push` 后的标准更新流程

AI 成功推送后，必须明确告诉项目所有者：**“GitHub 已更新；线上尚未更新，请执行本节。”**

### 4.1 本地：确认推送内容

```bash
git status --short
git log -1 --oneline
git push origin main
```

推送前只提交本次明确要上线的文件；不得夹带 `.env`、数据库、`-wal/-shm`、个人工具缓存或未知临时文件。

### 4.2 线上：备份、更新、重启、核验

```bash
ssh <deploy-user>@<server-host>
cd <app-dir>

# 1) 记录现有版本，作为回滚点
git rev-parse --short HEAD

# 2) 备份数据库；路径和目录必须替换为真实值
mkdir -p <backup-dir>
sqlite3 backend/fixpilot.db ".backup '<backup-dir>/fixpilot-$(date +%F-%H%M%S).db'"

# 3) 仅接受快进更新，避免线上历史被意外改写
git pull --ff-only origin main

# 4) 只有本次改了依赖时才重新安装
git diff --name-only HEAD@{1} HEAD | grep -qx 'backend/requirements.txt' && .venv/bin/pip install -r backend/requirements.txt

# 5) 重启并检查
sudo systemctl restart fixpilot
sudo systemctl is-active --quiet fixpilot
curl -fsS http://127.0.0.1:8000/api/health
git rev-parse --short HEAD
```

最后访问正式域名，最小人工冒烟包括：登录、打开历史对话、发送一条普通故障描述、确认流式回答出现。本次若涉及移动端、图片、模型配置、风险提示或分享页，按 [`RELEASE_READINESS.md`](RELEASE_READINESS.md) 增加对应检查。

### 4.3 何时要额外操作

| 本次改动 | 额外动作 |
| --- | --- |
| `backend/requirements.txt` | 重装依赖，再重启服务 |
| `backend/.env` 变量 | 在服务器私下更新 `.env`，重启服务；不得 Git 提交 |
| Nginx 配置 | `sudo nginx -t` 后 `sudo systemctl reload nginx` |
| 数据库结构 / 迁移逻辑 | 先完成数据库备份和恢复演练；首次启动会执行当前轻量迁移 |
| `file/` 下知识库或图片 | 用安全文件同步方式部署，确认权限后重启；不通过 Git 同步 |
| 纯前端、后端逻辑或 Prompt | 正常 `git pull` + 服务重启；浏览器硬刷新或无痕验证一次 |

## 5. 更新失败或上线后异常：安全回滚

### 5.1 服务起不来

```bash
sudo systemctl status fixpilot --no-pager
sudo journalctl -u fixpilot -n 120 --no-pager
```

先看错误再决定，不要连续重启碰运气。日志可能含用户内容或供应商细节，分享前先脱敏。

### 5.2 最新版本异常

回到第 4.2 节记录的上一版提交；不要用 `git reset --hard`：

```bash
cd <app-dir>
git checkout --detach <known-good-commit>
sudo systemctl restart fixpilot
curl -fsS http://127.0.0.1:8000/api/health
```

这只是临时恢复。随后必须在本地修复、生成新提交并重新按标准流程上线；不要把线上临时改动当作正式修复。

### 5.3 数据库恢复

只有确认数据库损坏或误操作、且服务已停止时，才可恢复备份。恢复前复制当前数据库作二次保护；WAL 模式还需处理同目录的 `-wal` / `-shm` 文件。此操作可能丢失备份后的数据，必须由项目所有者明确授权。

## 6. AI 的部署权限规则

任何接手 AI 都必须：

1. 先读 [`../AGENTS.md`](../AGENTS.md)、[`WORK_LOG.md`](WORK_LOG.md) 和本文件。
2. 区分“Git 已推送”和“线上已更新”；绝不把前者称作上线。
3. 未获明确服务器授权时，只给命令模板，不执行 SSH、重启、数据库复制、删除或 Git 历史重写。
4. 不读取、不显示、不记录 `.env`、API Key、密码、令牌、生产数据库内容或完整生产日志。
5. 对每次线上操作在私有运维记录中写明：时间、环境、部署提交、健康检查结果、回滚点；敏感值脱敏。
6. 配置与本文不一致时，先修订手册或标记差异，不能凭记忆跳过核验。

## 7. 当前未完成的上线前事项

本手册解决“如何部署与更新”，不代表已满足发布条件。仍以 [`RELEASE_READINESS.md`](RELEASE_READINESS.md) 为准：

- 用实际提供商/模型跑完实时回归基线；
- 验证额度耗尽、4xx/5xx、空流回复及用户可见恢复路径；
- 用真实线上数据库完成一次备份与恢复演练；
- 完成隐私/保留说明，并告知测试者管理员可查看会话；
- 公开发布前补 HTTPS、日志轮转、监控、限流与应急流程。

## 8. 把模板变成你的真实一键流程

只需由项目所有者安全确认以下信息：

1. 线上部署在哪里（云服务器、家用电脑、PaaS，还是尚未部署）？
2. 线上项目路径和 Python 虚拟环境路径是什么？
3. 是否已使用 Nginx + systemd？若不是，当前靠什么保持服务运行？
4. 数据库和 `file/` 目录在哪里？备份保留多久？

确认后，把第 2 节的占位符换成实际**非敏感**路径/服务名，并把第 4 节命令收敛成可直接复制的一段。
