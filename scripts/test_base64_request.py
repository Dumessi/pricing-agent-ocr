import sys
import os
import logging
import json
from alibabacloud_ocr20191230.client import Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ocr20191230 import models as ocr_models
from alibabacloud_tea_util import models as util_models
from serve_test_images import start_server, get_image_url

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_client():
    """创建OCR客户端"""
    try:
        config = open_api_models.Config(
            access_key_id=os.getenv('ALIYUN_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('ALIYUN_ACCESS_KEY_SECRET')
        )
        logger.debug("创建客户端配置")
        return Client(config)
    except Exception as e:
        logger.error(f"创建客户端失败: {str(e)}")
        raise

def test_single_image():
    """测试单个图片的OCR识别"""
    # 启动本地HTTP服务器
    server, thread = start_server()
    logger.info("启动本地HTTP服务器")

    try:
        # 获取测试图片URL
        image_name = 'WechatIMG119.jpg'
        image_url = get_image_url(image_name)
        logger.debug(f"获取到图片URL: {image_url}")

        # 创建客户端
        client = create_client()
        logger.debug("成功创建OCR客户端")

        # 创建运行时选项
        runtime = util_models.RuntimeOptions(
            connect_timeout=10000,
            read_timeout=10000,
            autoretry=True,
            max_attempts=3,
            ignore_ssl=True,
            http_proxy=os.getenv('HTTP_PROXY', ''),
            https_proxy=os.getenv('HTTPS_PROXY', '')
        )
        logger.debug("设置运行时选项")

        # 创建请求对象
        request = ocr_models.RecognizeTableRequest(
            url=image_url,
            output_format="json"
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
    finally:
        # 关闭服务器
        server.shutdown()
        server.server_close()
        logger.info("关闭本地HTTP服务器")

if __name__ == '__main__':
    test_single_image()
