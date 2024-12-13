import os
import base64
import json
import logging
import time
from typing import Optional, Dict, Any
from alibabacloud_ocr_api20210707.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr_api20210707 import models as ocr_models
from alibabacloud_tea_util import models as util_models
from app.core.config import settings
from app.models.ocr import OCRResult, TableCell, FileType

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

    async def recognize_table(self, image_path: str) -> Optional[OCRResult]:
        """识别表格内容
        
        Args:
            image_path: 图片路径
            
        Returns:
            Optional[OCRResult]: 识别结果
        """
        try:
            logger.info(f"开始处理图片: {image_path}")
            
            # 读取并编码图片
            image_data = self._read_image_file(image_path)
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            logger.info("图片编码完成")
            
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