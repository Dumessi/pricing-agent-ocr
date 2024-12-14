import asyncio
import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from app.services.ocr.aliyun_ocr_service import AliyunOCRService

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_ocr_response():
    """测试阿里云OCR响应格式"""
    try:
        # 初始化OCR服务
        ocr_service = AliyunOCRService()

        # 获取测试图片路径
        test_image = str(Path(project_root) / "tests" / "test_data" / "tables" / "quotations" / "WechatIMG119.jpg")
        logger.info(f"测试图片路径: {test_image}")

        # 执行OCR识别
        logger.info("开始OCR识别...")
        result = await ocr_service.recognize_table(test_image)

        if result:
            logger.info("OCR识别成功!")
            logger.info(f"表格行数: {result.rows}")
            logger.info(f"表格列数: {result.cols}")
            logger.info(f"单元格数量: {len(result.cells)}")

            # 输出前5个单元格的内容
            logger.info("\n前5个单元格内容:")
            for i, cell in enumerate(result.cells[:5]):
                logger.info(f"单元格 {i+1}: 行={cell.row}, 列={cell.col}, 内容='{cell.text}'")
        else:
            logger.error("OCR识别失败!")

    except Exception as e:
        logger.error(f"测试过程出错: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_ocr_response())
