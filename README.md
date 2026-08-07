# FixPilot

电脑故障排查助手：交互式问诊，一次只解决一个问题。基于 FastAPI + DeepSeek，支持知识库检索（RAG）与图片 OCR 识图（蓝屏代码、报错信息）。

## 功能

- 交互式问诊：一次只问一个关键判断题，逐步定位电脑故障（蓝屏、卡死、无法开机、网络异常等）
- 知识库检索：本地转写稿按时间戳切块 + BM25 检索，DeepSeek 生成回答
- 图片识图：RapidOCR 本地离线识别中文文字（如蓝屏代码、报错截图）
- 多窗口会话：每个问题独立窗口，左侧列表切换，本地持久化
- 对话分享：生成长图 / 只读网页链接（本地 html2canvas，不依赖外网）
- 邀请码 / 管理员体系，次数与有效期管理
- 玻璃拟态界面，提供多套登录页主题（`?bg=1` 到 `?bg=5`）

## 技术栈

- 后端：FastAPI + DeepSeek（deepseek-v4-flash）
- RAG：BM25（按时间戳切块）
- OCR：RapidOCR（onnxruntime）
- 前端：原生 HTML / CSS / JS

## 快速开始

1. 安装依赖

   ```bash
   pip install -r backend/requirements.txt
   ```

2. 配置环境变量（复制 `backend/.env.example` 为 `backend/.env`，填入）：

   ```bash
   DEEPSEEK_API_KEY=你的Key
   ADMIN_USERNAME=管理员账号
   ADMIN_PASSWORD=管理员密码
   FIXPILOT_TOKEN_SECRET=随机一长串
   ```

3. 准备知识库转写稿（文本文件，按时间戳切块），放在 `file/` 下。

4. 启动后端：

   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

5. 浏览器打开 <http://localhost:8000>

## 部署

支持根路径或子路径（如 `/fixpilot`）部署，Nginx 反向代理即可，聊天为流式输出，需关闭代理缓冲（`proxy_buffering off`）。

## 许可

[MIT](LICENSE)
