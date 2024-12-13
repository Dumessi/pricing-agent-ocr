from alibabacloud_ocr20191230.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr20191230 import models as ocr_models
import os
import base64
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_aliyun_sdk():
    """测试阿里云SDK基本功能"""
    try:
        # 创建配置
        config = open_api_models.Config(
            access_key_id=os.getenv('ALIYUN_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('ALIYUN_ACCESS_KEY_SECRET'),
            endpoint="ocr.cn-hangzhou.aliyuncs.com",  # 使用标准区域端点
            region_id="cn-hangzhou"  # 设置区域ID
        )

        # 创建客户端
        client = Client(config)
        logger.info("已创建OCR客户端")

        # 读取测试图片
        image_path = "/home/ubuntu/pricing-agent-ocr/tests/test_data/tables/quotations/WechatIMG119.jpg"
        with open(image_path, 'rb') as f:
            image_content = f.read()

        # 转换为Base64
        image_base64 = base64.b64encode(image_content).decode('utf-8')

        # 创建请求
        request = ocr_models.RecognizeTableRequest(
            image_url=image_base64,  # 使用正确的参数名
            output_format="json",
            assure_direction=True,
            has_line=True
        )

        logger.info("正在发送OCR请求...")
        response = client.recognize_table(request)
        logger.info(f"OCR响应: {response.body}")

    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    test_aliyun_sdk()
