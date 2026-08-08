# 账号密码绑定系统（软引导方案）

## Context

当前登录页有两种方式：邀请码登录（普通用户）、管理员登录（后台管理）。普通用户每次跨设备登录都需要重新输邀请码 + PIN，体验受限。

用户想加一个"账号密码登录"方式，但又不想强制弹窗打扰新用户。选定的平衡方案是**软引导**：
- 邀请码登录后直接进主界面（零摩擦）
- 主界面 topbar 上放一个"绑定账号"按钮（仅邀请码用户可见、且未绑定时才显示）
- 用户主动点击 → 弹出绑定弹窗 → 设置账号密码 → 该邀请码与账号绑定
- 下次登录时，"账号密码登录"标签可用，凭账号密码直接登录（仍走原邀请码的配额和会话）

## 设计要点

### 数据模型
新增 `users` 表，与 `invite_codes` **一对一**绑定：
```sql
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  invite_code TEXT UNIQUE NOT NULL,   -- 一对一绑定邀请码
  created_at TEXT NOT NULL,
  FOREIGN KEY (invite_code) REFERENCES invite_codes(code)
);
```
- **会话归属不变**：`conversations.invite_code` 仍是 owner key。账号用户登录后 token 里带 `code` 字段，`_owner(payload)` 仍返回邀请码。**零迁移**。
- **配额不变**：配额仍挂在邀请码上，账号登录继承。
- **绑定不可逆**：MVP 不做解绑，需要时管理员手工改库。

### 登录页 Tab 合并
- 原"管理员登录" tab → 改名"账号密码登录"
- 这个 tab 同时接受**管理员账号**和**用户账号**
- 后端 `/api/auth/account-login` 先查 `admin` 表，再查 `users` 表，命中哪个就返回对应 role 的 token

