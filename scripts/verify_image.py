import sys
from pathlib import Path
import base64
from PIL import Image
import io
import logging

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_image(image_path: str):
    """验证图片格式和属性"""
    try:
        # 打开并分析图片
        with Image.open(image_path) as img:
            logger.info(f"图片路径: {image_path}")
            logger.info(f"图片格式: {img.format}")
            logger.info(f"图片模式: {img.mode}")
            logger.info(f"图片尺寸: {img.size}")
            logger.info(f"图片信息: {img.info}")

            # 转换为RGB（如果需要）
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # 保存为JPEG并获取大小
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95)
            jpeg_data = output.getvalue()
            base64_data = base64.b64encode(jpeg_data).decode('utf-8')

            logger.info(f"转换后JPEG大小: {len(jpeg_data)} bytes")
            logger.info(f"Base64编码长度: {len(base64_data)}")

            # 检查文件大小限制（阿里云OCR API限制）
            max_size = 4 * 1024 * 1024  # 4MB
            if len(jpeg_data) > max_size:
                logger.warning(f"警告：图片大小 ({len(jpeg_data)} bytes) 超过4MB限制")

    except Exception as e:
        logger.error(f"图片验证失败: {str(e)}")
        raise

if __name__ == "__main__":
    test_image = str(Path(project_root) / "tests" / "test_data" / "tables" / "quotations" / "WechatIMG119.jpg")
    verify_image(test_image)
