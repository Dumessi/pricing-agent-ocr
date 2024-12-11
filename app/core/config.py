from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', '.env')
load_dotenv(env_path)

class Settings(BaseSettings):
    # MongoDB配置
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "pricing_agent")

    # 应用配置
    APP_NAME: str = os.getenv("APP_NAME", "Pricing Agent OCR")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 文件上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf", "xlsx", "xls"]
    MAX_FILES_PER_REQUEST: int = int(os.getenv("MAX_FILES_PER_REQUEST", "5"))

    # OCR配置
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "ch")
    OCR_USE_ANGLE_CLASS: bool = os.getenv("OCR_USE_ANGLE_CLASS", "True").lower() == "true"
    OCR_USE_GPU: bool = os.getenv("OCR_USE_GPU", "False").lower() == "true"
    MIN_CONFIDENCE: float = float(os.getenv("MIN_CONFIDENCE", "0.5"))

    class Config:
        env_file = env_path

settings = Settings() 