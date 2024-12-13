from typing import List, Dict, Optional, Tuple
from app.models.ocr import OCRTask, TaskStatus, TableStructure, TableCell, FileType
from app.core.database import Database, COLLECTIONS
from app.utils.excel_parser import ExcelParser
from app.core.config import settings
import uuid
import asyncio
from paddleocr import PaddleOCR
import numpy as np
from PIL import Image
import cv2
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
            use_gpu=settings.OCR_USE_GPU,
            det_algorithm=settings.OCR_DET_ALGORITHM,
            rec_algorithm=settings.OCR_REC_ALGORITHM,
            enable_mkldnn=False,  # 暂时禁用MKLDNN
            limit_side_len=settings.OCR_LIMIT_SIDE_LEN,
            det_limit_side_len=settings.OCR_DET_LIMIT_SIDE_LEN,
            det_db_thresh=0.2,  # 降低检测阈值，提高召回率
            det_db_box_thresh=0.3,  # 降低框选阈值
            det_db_unclip_ratio=2.0,  # 增加文本区域扩张比例
            rec_batch_num=settings.OCR_REC_BATCH_NUM,
            rec_char_dict_path=None,  # 使用默认字典
            cls_batch_num=1,  # 减少批处理大小，提高准确率
            cls_thresh=0.8,  # 提高方向分类阈值
            drop_score=0.3,  # 降低文本置信度阈值
            use_space_char=True,  # 启用空格字符识别
            use_dilation=True,  # 启用膨胀操作
            det_db_score_mode="slow",  # 使用更精确的评分模式
            table=settings.OCR_ENABLE_TABLE,
            table_max_len=settings.OCR_TABLE_MAX_LEN,
            show_log=True
        )

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        try:
            # 调整图像大小
            height, width = image.shape[:2]
            if width > 2000:
                scale = 2000 / width
                new_width = 2000
                new_height = int(height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # 转换为灰度图
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 去噪处理
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            # 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            equalized = clahe.apply(denoised)
            
            # 对比度增强
            alpha = 1.3  # 对比度增强因子
            beta = 15    # 亮度增强因子
            enhanced = cv2.convertScaleAbs(equalized, alpha=alpha, beta=beta)
            
            # 自适应二值化
            binary = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 形态学操作
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
            
            # 倾斜校正
            coords = np.column_stack(np.where(morph > 0))
            if len(coords) > 100:  # 确保有足够的点进行校正
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = 90 + angle
                
                # 如果倾斜角度大于0.5度才进行校正
                if abs(angle) > 0.5:
                    (h, w) = morph.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    rotated = cv2.warpAffine(
                        morph, M, (w, h),
                        flags=cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE
                    )
                else:
                    rotated = morph
            else:
                rotated = morph
            
            # 边缘增强
            kernel_sharpen = np.array([
                [-1,-1,-1],
                [-1, 9,-1],
                [-1,-1,-1]
            ])
            sharpened = cv2.filter2D(rotated, -1, kernel_sharpen)
            
            # 最终的降噪处理
            final = cv2.medianBlur(sharpened, 3)
            
            return final
            
        except Exception as e:
            print(f"Warning: Image preprocessing failed: {str(e)}")
            return image  # 如果处理失败，返回原图

    def detect_table_structure(self, image: np.ndarray) -> Tuple[List[List[int]], List[List[int]]]:
        """检测表格结构"""
        try:
            # 边缘检测
            edges = cv2.Canny(image, 30, 150, apertureSize=3)
            
            # 膨胀操作，连接断开的线条
            kernel = np.ones((2,2), np.uint8)
            dilated = cv2.dilate(edges, kernel, iterations=1)
            
            # 使用概率霍夫变换检测直线
            min_line_length = image.shape[1] * 0.1  # 最小线长为图像宽度的10%
            max_line_gap = image.shape[1] * 0.05    # 最大间隙为图像宽度的5%
            
            lines = cv2.HoughLinesP(
                dilated,
                rho=1,
                theta=np.pi/180,
                threshold=30,
                minLineLength=min_line_length,
                maxLineGap=max_line_gap
            )
            
            if lines is None:
                return [], []
            
            # 分离水平和垂直线
            h_lines = []
            v_lines = []
            
            height, width = image.shape[:2]
            min_length = min(height, width) * 0.05  # 最小有效线长
            
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                
                if length < min_length:
                    continue
                    
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi)
                
                # 水平线（角度误差在5度以内）
                if angle < 5 or angle > 175:
                    # 延��线条到图像边界
                    if abs(y2 - y1) < height * 0.02:  # 确保是水平线
                        y_avg = (y1 + y2) // 2
                        h_lines.append([0, y_avg, width, y_avg])
                
                # 垂直线（角度误差在5度以内）
                elif 85 < angle < 95:
                    # 延长线条到图像边界
                    if abs(x2 - x1) < width * 0.02:  # 确保是垂直线
                        x_avg = (x1 + x2) // 2
                        v_lines.append([x_avg, 0, x_avg, height])
            
            # 合并相近的线条
            h_lines = self._merge_nearby_lines(h_lines, True, threshold=height*0.01)
            v_lines = self._merge_nearby_lines(v_lines, False, threshold=width*0.01)
            
            # 移除重复的线条
            h_lines = self._remove_duplicate_lines(h_lines, True)
            v_lines = self._remove_duplicate_lines(v_lines, False)
            
            # 确保线条覆盖整个表格区域
            if h_lines and v_lines:
                # 添加边界线
                h_lines.insert(0, [0, 0, width, 0])  # 顶部边界
                h_lines.append([0, height-1, width, height-1])  # 底部边界
                v_lines.insert(0, [0, 0, 0, height])  # 左侧边界
                v_lines.append([width-1, 0, width-1, height])  # 右侧边界
            
            return h_lines, v_lines
            
        except Exception as e:
            print(f"Warning: Table structure detection failed: {str(e)}")
            return [], []
    
    def _merge_nearby_lines(self, lines: List[List[int]], is_horizontal: bool, 
                          threshold: int = 10) -> List[List[int]]:
        """合并相近的线条"""
        if not lines:
            return []
            
        # 按y坐标（水平线）或x坐标（垂直线）排序
        idx = 1 if is_horizontal else 0
        sorted_lines = sorted(lines, key=lambda x: x[idx])
        
        merged_lines = []
        current_line = sorted_lines[0]
        
        for line in sorted_lines[1:]:
            if is_horizontal:
                if abs(line[1] - current_line[1]) < threshold:
                    # 更新当前线的终点
                    current_line[2] = max(current_line[2], line[2])
                else:
                    merged_lines.append(current_line)
                    current_line = line
            else:
                if abs(line[0] - current_line[0]) < threshold:
                    # 更新当前线的终点
                    current_line[3] = max(current_line[3], line[3])
                else:
                    merged_lines.append(current_line)
                    current_line = line
        
        merged_lines.append(current_line)
        return merged_lines

    def _remove_duplicate_lines(self, lines: List[List[int]], is_horizontal: bool, 
                              threshold: float = 0.02) -> List[List[int]]:
        """移除重复的线条"""
        if not lines:
            return []
        
        # 转换阈值为像素值
        if is_horizontal:
            threshold = int(lines[0][3] * threshold)  # 使用高度计算阈值
        else:
            threshold = int(lines[0][2] * threshold)  # 使用宽度计算阈值
        
        # 按位置排序
        idx = 1 if is_horizontal else 0
        sorted_lines = sorted(lines, key=lambda x: x[idx])
        
        # 移除重复线条
        result = [sorted_lines[0]]
        for line in sorted_lines[1:]:
            prev_line = result[-1]
            if is_horizontal:
                if abs(line[1] - prev_line[1]) > threshold:
                    result.append(line)
            else:
                if abs(line[0] - prev_line[0]) > threshold:
                    result.append(line)
        
        return result

    def analyze_table_cells(self, h_lines: List[List[int]], v_lines: List[List[int]], 
                          image_height: int, image_width: int) -> Tuple[List[int], List[int]]:
        """分析表格单元格"""
        try:
            # 提取行和列的位置
            rows = sorted(set(line[1] for line in h_lines))
            cols = sorted(set(line[0] for line in v_lines))
            
            # 处理空行和空列
            if not rows:
                rows = [0, image_height]
            else:
                if rows[0] > settings.TABLE_MIN_ROW_HEIGHT:
                    rows.insert(0, 0)
                if rows[-1] < image_height - settings.TABLE_MIN_ROW_HEIGHT:
                    rows.append(image_height)
            
            if not cols:
                cols = [0, image_width]
            else:
                if cols[0] > settings.TABLE_MIN_COL_WIDTH:
                    cols.insert(0, 0)
                if cols[-1] < image_width - settings.TABLE_MIN_COL_WIDTH:
                    cols.append(image_width)
            
            return rows, cols
            
        except Exception as e:
            print(f"Warning: Table cell analysis failed: {str(e)}")
            return [0, image_height], [0, image_width]
    
    def _detect_merged_cells(self, h_lines: List[List[int]], v_lines: List[List[int]], 
                           rows: List[int], cols: List[int]) -> List[List[int]]:
        """检测合并单元格"""
        merged_cells = []
        
        # 检查每个可能的单元格区域
        for i in range(len(rows) - 1):
            for j in range(len(cols) - 1):
                # 检查是否有分隔线
                has_h_line = any(
                    abs(line[1] - rows[i]) < 5 for line in h_lines
                )
                has_v_line = any(
                    abs(line[0] - cols[j]) < 5 for line in v_lines
                )
                
                if not has_h_line or not has_v_line:
                    # 可能是合并单元格的一部分
                    merged_cells.append([i, j])
        
        # 合并相邻的合并单元格
        result = []
        for cell in merged_cells:
            merged = False
            for existing in result:
                if (abs(cell[0] - existing[0]) <= 1 and 
                    abs(cell[1] - existing[1]) <= 1):
                    # 扩展现有的合并单元格
                    existing[0] = min(existing[0], cell[0])
                    existing[1] = min(existing[1], cell[1])
                    merged = True
                    break
            if not merged:
                result.append(cell)
        
        return result

    def _normalize_text(self, text: str) -> str:
        """清理和规范化文本"""
        if not text:
            return ""
            
        # 移除多余的空白字符
        text = " ".join(text.split())
        
        # 统一全角字符到半角
        text = self._full_to_half(text)
        
        # 规范化DN规格写法
        text = self._normalize_dn_spec(text)
        
        # 规范化单位
        text = self._normalize_units(text)
        
        # 规范化数字
        text = self._normalize_numbers(text)
        
        # 移除特殊字符
        text = text.strip(".,;:!?()[]{}\"'")
        
        return text.strip()
    
    def _normalize_dn_spec(self, text: str) -> str:
        """规范化DN规格写法"""
        import re
        
        # DN规格的正则表达式
        dn_pattern = r'[Dd][Nn]?\s*(\d+)(?:\s*[×xX*]\s*(\d+))*'
        
        def replace_dn(match):
            parts = [p for p in match.groups() if p]
            return 'DN' + '*'.join(parts)
        
        return re.sub(dn_pattern, replace_dn, text)
    
    def _normalize_units(self, text: str) -> str:
        """规范化单位"""
        # 单位映射表
        unit_map = {
            '个': '个',
            'pcs': '个',
            'PCS': '个',
            '件': '个',
            '套': '套',
            'SET': '套',
            'set': '套',
            '米': 'm',
            'M': 'm',
            '米': 'm',
            '条': '条'
        }
        
        for old, new in unit_map.items():
            text = text.replace(old, new)
        
        return text
    
    def _normalize_numbers(self, text: str) -> str:
        """规范化数字"""
        import re
        
        # 中文数字映射
        cn_num = {
            '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
            '零': '0'
        }
        
        # 替换中文数字
        for cn, ar in cn_num.items():
            text = text.replace(cn, ar)
        
        # 规范化小数点
        text = text.replace('。', '.')
        
        # 处理数字间的特殊字符
        number_pattern = r'(\d+)[,，](\d{3})'
        while re.search(number_pattern, text):
            text = re.sub(number_pattern, r'\1\2', text)
        
        return text
    
    def _full_to_half(self, text: str) -> str:
        """将全角字符转换为半角字符"""
        result = ""
        for char in text:
            code = ord(char)
            if 0xFF01 <= code <= 0xFF5E:
                # 全角字符范围
                result += chr(code - 0xFEE0)
            elif code == 0x3000:
                # 全角空格
                result += " "
            else:
                result += char
        return result
    
    def _calculate_overlap(self, box1: List[float], box2: List[float]) -> float:
        """计算两个边界框的重叠面积"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        if x1 < x2 and y1 < y2:
            return (x2 - x1) * (y2 - y1)
        return 0

    def _process_image_ocr(self, image_path: str) -> TableStructure:
        """处理图片OCR"""
        try:
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Failed to load image")
            
            # 图像预处理
            processed_image = self.preprocess_image(image)
            
            # 多次尝试不同的预处理方法
            results = []
            
            # 原始图像识别
            result1 = self.ocr.ocr(image, cls=True)
            if result1:
                results.extend(result1[0] if isinstance(result1[0], list) else result1)
            
            # 预处理后的图像识别
            result2 = self.ocr.ocr(processed_image, cls=True)
            if result2:
                results.extend(result2[0] if isinstance(result2[0], list) else result2)
            
            # 二值化图像识别
            _, binary = cv2.threshold(
                cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
                0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            result3 = self.ocr.ocr(binary, cls=True)
            if result3:
                results.extend(result3[0] if isinstance(result3[0], list) else result3)
            
            if not results:
                raise ValueError("OCR failed to process image")
            
            # 合并结果并去重
            unique_results = []
            seen_texts = set()
            
            for item in results:
                if not isinstance(item, list) or len(item) != 2:
                    continue
                    
                box = item[0]
                text, confidence = item[1]
                
                # 清理文本
                text = self._normalize_text(text)
                if not text or text in seen_texts:
                    continue
                
                seen_texts.add(text)
                unique_results.append([box, [text, confidence]])
            
            # 检测表格结构
            h_lines, v_lines = self.detect_table_structure(processed_image)
            rows, cols = self.analyze_table_cells(
                h_lines, v_lines, 
                image.shape[0], image.shape[1]
            )
            
            # 提取单元格内容
            cells = self.extract_cell_content(
                processed_image, 
                [rows, cols], 
                unique_results
            )
            
            # 构建表格结构
            # 假设第一行是表头
            headers = {}
            first_row_cells = [c for c in cells if c.row < settings.TABLE_HEADER_ROWS]
            for cell in first_row_cells:
                headers[cell.text] = cell.col
            
            return TableStructure(
                headers=headers,
                cells=cells,
                merged_cells=[]  # TODO: 实现合并单元格检测
            )
        except Exception as e:
            raise Exception(f"Failed to process image: {str(e)}")

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
            merged_cells=[]  # TODO: 处理Excel合并单元格
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

    def extract_cell_content(self, image: np.ndarray, cells: List[List[int]], 
                           ocr_result: List) -> List[TableCell]:
        """提取单元格内容"""
        table_cells = []
        cells_content = {}  # 用于存储每个单元格的所有文本
        
        # 将OCR结果按位置分配到单元格
        for line in ocr_result:
            if not isinstance(line, list) or len(line) != 2:
                continue
                
            try:
                box = line[0]
                text, confidence = line[1]
                
                # 清理和规范化文本
                text = self._normalize_text(text)
                if not text:
                    continue
                
                # 计算文本框的边界框
                x_coords = [p[0] for p in box]
                y_coords = [p[1] for p in box]
                min_x, max_x = min(x_coords), max(x_coords)
                min_y, max_y = min(y_coords), max(y_coords)
                center_x = (min_x + max_x) / 2
                center_y = (min_y + max_y) / 2
                
                # 确定所属单元格
                row = col = -1
                max_overlap = 0
                
                for i in range(len(cells[0]) - 1):
                    for j in range(len(cells[1]) - 1):
                        cell_x1, cell_y1 = cells[1][j], cells[0][i]
                        cell_x2, cell_y2 = cells[1][j+1], cells[0][i+1]
                        
                        # 计算重叠面积
                        overlap = self._calculate_overlap(
                            [min_x, min_y, max_x, max_y],
                            [cell_x1, cell_y1, cell_x2, cell_y2]
                        )
                        
                        if overlap > max_overlap:
                            max_overlap = overlap
                            row, col = i, j
                
                if row != -1 and col != -1:
                    cell_key = (row, col)
                    if cell_key not in cells_content:
                        cells_content[cell_key] = []
                    cells_content[cell_key].append((text, confidence, center_y))
                    
            except Exception as e:
                print(f"Warning: Failed to process OCR result: {str(e)}")
                continue
        
        # 处理每个单元格的内容
        for (row, col), contents in cells_content.items():
            # 按y坐标排序内容
            contents.sort(key=lambda x: x[2])
            
            # 合并文本，处理可能的多行内容
            texts = []
            total_confidence = 0
            prev_y = None
            
            for text, conf, y in contents:
                if prev_y is not None and abs(y - prev_y) > 20:
                    # 如果y坐标差距较大，添加换行符
                    texts.append('\n')
                texts.append(text)
                total_confidence += conf
                prev_y = y
            
            merged_text = " ".join(texts)
            avg_confidence = total_confidence / len(contents)
            
            # 后处理规则
            if row == 0:  # 表头行
                merged_text = merged_text.upper()  # 表头转大写
            
            cell = TableCell(
                row=row,
                col=col,
                text=merged_text,
                confidence=float(avg_confidence)
            )
            table_cells.append(cell)
        
        return table_cells