from typing import List, Dict, Optional, Tuple, Any
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
from app.models.ocr import OCRResult, TableCell, FileType
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

    async def recognize_table(self, image_path: str) -> Optional[OCRResult]:
        """识别表格内容

        Args:
            image_path: 图片路径

        Returns:
            Optional[OCRResult]: 识别结果
        """
        try:
            logger.info(f"开始处理图片: {image_path}")

            # 预处理图片
            processed_image = self.preprocess_image(image_path)
            if processed_image is None:
                raise ValueError("图像预处理失败")

            # 保存预处理后的图片
            temp_path = f"{image_path}_processed.jpg"
            cv2.imwrite(temp_path, processed_image)

            try:
                # 读取并编码预处理后的图片
                with open(temp_path, 'rb') as f:
                    image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                logger.info("预处理图片编码完成")
            finally:
                # 确保临时文件被删除
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            # 创建请求
            req = ocr_models.RecognizeTableOcrRequest(
                image_url=image_base64,
                need_sort=False,
                skip_detection=False
            )
            logger.info("已创建识别请求")

            # 创建运行时选项
            runtime = util_models.RuntimeOptions(
                read_timeout=10000,
                connect_timeout=10000,
                retry_times=3
            )
            logger.info("已创建运行时选项")

            # 发送请求
            try:
                logger.info("正在发送API请求...")
                response = self.client.recognize_table_ocr_with_options(req, runtime)
                logger.info("API请求成功")
                logger.debug(f"API响应: {response.body.data}")
            except Exception as e:
                logger.error(f"API请求失败: {str(e)}")
                return None

            # 解析响应
            if not response or not response.body or not response.body.data:
                logger.error("响应数据为空")
                return None

            try:
                result = json.loads(response.body.data)
            except Exception as e:
                logger.error(f"解析响应数据失败: {str(e)}")
                return None

            # 提取表格数据
            tables = result.get("tables", [])
            if not tables:
                logger.warning("未检测到表格")
                return None

            # 使用第一个表格
            table = tables[0]
            cells = []

            # 解析单元格数据
            try:
                for row_idx, row in enumerate(table.get("cells", [])):
                    for col_idx, cell in enumerate(row):
                        text = cell.get("text", "")
                        confidence = float(cell.get("score", 0.0))
                        row_span = cell.get("row_span", 1)
                        col_span = cell.get("col_span", 1)

                        cells.append(TableCell(
                            text=text,
                            row=row_idx,
                            column=col_idx,
                            row_span=row_span,
                            col_span=col_span,
                            confidence=confidence
                        ))
                logger.info(f"成功解析 {len(cells)} 个单元格")
            except Exception as e:
                logger.error(f"解析单元格数据失败: {str(e)}")
                return None

            # 提取表头信息
            headers = []
            if cells:
                try:
                    header_cells = [cell for cell in cells if cell.row == 0]
                    headers = [cell.text for cell in sorted(header_cells, key=lambda x: x.column)]
                    logger.info(f"成功提取 {len(headers)} 个表头")
                except Exception as e:
                    logger.error(f"提取表头信息失败: {str(e)}")

            logger.info(f"成功解析表格: {len(cells)}个单元格, {len(headers)}个表头")

            return OCRResult(
                cells=cells,
                headers=headers,
                raw_text=result.get("content", ""),
                file_type=FileType.IMAGE
            )

        except Exception as e:
            logger.error(f"OCR识别失败: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None
