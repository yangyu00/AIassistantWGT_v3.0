import os
from pathlib import Path
from dotenv import load_dotenv

# 获取根目录
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    # --- 应用配置 ---
    API_HOST: str = os.getenv("API_HOST")
    API_PORT: int = int(os.getenv("API_PORT"))


# 全局实例
settings = Config()
