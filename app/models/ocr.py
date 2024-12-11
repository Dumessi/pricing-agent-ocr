from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

class FileType(str, Enum):
    IMAGE = "image"
    EXCEL = "excel"

class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TableCell(BaseModel):
    row: int = Field(..., description="行索引")
    col: int = Field(..., description="列索引")
    text: str = Field(..., description="单元格文本")
    confidence: float = Field(..., description="识别置信度")

class TableStructure(BaseModel):
    headers: Dict[str, int] = Field(..., description="表头映射")
    merged_cells: List[Dict[str, int]] = Field(default_factory=list, description="合并单元格信息")
    cells: List[TableCell] = Field(..., description="单元格内容")

class OCRTask(BaseModel):
    task_id: str = Field(..., description="任务ID")
    file_url: str = Field(..., description="文件URL")
    file_type: FileType = Field(..., description="文件类型")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    result: Optional[TableStructure] = Field(None, description="识别结果")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)

class OCRRequest(BaseModel):
    file_type: FileType
    file_content: bytes = Field(..., description="文件内容")
    file_name: str = Field(..., description="文件名")

class OCRResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str
    result: Optional[Dict[str, Any]] = None 