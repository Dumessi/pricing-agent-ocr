import os
import logging
import json
from alibabacloud_ocr20191230.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr20191230 import models as ocr_models
from alibabacloud_tea_util import models as util_models

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_client():
    """创建OCR客户端"""
    try:
        config = open_api_models.Config(
            access_key_id=os.getenv('ALIYUN_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('ALIYUN_ACCESS_KEY_SECRET'),
            region_id='cn-shanghai',  # 更新区域
            endpoint='ocr.cn-shanghai.aliyuncs.com'  # 更新端点
        )
        logger.debug(f"创建客户端配置: region_id=cn-shanghai, endpoint=ocr.cn-shanghai.aliyuncs.com")
        return Client(config)
    except Exception as e:
        logger.error(f"创建客户端失败: {str(e)}")
        raise

def test_ocr():
    """测试OCR API连接"""
    try:
        # 创建客户端
        client = create_client()
        logger.debug("成功创建OCR客户端")

        # 使用公开可访问的测试图片URL
        test_image_url = "https://raw.githubusercontent.com/aliyun/aliyun-oss-python-sdk/master/examples/data/example.jpg"

        # 创建运行时选项
        runtime = util_models.RuntimeOptions(
            connect_timeout=10000,
            read_timeout=10000,
            autoretry=True,
            max_attempts=3
        )
        logger.debug("设置运行时选项")

        # 创建请求对象
        request = ocr_models.RecognizeTableRequest(
            image_url=test_image_url,
            output_format="json",
            use_finance_model=True,  # 金融票据模型
            assure_direction=True,    # 确保方向
            has_line=True,           # 包含表格线
            skip_detection=False      # 不跳过检测
        )
        logger.debug(f"创建请求对象: {request.to_map()}")

        # 发送请求
        logger.info("正在发送OCR请求...")
        try:
            response = client.recognize_table_with_options(request, runtime)
            logger.debug(f"Raw response: {response}")

            if response and response.body:
                logger.info("OCR请求成功")
                logger.debug(f"响应内容: {json.dumps(response.body.to_map(), ensure_ascii=False, indent=2)}")
                return True
            else:
                logger.error("OCR响应为空")
                return False

        except Exception as api_error:
            logger.error(f"API调用错误: {str(api_error)}")
            if hasattr(api_error, 'code'):
                logger.error(f"错误代码: {api_error.code}")
            if hasattr(api_error, 'message'):
                logger.error(f"错误信息: {api_error.message}")
            if hasattr(api_error, 'request_id'):
                logger.error(f"请求ID: {api_error.request_id}")
            raise

    except Exception as e:
        logger.error(f"OCR请求失败: {str(e)}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误代码: {getattr(e, 'code', 'Unknown')}")
        logger.error(f"错误信息: {getattr(e, 'message', str(e))}")
        return False

if __name__ == '__main__':
    test_ocr()
