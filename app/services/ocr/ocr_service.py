from typing import List, Dict, Optional
from app.models.ocr import OCRTask, TaskStatus, TableStructure, TableCell
from app.core.database import Database, COLLECTIONS
from app.utils.excel_parser import ExcelParser
from app.models.ocr import FileType
from app.core.config import settings
import uuid
import asyncio
from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import os

class OCRService:
    def __init__(self):
        self.db = Database.get_db()
        self.collection = self.db[COLLECTIONS["ocr_tasks"]]
        self.excel_parser = ExcelParser()
        # 初始化OCR引擎
        self.ocr = PaddleOCR(
            use_angle_cls=settings.OCR_USE_ANGLE_CLASS,
            lang=settings.OCR_LANGUAGE,
            use_gpu=settings.OCR_USE_GPU
        )

    async def create_task(self, file_paths: List[str], file_types: List[FileType]) -> str:
        """创建OCR任务"""
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        task = OCRTask(
            task_id=task_id,
            file_url=file_paths[0],  # 暂时只处理第一个文件
            file_type=file_types[0],
            status=TaskStatus.PENDING
        )
        
        # 保存到数据库
        await self.collection.insert_one(task.dict())
        
        # 异步处理任务
        asyncio.create_task(self._process_task(task_id))
        
        return task_id

    async def get_task_status(self, task_id: str) -> Optional[OCRTask]:
        """获取任务状态"""
        doc = await self.collection.find_one({"task_id": task_id})
        if doc:
            return OCRTask(**doc)
        return None

    def _process_image_ocr(self, image_path: str) -> TableStructure:
        """处理图片OCR"""
        # 读取图片
        img = Image.open(image_path)
        
        # 执行OCR识别
        result = self.ocr.ocr(image_path, cls=True)
        
        # 提取文本和位置信息
        cells = []
        for idx, line in enumerate(result):
            box = line[0]
            text = line[1][0]
            confidence = float(line[1][1])
            
            # 计算行列位置（根据坐标）
            x = (box[0][0] + box[1][0] + box[2][0] + box[3][0]) / 4
            y = (box[0][1] + box[1][1] + box[2][1] + box[3][1]) / 4
            
            # 简单的行列估算（可以根据实际需求调整）
            row = int(y / 30)  # 假设每行高度约30像素
            col = int(x / 100)  # 假设每列宽度约100像素
            
            cell = TableCell(
                row=row,
                col=col,
                text=text,
                confidence=confidence
            )
            cells.append(cell)
        
        # 构建表格结构
        # 这里简单处理，假设第一行是表头
        headers = {}
        first_row_cells = [c for c in cells if c.row == 0]
        for cell in first_row_cells:
            headers[cell.text] = cell.col
        
        return TableStructure(
            headers=headers,
            cells=cells,
            merged_cells=[]  # 暂不处理合并单元格
        )

    def _process_excel(self, file_path: str) -> TableStructure:
        """处理Excel文件"""
        # 使用ExcelParser解析Excel
        df = self.excel_parser.parse_excel(file_path)
        
        # 转换为TableStructure
        headers = {col: idx for idx, col in enumerate(df.columns)}
        cells = []
        
        for row_idx, row in df.iterrows():
            for col_idx, (col_name, value) in enumerate(row.items()):
                cell = TableCell(
                    row=row_idx,
                    col=col_idx,
                    text=str(value),
                    confidence=1.0  # Excel数据置信度为1
                )
                cells.append(cell)
        
        return TableStructure(
            headers=headers,
            cells=cells,
            merged_cells=[]  # 暂不处理合并单元格
        )

    async def _process_task(self, task_id: str):
        """处理OCR任务"""
        try:
            # 更新任务状态为处理中
            await self.collection.update_one(
                {"task_id": task_id},
                {"$set": {"status": TaskStatus.PROCESSING}}
            )
            
            # 获取任务信息
            task = await self.get_task_status(task_id)
            if not task:
                return
            
            # 根据文件类型处理
            if task.file_type == FileType.EXCEL:
                result = self._process_excel(task.file_url)
            else:
                # 处理图片OCR
                result = self._process_image_ocr(task.file_url)
            
            # 更新任务状态为完成
            await self.collection.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "status": TaskStatus.COMPLETED,
                        "result": result.dict() if result else None
                    }
                }
            )
            
        except Exception as e:
            # 更新任务状态为失败
            await self.collection.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "status": TaskStatus.FAILED,
                        "error_message": str(e)
                    }
                }
            )