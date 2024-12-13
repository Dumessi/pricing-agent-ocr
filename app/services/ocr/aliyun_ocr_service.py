from typing import List, Dict, Optional, Tuple, Any, Union
import base64
import os
import json
import logging
import numpy as np
import cv2
from alibabacloud_ocr_api20210707.client import Client
from alibabacloud_ocr_api20210707 import models as ocr_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from app.models.ocr import OCRResult, TableCell, FileType, TableRecognitionResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AliyunOCRService:
    def __init__(self):
        """初始化阿里云OCR客户端"""
        try:
            logger.info("正在初始化阿里云OCR服务...")
            logger.info(f"Access Key ID: {settings.ALIYUN_ACCESS_KEY_ID}")
            logger.info(f"Access Key Secret: {'*' * len(settings.ALIYUN_ACCESS_KEY_SECRET)}")

            # 创建配置
            config = open_api_models.Config(
                access_key_id=settings.ALIYUN_ACCESS_KEY_ID,
                access_key_secret=settings.ALIYUN_ACCESS_KEY_SECRET,
                endpoint="ocr-api.cn-shanghai.aliyuncs.com"
            )
            logger.info("已创建SDK配置")

            # 创建客户端
            self.client = Client(config)
            logger.info("已创建OCR客户端")

        except Exception as e:
            logger.error(f"初始化OCR服务失败: {str(e)}")
            raise

    def _read_image_file(self, image_path: str) -> bytes:
        """读取图片文件

        Args:
            image_path: 图片路径

        Returns:
            bytes: 图片二进制数据
        """
        try:
            with open(image_path, 'rb') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取图片文件失败: {str(e)}")
            raise

    def preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """图像预处理

        Args:
            image_path: 图片路径

        Returns:
            Optional[np.ndarray]: 预处理后的图像数组，失败则返回None
        """
        try:
            # 读取图片
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("Failed to load image")

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
            logger.error(f"图像预处理失败: {str(e)}")
            return None







    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""

        text = " ".join(text.split())
        text = self._full_to_half(text)
        text = self._normalize_dn_spec(text)
        text = self._normalize_units(text)
        text = self._normalize_numbers(text)
        text = text.strip(".,;:!?()[]{}\"'")

        return text.strip()

    def _normalize_dn_spec(self, text: str) -> str:
        import re

        dn_pattern = r'[Dd][Nn]?\s*(\d+)(?:\s*[×xX*]\s*(\d+))*'

        def replace_dn(match):
            parts = [p for p in match.groups() if p]
            return 'DN' + '*'.join(parts)

        return re.sub(dn_pattern, replace_dn, text)

    def _normalize_units(self, text: str) -> str:
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
        import re

        cn_num = {
            '一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
            '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
            '零': '0'
        }

        for cn, ar in cn_num.items():
            text = text.replace(cn, ar)

        text = text.replace('。', '.')

        number_pattern = r'(\d+)[,，](\d{3})'
        while re.search(number_pattern, text):
            text = re.sub(number_pattern, r'\1\2', text)

        return text

    def _full_to_half(self, text: str) -> str:
        result = ""
        for char in text:
            code = ord(char)
            if 0xFF01 <= code <= 0xFF5E:
                result += chr(code - 0xFEE0)
            elif code == 0x3000:
                result += " "
            else:
                result += char
        return result

    async def process_image(self, task) -> Optional[OCRResult]:
        """处理图片文件

        Args:
            task: OCR任务

        Returns:
            Optional[OCRResult]: OCR结果
        """
        try:
            logger.info(f"开始处理图片任务: {task.task_id}")
            return await self.recognize_table(task.file_path)
        except Exception as e:
            logger.error(f"处理图片任务失败: {str(e)}")
            return None

    async def process_excel(self, task) -> Optional[OCRResult]:
        """处理Excel文件

        Args:
            task: OCR任务

        Returns:
            Optional[OCRResult]: OCR结果
        """
        try:
            import pandas as pd
            logger.info(f"开始处理Excel任务: {task.task_id}")

            # 读取Excel文件
            df = pd.read_excel(task.file_path)

            # 转换为表格单元格
            cells = []
            for row_idx, row in df.iterrows():
                for col_idx, value in enumerate(row):
                    if pd.notna(value):  # 跳过空值
                        cells.append(TableCell(
                            text=str(value),
                            row=row_idx,
                            column=col_idx,
                            row_span=1,
                            col_span=1,
                            confidence=1.0  # Excel数据可信度为1
                        ))

            # 获取表头
            headers = df.columns.tolist()

            return OCRResult(
                cells=cells,
                headers=headers,
                raw_text="",  # Excel文件不需要原始文本
                file_type=FileType.EXCEL
            )
        except Exception as e:
            logger.error(f"处理Excel任务失败: {str(e)}")
            return None

    async def recognize_table(self, image_input: Union[str, bytes]) -> Optional[TableRecognitionResult]:
        """识别表格

        Args:
            image_input: 图片路径或二进制数据

        Returns:
            Optional[TableRecognitionResult]: 表格识别结果
        """
        try:
            # 处理输入
            if isinstance(image_input, str):
                image_data = self._read_image_file(image_input)
                logger.info(f"从文件读取图片: {image_input}")
            else:
                image_data = image_input
                logger.info("使用提供的图片二进制数据")

            # Base64编码
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            logger.info("图片已转换为Base64格式")

            # 创建请求
            request = ocr_models.RecognizeTableOcrRequest(
                image_url='',
                image_base64=image_base64
            )
            runtime = util_models.RuntimeOptions()
            logger.info("已创建OCR请求")

            # 发送请求
            logger.info("正在发送OCR请求...")
            response = self.client.recognize_table_ocr_with_options(request, runtime)
            logger.info("已收到OCR响应")
            logger.debug(f"OCR响应内容: {response.body}")

            # 处理响应
            if response.body and hasattr(response.body, 'data'):
                data = response.body.data
                if hasattr(data, 'tables') and data.tables:
                    tables = data.tables
                    if not tables:
                        logger.warning("未在图片中找到表格")
                        return None

                    # 处理第一个表格
                    table = tables[0]
                    result = TableRecognitionResult(
                        cells=[
                            TableCell(
                                text=cell.content,
                                row=cell.row_idx,
                                col=cell.col_idx,
                                row_span=cell.row_span,
                                col_span=cell.col_span
                            ) for cell in table.cells
                        ],
                        rows=table.rows,
                        cols=table.cols
                    )
                    logger.info(f"成功识别表格，包含 {len(result.cells)} 个单元格")
                    return result
                else:
                    logger.warning("响应中没有表格数据")
                    return None
            else:
                logger.warning("无效的OCR响应")
                return None

        except Exception as e:
            logger.error(f"表格识别失败: {str(e)}")
            return None
