import asyncio
import json
import os
from uuid import uuid4
import pytest
from app.services.ocr.aliyun_ocr_service import AliyunOCRService
from app.services.matcher.matcher import MaterialMatcher
from app.models.ocr import FileType, OCRTask, TaskStatus
from app.core.database import Database, COLLECTIONS
from app.core.config import settings

@pytest.fixture(autouse=True)
async def setup_test_data(database):
    """设置测试数据"""
    try:
        # 导入测试数据
        with open('tests/test_data/materials.json', 'r', encoding='utf-8') as f:
            materials = json.load(f)
            await database[COLLECTIONS["materials"]].insert_many(materials)

        # 生成测试Excel文件
        os.system('python tests/test_data/test_order.py')
    except Exception as e:
        pytest.fail(f"测试数据设置失败: {str(e)}")

@pytest.mark.asyncio
async def test_excel_processing():
    """测试Excel处理"""
    try:
        # 创建OCR服务
        ocr_service = AliyunOCRService()

        # 创建任务
        file_path = os.path.join(os.path.dirname(__file__), 'test_data/test_order.xlsx')
        task = OCRTask(
            task_id=str(uuid4()),
            file_path=file_path,
            file_type=FileType.EXCEL,
            status=TaskStatus.PENDING
        )

        # 处理Excel文件
        result = await ocr_service.process_excel(task)
        assert result is not None, "OCR结果不能为空"
        assert len(result.cells) > 0, "OCR结果应包含单元格数据"

        # 验证识别结果
        found_material = False
        for cell in result.cells:
            if cell.text == "卡箍":
                found_material = True
                break
        assert found_material, "未能识别到预期的物料名称"
    except Exception as e:
        pytest.fail(f"Excel处理测试失败: {str(e)}")

@pytest.mark.asyncio
async def test_table_image_processing():
    """测试表格图片处理"""
    try:
        ocr_service = AliyunOCRService()

        # 测试标准表格图片
        file_path = os.path.join(os.path.dirname(__file__), 'test_data/tables/standard/table1.png')
        assert os.path.exists(file_path), f"测试图片不存在: {file_path}"

        task = OCRTask(
            task_id=str(uuid4()),
            file_path=file_path,
            file_type=FileType.IMAGE,
            status=TaskStatus.PENDING
        )

        result = await ocr_service.process_image(task)
        assert result is not None, "OCR结果不能为空"
        assert result.table_structure is not None, "表格结构不能为空"
        assert len(result.table_structure.cells) > 0, "表格应包含单元格数据"
    except Exception as e:
        pytest.fail(f"表格图片处理测试失败: {str(e)}")

@pytest.mark.asyncio
async def test_material_matching():
    """测试物料匹配"""
    try:
        matcher = MaterialMatcher()

        # 测试完全匹配
        result = await matcher.match_material("卡箍", "DN100")
        assert result is not None, "匹配结果不能为空"
        assert result.matched_code == "P001", "匹配的物料编码不正确"
        assert result.confidence == 1.0, "完全匹配的置信度应为1.0"

        # 测试模糊匹配
        result = await matcher.match_material("卡箍接头", "DN100")
        assert result is not None, "模糊匹配结果不能为空"
        assert result.confidence < 1.0, "模糊匹配的置信度应小于1.0"
        assert result.match_type == "fuzzy", "应该是模糊匹配类型"
    except Exception as e:
        pytest.fail(f"物料匹配测试失败: {str(e)}") 