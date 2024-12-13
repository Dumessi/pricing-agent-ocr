import pytest
import os
import logging
from pathlib import Path
from app.services.ocr.aliyun_ocr_service import AliyunOCRService
from app.services.matcher.matcher import MaterialMatcher
from app.models.material import MaterialMatch

logger = logging.getLogger(__name__)

@pytest.fixture
def test_images_dir():
    """获取测试图片目录"""
    return Path(__file__).parent / "test_data" / "tables" / "quotations"

@pytest.fixture
def ocr_service():
    """创建OCR服务实例"""
    return AliyunOCRService()

@pytest.fixture
def material_matcher():
    """创建物料匹配器实例"""
    return MaterialMatcher()

@pytest.mark.asyncio
async def test_table_recognition(test_images_dir, ocr_service):
    """测试表格识别功能"""
    # 获取测试图片列表
    image_files = list(test_images_dir.glob("*.jpg"))
    assert len(image_files) > 0, "未找到测试图片"

    # 测试第一张图片的表格识别
    test_image = str(image_files[0])
    logger.info(f"正在测试图片: {test_image}")

    # 执行OCR识别
    result = await ocr_service.recognize_table(test_image)
    logger.info(f"OCR识别结果: {result}")

    assert result is not None, "OCR识别失败"
    assert len(result.cells) > 0, "未识别到表格单元格"

    # 验证表格结构
    assert result.rows > 0, "未识别到表格行"
    assert result.cols > 0, "未识别到表格列"

@pytest.mark.asyncio
async def test_material_matching(test_images_dir, ocr_service, material_matcher):
    """测试物料匹配功能"""
    # 获取测试图片
    image_files = list(test_images_dir.glob("*.jpg"))
    test_image = str(image_files[0])

    # 执行OCR识别
    result = await ocr_service.recognize_table(test_image)
    assert result is not None, "OCR识别失败"

    # 获取物料名称列
    material_names = result.get_column("名称")
    assert len(material_names) > 0, "未识别到物料名称"

    # 测试物料匹配
    for name in material_names[:3]:  # 测试前3个物料
        match_result = await material_matcher.match_material(name)
        assert isinstance(match_result, MaterialMatch)
        assert match_result.original_text == name
        assert match_result.confidence > 0.5, f"物料 '{name}' 匹配置信度过低"

@pytest.mark.asyncio
async def test_full_quotation_processing(test_images_dir, ocr_service, material_matcher):
    """测试完整报价单处理流程"""
    image_files = list(test_images_dir.glob("*.jpg"))

    for image_file in image_files[:2]:  # 测试前两张图片
        # OCR识别
        result = await ocr_service.recognize_table(str(image_file))
        assert result is not None, f"图片 {image_file.name} OCR识别失败"

        # 获取表格数据
        rows = result.get_rows()
        assert len(rows) > 0, f"图片 {image_file.name} 未识别到表格数据"

        # 物料匹配测试
        for row in rows[:3]:  # 测试每张图片的前3行
            if "名称" in row and row["名称"]:
                match_result = await material_matcher.match_material(row["名称"])
                assert match_result is not None, f"物料 '{row['名称']}' 匹配失败"
                assert match_result.confidence > 0.5, f"物料 '{row['名称']}' 匹配置信度过低"
