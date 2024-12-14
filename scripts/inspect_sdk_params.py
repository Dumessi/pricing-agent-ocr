import inspect
from alibabacloud_ocr20191230 import models as ocr_models
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def inspect_request_class():
    """检查RecognizeTableRequest类的参数"""
    try:
        # 获取类的源代码
        source = inspect.getsource(ocr_models.RecognizeTableRequest)
        logger.info("RecognizeTableRequest类的源代码:")
        logger.info(source)

        # 获取类的初始化参数
        sig = inspect.signature(ocr_models.RecognizeTableRequest.__init__)
        logger.info("\n初始化参数:")
        for param_name, param in sig.parameters.items():
            if param_name != 'self':
                logger.info(f"参数名: {param_name}, 类型: {param.annotation}")

        # 创建一个示例对象并检查其属性
        example = ocr_models.RecognizeTableRequest()
        logger.info("\n可用属性:")
        for attr in dir(example):
            if not attr.startswith('_'):
                logger.info(attr)

    except Exception as e:
        logger.error(f"检查SDK参数时出错: {str(e)}")

if __name__ == '__main__':
    inspect_request_class()
