from enum import Enum
from typing import List, Optional, Dict
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
    col: int  # Changed from column to col to match Aliyun API
    row_span: int = 1
    col_span: int = 1
    confidence: float = 0.0

class TableRecognitionResult(BaseModel):
    """表格识别结果"""
    cells: List[TableCell]
    rows: int
    cols: int

    def get_column(self, header_name: str) -> List[str]:
        """获取指定列的数据"""
        header_cells = [cell for cell in self.cells if cell.row == 0]
        header_cells.sort(key=lambda x: x.col)

        try:
            col_idx = next(i for i, cell in enumerate(header_cells)
                          if header_name in cell.text)
        except StopIteration:
            return []

        column_cells = [cell for cell in self.cells
                       if cell.col == col_idx and cell.row > 0]
        column_cells.sort(key=lambda x: x.row)
        return [cell.text for cell in column_cells]

    def get_rows(self) -> List[Dict[str, str]]:
        """获取所有行数据"""
        if not self.cells:
            return []

        header_cells = [cell for cell in self.cells if cell.row == 0]
        header_cells.sort(key=lambda x: x.col)
        headers = [cell.text for cell in header_cells]

        rows = []
        for row_idx in range(1, self.rows):
            row_cells = [cell for cell in self.cells if cell.row == row_idx]
            row_cells.sort(key=lambda x: x.col)

            row_data = {}
            for header, cell in zip(headers, row_cells):
                row_data[header] = cell.text
            rows.append(row_data)

        return rows

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