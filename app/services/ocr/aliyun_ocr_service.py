import base64
import logging
from typing import Optional, Union, List, Dict, Any

from alibabacloud_ocr20191230 import models as ocr_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr20191230.client import Client
from alibabacloud_tea_util import models as util_models

from app.core.config import settings
from app.models.ocr import TableRecognitionResult, TableCell, OCRResult, FileType

logger = logging.getLogger(__name__)

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
                endpoint="ocr.cn-hangzhou.aliyuncs.com",  # 使用标准区域端点
                region_id="cn-hangzhou"  # 设置区域ID
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

    def preprocess_image(self, image_data: bytes) -> bytes:
        """预处理图片

        Args:
            image_data: 原始图片数据

        Returns:
            bytes: 处理后的图片数据
        """
        try:
            import io
            from PIL import Image

            # 将二进制数据转换为PIL Image对象
            image = Image.open(io.BytesIO(image_data))

            # 转换为RGB模式（如果是RGBA，去除alpha通道）
            if image.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # 调整图片大小（如果太大）
            max_size = 4096  # 阿里云OCR API的最大支持尺寸
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # 确保图片质量（DPI）
            dpi = image.info.get('dpi', (300, 300))
            if isinstance(dpi, tuple) and (dpi[0] < 300 or dpi[1] < 300):
                # 如果DPI太低，进行重采样
                new_size = tuple(int(dim * 300 / min(dpi)) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # 保存为JPEG格式（阿里云OCR推荐格式）
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95, dpi=(300, 300))
            processed_data = output.getvalue()

            logger.info("图片预处理完成")
            return processed_data

        except Exception as e:
            logger.error(f"图片预处理失败: {str(e)}")
            raise







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

    async def recognize_table(self, image_path: str) -> Optional[OCRResult]:
        """识别表格内容

        Args:
            image_path: 图片路径

        Returns:
            OCRResult: OCR识别结果
        """
        try:
            # 读取并预处理图片
            logger.info(f"从文件读取图片: {image_path}")
            image_bytes = self._read_image_file(image_path)
            if not image_bytes:
                logger.error("读取图片失败")
                return None

            # 预处理图片
            processed_image = self.preprocess_image(image_bytes)
            logger.info("图片预处理完成")

            # 转换为Base64
            image_base64 = base64.b64encode(processed_image).decode('utf-8')
            logger.info("图片已转换为Base64格式")
            logger.debug(f"Base64长度: {len(image_base64)}")

            # 创建请求对象
            request = ocr_models.RecognizeTableRequest(
                image_url=image_base64,  # 使用正确的参数名
                output_format="json",
                assure_direction=True,
                has_line=True,
                skip_detection=False,
                use_finance_model=False
            )
            logger.info("已创建OCR请求")
            logger.debug(f"请求参数: {request.to_map()}")

            # 创建运行时选项
            runtime = util_models.RuntimeOptions()

            # 发送请求
            logger.info("正在发送OCR请求...")
            response = await self.client.recognize_table_with_options_async(request, runtime)

            if not response or not response.body:
                logger.error("OCR响应为空")
                return None

            logger.info("OCR请求成功")
            logger.debug(f"OCR响应: {response.body}")

            # 解析响应
            data = response.body
            if not isinstance(data, dict):
                logger.error(f"OCR响应格式错误: {type(data)}")
                return None

            # 提取表格数据
            tables_result = data.get('Data', {}).get('TableArray', [])
            if not tables_result:
                logger.warning("未检测到表格")
                return None

            # 处理识别结果
            result = OCRResult(
                raw_text="",  # 原始文本将从表格内容中提取
                tables=[],    # 表格数据将在下面处理
                confidence=float(data.get('Data', {}).get('Confidence', 0))
            )

            # 处理每个表格
            for table in tables_result:
                table_data = []
                for row in table.get('TableRows', []):
                    row_data = []
                    for cell in row.get('TableCells', []):
                        cell_text = cell.get('Text', '').strip()
                        row_data.append(cell_text)
                    if row_data:
                        table_data.append(row_data)
                if table_data:
                    result.tables.append(table_data)

            # 如果没有提取到任何表格数据，返回None
            if not result.tables:
                logger.warning("未能提取到有效的表格数据")
                return None

            return result

        except Exception as e:
            logger.error(f"OCR请求失败: {str(e)}")
            logger.error(f"错误代码: {getattr(e, 'code', 'Unknown')}")
            logger.error(f"错误信息: {getattr(e, 'message', str(e))}")
            return None
