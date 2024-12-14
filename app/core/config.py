from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv
from pathlib import Path

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 加载.env文件
env_path = os.path.join(BASE_DIR, 'config', '.env')
load_dotenv(env_path)

class Settings(BaseSettings):
    # 阿里云OCR配置
    ALIYUN_ACCESS_KEY_ID: str = os.getenv("ALIYUN_ACCESS_KEY_ID", "")
    ALIYUN_ACCESS_KEY_SECRET: str = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "")
    ALIYUN_ENDPOINT: str = os.getenv("ALIYUN_ENDPOINT", "ocr-api.cn-shanghai.aliyuncs.com")

    # MongoDB配置
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    MONGODB_DB: str = os.getenv("MONGODB_DB", "pricing_agent")

    # 应用配置
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Pricing Agent OCR")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # 文件上传配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "pdf", "xlsx", "xls"]
    MAX_FILES_PER_REQUEST: int = int(os.getenv("MAX_FILES_PER_REQUEST", "5"))

    # OCR基础配置
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "ch")
    OCR_USE_ANGLE_CLASS: bool = os.getenv("OCR_USE_ANGLE_CLASS", "True").lower() == "true"
    OCR_USE_GPU: bool = os.getenv("OCR_USE_GPU", "False").lower() == "true"
    MIN_CONFIDENCE: float = float(os.getenv("MIN_CONFIDENCE", "0.5"))

    # OCR检测配置
    OCR_DET_ALGORITHM: str = os.getenv("OCR_DET_ALGORITHM", "DB")
    OCR_ENABLE_MKLDNN: bool = os.getenv("OCR_ENABLE_MKLDNN", "True").lower() == "true"
    OCR_LIMIT_SIDE_LEN: int = int(os.getenv("OCR_LIMIT_SIDE_LEN", "960"))
    OCR_DET_LIMIT_SIDE_LEN: int = int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "960"))
    OCR_DET_DB_THRESH: float = float(os.getenv("OCR_DET_DB_THRESH", "0.3"))
    OCR_DET_DB_BOX_THRESH: float = float(os.getenv("OCR_DET_DB_BOX_THRESH", "0.5"))
    OCR_DET_DB_UNCLIP_RATIO: float = float(os.getenv("OCR_DET_DB_UNCLIP_RATIO", "1.6"))

    # OCR识别配置
    OCR_REC_ALGORITHM: str = os.getenv("OCR_REC_ALGORITHM", "CRNN")
    OCR_REC_BATCH_NUM: int = int(os.getenv("OCR_REC_BATCH_NUM", "6"))
    OCR_ENABLE_TABLE: bool = os.getenv("OCR_ENABLE_TABLE", "True").lower() == "true"
    OCR_TABLE_MAX_LEN: int = int(os.getenv("OCR_TABLE_MAX_LEN", "488"))
    OCR_TABLE_MODEL: str = os.getenv("OCR_TABLE_MODEL", "TableStructure")

    # 表格识别配置
    TABLE_MIN_ROW_HEIGHT: int = int(os.getenv("TABLE_MIN_ROW_HEIGHT", "20"))
    TABLE_MIN_COL_WIDTH: int = int(os.getenv("TABLE_MIN_COL_WIDTH", "40"))
    TABLE_MERGE_CELLS_THRESHOLD: int = int(os.getenv("TABLE_MERGE_CELLS_THRESHOLD", "5"))
    TABLE_HEADER_ROWS: int = int(os.getenv("TABLE_HEADER_ROWS", "1"))

    class Config:
        env_file = env_path
        extra = "allow"  # 允许额外的字段

settings = Settings() 