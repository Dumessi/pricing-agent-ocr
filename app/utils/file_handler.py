import os
import uuid
from fastapi import UploadFile
from typing import List
from app.core.config import settings
from app.models.ocr import FileType

def get_file_type(filename: str) -> FileType:
    """根据文件扩展名判断文件类型"""
    ext = filename.lower().split('.')[-1]
    if ext in ['jpg', 'jpeg', 'png', 'pdf']:
        return FileType.IMAGE
    elif ext in ['xlsx', 'xls']:
        return FileType.EXCEL
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def is_valid_file(file: UploadFile) -> bool:
    """验证文件是否合法"""
    # 检查文件大小
    try:
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(0)
        if size > settings.MAX_UPLOAD_SIZE:
            return False
    except Exception:
        return False

    # 检查文件扩展名
    ext = file.filename.lower().split('.')[-1]
    return ext in settings.ALLOWED_EXTENSIONS

async def save_upload_file(file: UploadFile) -> str:
    """保存上传的文件并返回保存路径"""
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 生成唯一文件名
    ext = file.filename.lower().split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    
    # 保存文件
    try:
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)
        return file_path
    except Exception as e:
        raise Exception(f"Failed to save file: {str(e)}")

def clean_old_files():
    """清理过期的上传文件"""
    # TODO: 实现文件清理逻辑
    pass 