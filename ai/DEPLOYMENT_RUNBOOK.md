# FixPilot 线上部署与更新手册（实际环境）

> 适用对象：项目所有者与后续接手的 AI。
> 最后核对：2026-08-10（Asia/Shanghai）
> 本文记录的是 **FixPilot 当前已验证的实际做法**，不是通用服务器教程。没有明确授权时，AI 不得自行 SSH、重启线上进程、读取 `.env`、数据库或日志。

## 0. 核心事实

- `git push origin main` 只把代码推到 GitHub；线上服务不会自动更新。
- 线上项目目录：`/www/wwwroot/fixpilot`
- 后端工作目录：`/www/wwwroot/fixpilot/backend`
- 虚拟环境：后端目录下的 `.venv`
- Uvicorn 监听：`0.0.0.0:8135`
- 当前进程管理方式：`pkill` 停旧进程，再用 `nohup` 后台启动；**不是 systemd**。
- 服务日志：`/www/wwwroot/fixpilot/backend/uvicorn.log`
- 健康接口：`/api/health`
- SQLite 数据库、`.env`、`file/` 知识库和图片均不通过 Git 同步，不能为了“同步完整”而提交。

> 不要在没有新事实的情况下，把本文改成 systemd、Docker、PM2、Nginx 细节或别的端口。当前线上反向代理如何管理尚未在本手册确认，不能猜测或随意改动。

## 1. 每次日常上线：唯一标准流程

前提：本地改动已验证，准备上线的文件已提交。以下命令按顺序执行。

### 1.1 本地：提交并推送

```bash
# 只暂存本次明确要上线的文件；不要 git add .
git add <改动的文件>
git commit -m "说明本次改动"
git push origin main
```

推送成功后，AI 必须说清楚：**“GitHub 已更新；线上尚未更新。请继续执行 1.2。”**

### 1.2 服务器：拉取代码

```bash
cd /www/wwwroot/fixpilot
git pull origin main
```

如果偶发出现 GitHub 的 `GnuTLS/TLS` 网络错误，不代表仓库没有新版本：先重试一次，确认网络正常后再继续。不要因为一次网络抖动去重置 Git 历史或覆盖线上文件。

### 1.3 服务器：仅在依赖变更时安装依赖

只有本次提交改动了 `backend/requirements.txt`，才执行：

```bash
cd /www/wwwroot/fixpilot/backend
.venv/bin/pip install -r requirements.txt
```

普通前端、后端逻辑、Prompt、文档改动不需要重复安装依赖。

### 1.4 服务器：重启 Uvicorn

```bash
cd /www/wwwroot/fixpilot/backend

# 停掉旧服务
pkill -f "uvicorn app.main:app"
sleep 1

# 用当前仓库代码启动新服务
nohup .venv/bin/python .venv/bin/uvicorn app.main:app \
  --host 0.0.0.0 --port 8135 > uvicorn.log 2>&1 &

# 等待启动并查看最终日志
sleep 3
tail -n 20 uvicorn.log
```


日志里看到 `Application startup complete` 才算服务启动成功。可再补一条无副作用的健康检查：

```bash
curl -fsS http://127.0.0.1:8135/api/health
```

预期返回包含 `"status":"ok"` 的 JSON。若启动失败，先查看 `tail -n 80 uvicorn.log`，不要连续盲目重启。

### 1.5 浏览器：清掉静态缓存并人工验证

1. 强制刷新：`Ctrl + F5`。
2. 登录后打开一个已有对话，确认页面不空白。
3. 发一条普通问题，确认能出现流式回复。
4. 本次若改了移动端、图片、模型、风险提示、分享页，再做对应人工检查。

## 2. 前端缓存规则

静态资源改动后，浏览器可能继续使用旧的 JavaScript 或 CSS；强刷不一定能弥补服务器/缓存层的旧版本引用。

- 改 `backend/static/app.js`：更新 `backend/static/index.html` 里的 `app.js?v=<新版本>`。
- 改 `backend/static/style.css`：更新 `style.css?v=<新版本>`。
- 只在对应静态文件改动时递增其版本号；不要每次无关提交都乱改版本号。
- 提交、推送、服务器 `git pull`、重启后，再 `Ctrl+F5` 验证。

