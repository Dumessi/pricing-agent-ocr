from alibabacloud_ocr20191230.client import Client
from alibabacloud_tea_openapi import models as open_api_models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_sdk_config():
    """验证SDK配置"""
    try:
        # 测试不同的端点配置
        endpoints = [
            "ocr-api.aliyuncs.com",
            "ocr.aliyuncs.com",
            "ocr-api.cn-hangzhou.aliyuncs.com",
            "ocr.cn-hangzhou.aliyuncs.com"
        ]

        for endpoint in endpoints:
            try:
                config = open_api_models.Config(
                    access_key_id="test",
                    access_key_secret="test",
                    region_id="cn-hangzhou",
                    endpoint=endpoint
                )
                client = Client(config)
                logger.info(f"成功创建客户端配置 - 端点: {endpoint}")
                logger.info(f"客户端配置: {config.to_map()}")
            except Exception as e:
                logger.error(f"端点 {endpoint} 配置失败: {str(e)}")

    except Exception as e:
        logger.error(f"验证SDK配置失败: {str(e)}")

if __name__ == "__main__":
    verify_sdk_config()
