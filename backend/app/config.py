"""项目配置：从环境变量 / .env 读取。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（FixPilot）
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / "backend" / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

TRANSCRIPT_PATH = ROOT_DIR / os.getenv(
    "TRANSCRIPT_PATH", "file/2025全球最全电脑故障解决指南(720P).txt"
)

# 检索参数
TOP_K = 6

# 管理员账号（首次启动自动创建）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
# 会话 token 有效期（秒）
TOKEN_TTL = 60 * 60 * 24 * 7