## 3. 已验证事故案例：空白页与 `autoResize`

### 现象

强刷后页面只有底色，没有界面。浏览器 `F12 → Console` 报错：

```text
Uncaught ReferenceError: autoResize is not defined at app.js?v=47:2482:33
```

### 实际根因

- 本地 `app.js` 已写入 `autoResize()`，但当时没有提交和 push；线上 `git pull` 因而拉不到该函数。
- `index.html` 仍指向 `app.js?v=47`，旧缓存也继续指向旧 bundle。
- 事件绑定已经调用 `autoResize`，函数缺失会在页面初始化时抛异常，导致整页脚本中断、界面空白。

### 当时如何修复

1. 对照本地和线上代码，确认本地函数存在、线上版本没有。
2. 把 `autoResize()` 加入 `backend/static/app.js`。
3. 把 `index.html` 中 `app.js?v=47` 升为 `app.js?v=48`。
4. 提交 `01fdb37`，push 到 GitHub。
5. 服务器执行：`git pull origin main` → 按第 1.4 节重启 Uvicorn → 检查日志。
6. 浏览器 `Ctrl+F5` 后，空白页恢复。

本事件已记录于：

- `ai/WORK_LOG.md`（提交 `f2ce670`）
- `reports/fixed.md`（提交 `f2ce670`）

### 下次遇到空白页的最短排查路径

1. `F12 → Console`，先拿到第一个报错和资源版本号，例如 `app.js?v=47`。
2. 检查本地对应函数/代码是否真的存在。
3. `git log -1 --oneline`：确认本地修复是否已 commit。
4. `git push origin main` 后，服务器确认 `git pull` 确实成功。
5. 静态资源有改动时同步递增 `?v=`；重启服务后再 `Ctrl+F5`。
6. 仍失败才查看 `uvicorn.log`。不要先猜 API、数据库或前端样式。

## 4. 补充的安全操作

### 4.1 涉及数据库结构或数据的更新

普通代码更新不应操作数据库文件。只有数据库结构、迁移逻辑或数据修复明确需要时：

1. 先征得项目所有者同意；
2. 先做可恢复备份；
3. 记录当前 Git 提交；
4. 再上线并验证登录、历史对话和管理员功能。

数据库可能包含用户对话和自定义 API 配置，备份不能上传到 GitHub、公开网盘或聊天窗口。

### 4.2 回滚原则

如果新版本已启动但核心功能异常：

1. 记录当前提交和 `uvicorn.log` 的脱敏片段；
2. 在本地修复后走一条新的提交上线；
3. 未经项目所有者明确批准，任何 AI 不得在线上执行 `git reset --hard`、删除数据库、删除 `.env` 或覆盖 `file/`。

## 5. 后续 AI 的固定职责

每个接手 AI 在“push / 上线 / 线上异常”任务中必须：

1. 先读 `AGENTS.md`、`ai/WORK_LOG.md`、本文件及 `ai/RELEASE_READINESS.md`。
2. 每次成功 `git push` 后，提示项目所有者执行本手册第 1.2—1.5 节；不能把 push 说成已上线。
3. 没有明确授权时，只给出上述命令，不执行服务器操作。
4. 不读取、不复述 `.env`、API Key、密码、Token、生产数据库或完整线上日志。
5. 修复线上问题后，按 `AGENTS.md` 写入 `ai/WORK_LOG.md`；若是已验证的 Bug，还要写 `reports/fixed.md`。
6. 发现真实部署方式与本文不一致时，先读取已有记录、向项目所有者确认，再更新本文；不要以通用经验替代实际事实。

## 6. 上线不等于可以公开发布

本手册只处理部署。是否可扩大测试或公开使用仍以 `ai/RELEASE_READINESS.md` 为准，尤其要完成实际模型的回归、异常回复/额度耗尽验证、数据备份恢复演练以及隐私告知。
