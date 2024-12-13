import os
import logging
from alibabacloud_ocr20191230.client import Client
from alibabacloud_tea_openapi import models as open_api_models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sdk_init():
    """测试阿里云OCR SDK初始化"""
    try:
        logger.info("正在初始化OCR客户端...")
        
        # 创建配置
        config = open_api_models.Config(
            access_key_id=os.getenv('ALIYUN_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('ALIYUN_ACCESS_KEY_SECRET'),
            endpoint="ocr.cn-shanghai.aliyuncs.com",
            region_id="cn-shanghai"
        )
        
        # 创建客户端
        client = Client(config)
        logger.info("OCR客户端初始化成功")
        
        # 获取SDK版本信息
        logger.info(f"SDK版本: {client.__module__}")
        
        return True
    except Exception as e:
        logger.error(f"初始化失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_sdk_init()