### 复用现有能力
- 密码哈希：复用 [auth.py:12](file:///d:/personal/cc/FixPilot/backend/app/auth.py#L12) 的 `hash_password` / `verify_password`（pbkdf2_hmac sha256 100k 迭代，salt$digest 格式）
- Token：复用 [auth.py:57](file:///d:/personal/cc/FixPilot/backend/app/auth.py#L57) 的 `make_token` / `verify_token`，payload 加 `username` 字段
- 弹窗模式：复用 [index.html:72](file:///d:/personal/cc/FixPilot/backend/static/index.html#L72) 的 PIN modal 模式（scrim + card + close + title + body）
- topbar 按钮模式：复用 [index.html:129](file:///d:/personal/cc/FixPilot/backend/static/index.html#L129) 的 adminBtn 模式（display:none 默认，JS 控制显示）

## 后端改动

### 1. [backend/app/db.py](file:///d:/personal/cc/FixPilot/backend/app/db.py)
- `init_db()` 的 `executescript` 里加 `users` 表 CREATE 语句
- 新增函数：
  - `create_user(username, password_hash, invite_code) -> None`（INSERT OR IGNORE）
  - `get_user_by_username(username) -> Optional[dict]`
  - `get_user_by_invite_code(code) -> Optional[dict]`（用于判断是否已绑定）

### 2. [backend/app/main.py](file:///d:/personal/cc/FixPilot/backend/app/main.py)
- 新增 Pydantic 模型：
  - `BindAccountRequest { username, password }`
  - `AccountLoginRequest { username, password }`（替代 `AdminLoginRequest`，或并存）
- 新增端点 `POST /api/auth/bind-account`：
  - 要求 `role == "user"` 的 token（即邀请码登录用户）
  - 校验 username 格式（3-20 位，字母数字下划线，转小写）
  - 校验 password 长度（≥6）
  - 检查 username 不重复、当前邀请码未绑定
  - 调 `db.create_user(username, hash_password(password), code)`
  - 返回 `{ok: true, username}`
- 改造 `POST /api/auth/admin-login` → 重命名为 `/api/auth/account-login`：
  - 先查 `db.get_admin(username)`，命中且密码对 → 返回 admin token
  - 否则查 `db.get_user(username)`，命中且密码对 → 返回 user token（payload 带 `code`）
  - 都不命中 → 401
- 新增端点 `GET /api/auth/bind-status`（或扩展 `/api/auth/me`）：
  - 返回当前邀请码是否已绑定账号、绑定到的 username
  - 用于前端决定是否显示"绑定账号"按钮

### 3. [backend/app/auth.py](file:///d:/personal/cc/FixPilot/backend/app/auth.py)
- 无需改动，复用现有 `hash_password` / `verify_password` / `make_token` / `verify_token`

## 前端改动

### 1. [backend/static/index.html](file:///d:/personal/cc/FixPilot/backend/static/index.html)
- **登录 tab 改名**：`管理员登录` → `账号密码登录`（[L40](file:///d:/personal/cc/FixPilot/backend/static/index.html#L40)）
- **adminPanel 输入框 placeholder 改名**（[L56-58](file:///d:/personal/cc/FixPilot/backend/static/index.html#L56)）：
  - `管理员账号` → `账号`
  - `登录后台` → `登录`
- **新增"绑定账号"按钮**（在 topbar-right，adminBtn 旁）：
  ```html
  <button class="logout-btn" id="bindAccountBtn" aria-label="绑定账号" style="display:none">
    <svg viewBox="0 0 24 24" ...><!-- 用户图标 --></svg>
  </button>
  ```
- **新增绑定弹窗**（仿 PIN modal 模式，放在 adminModal 旁）：
  ```html
  <div class="bind-scrim" id="bindModal">
    <div class="bind-card">
      <button class="pin-close" id="bindClose">...</button>
      <div class="bind-title">绑定账号密码</div>
      <div class="bind-desc">设置账号密码后，下次可用账号密码登录，无需再输邀请码</div>
      <input class="login-input" id="bindUser" placeholder="设置账号（3-20 位字母/数字/下划线）" />
      <input class="login-input" id="bindPass" type="password" placeholder="设置密码（≥6 位）" />
      <button class="login-btn" id="bindSubmitBtn">绑定</button>
      <div class="login-err" id="bindErr"></div>
    </div>
  </div>
  ```

### 2. [backend/static/app.js](file:///d:/personal/cc/FixPilot/backend/static/app.js)
- **绑定按钮显示逻辑**：在 `enterApp()` 或登录成功后的 UI 更新里：
  - 若 `user.role === "user"` 且未绑定 → `bindAccountBtn.style.display = 'inline-flex'`
  - 调 `/api/auth/me` 拿绑定状态（或在 invite-login 响应里附带）
- **绑定按钮点击** → 打开 `bindModal`，聚焦 `bindUser`
- **绑定提交逻辑**：
  - 前端校验 username/password 格式
  - POST `/api/auth/bind-account` { username, password }
  - 成功 → toast `绑定成功，下次可用账号密码登录` + 关闭弹窗 + 隐藏 bindAccountBtn
  - 失败 → 显示错误信息
- **账号密码登录改造**：
  - `adminLoginBtn` 的点击处理改为调 `/api/auth/account-login`
  - 响应处理：`role === "admin"` → 显示 adminBtn（齿轮）；`role === "user"` → 显示普通用户 UI
- **登录后状态恢复**（页面加载时）：
  - 调 `/api/auth/me` → 拿 role + 绑定状态
  - 邀请码用户且未绑定 → 显示 bindAccountBtn

### 3. [backend/static/style.css](file:///d:/personal/cc/FixPilot/backend/static/style.css)
- 新增 `.bind-scrim` / `.bind-card` 样式（复用 `.pin-scrim` / `.pin-card` 模式，可直接 alias 或复制）
- bind-card 内的 `.login-input` / `.login-btn` 已有现成样式，无需新增

## 关键文件清单

| 文件 | 改动 |
|------|------|
| [backend/app/db.py](file:///d:/personal/cc/FixPilot/backend/app/db.py) | 加 `users` 表 + 3 个 CRUD 函数 |
| [backend/app/main.py](file:///d:/personal/cc/FixPilot/backend/app/main.py) | 加 `/api/auth/bind-account`、改造 `/api/auth/admin-login` → `/api/auth/account-login`、扩展 `/api/auth/me` |
| [backend/static/index.html](file:///d:/personal/cc/FixPilot/backend/static/index.html) | tab 改名、placeholder 改名、加 bindAccountBtn、加 bindModal |
| [backend/static/app.js](file:///d:/personal/cc/FixPilot/backend/static/app.js) | 绑定流程、账号登录改造、按钮显示逻辑 |
| [backend/static/style.css](file:///d:/personal/cc/FixPilot/backend/static/style.css) | bind-scrim/bind-card 样式（可复用 pin-scrim/pin-card） |

## 验证方案

1. **启动后端**：`python -m app.main` 或宝塔入口，确认 `users` 表自动建好（`sqlite3 fixpilot.db ".schema users"`）
2. **邀请码登录**：用现有邀请码登录 → 进主界面 → topbar 右侧应出现"绑定账号"按钮
3. **绑定流程**：点绑定按钮 → 输入 username/password → 提交 → toast 成功 → 按钮消失
4. **账号密码登录**：退出 → 切到"账号密码登录" tab → 输入刚绑定的账号密码 → 应正常进主界面，会话列表保持
5. **管理员登录**：切到"账号密码登录" tab → 输入 admin 账号密码 → 应进主界面且齿轮按钮可见
6. **重复绑定校验**：已绑定的邀请码再尝试绑定 → 应返回错误
7. **用户名重复校验**：用已存在的 username 绑定 → 应返回错误
8. **浏览器开发者工具**：检查 Network 中各 API 调用返回 200/4xx 正确，localStorage 中 token 正确写入
