from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

class FileType(str, Enum):
    """文件类型枚举"""
    IMAGE = "image"
    PDF = "pdf"
    EXCEL = "excel"

class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TableCell(BaseModel):
    """表格单元格"""
    text: str
    row: int
    column: int
    row_span: int = 1
    col_span: int = 1
    confidence: float = 0.0

class OCRResult(BaseModel):
    """OCR识别结果"""
    cells: List[TableCell]
    headers: List[str]
    raw_text: str
    file_type: FileType

class OCRTask(BaseModel):
    """OCR任务"""
    task_id: str
    file_path: str
    file_type: FileType
    status: TaskStatus
    result: Optional[OCRResult] = None
    error_message: Optional[str] = None 