import re
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.material import MaterialBase, MaterialMatch
from app.services.matcher.matcher import MaterialMatcher
from app.core.database import get_database, COLLECTIONS
import logging

logger = logging.getLogger(__name__)

@pytest.fixture
async def material_data():
    """测试用物料数据"""
    return [
        {
            "material_code": "M001",
            "material_name": "首联湿式报警阀DN100",
            "specification": "DN100",
            "unit": "台",
            "factory_price": 2000.0,
            "status": True
        },
        {
            "material_code": "M002",
            "material_name": "球阀DN50",
            "specification": "DN50",
            "unit": "个",
            "factory_price": 150.0,
            "status": True
        },
        {
            "material_code": "M003",
            "material_name": "闸阀2寸",
            "specification": "2寸",
            "unit": "台",
            "factory_price": 200.0,
            "status": True
        },
        {
            "material_code": "M004",
            "material_name": "止回阀DN80",
            "specification": "DN80",
            "unit": "个",
            "factory_price": 180.0,
            "status": True
        },
        {
            "material_code": "M005",
            "material_name": "蝶阀DN200",
            "specification": "DN200",
            "unit": "台",
            "factory_price": 300.0,
            "status": True
        },
        {
            "material_code": "M006",
            "material_name": "法兰DN100",
            "specification": "DN100",
            "unit": "件",
            "factory_price": 80.0,
            "status": True
        }
    ]

@pytest.fixture
async def mock_db(test_db, material_data):
    """Mock数据库"""
    # Insert test data into materials collection
    collection = test_db[COLLECTIONS["materials"]]
    await collection.delete_many({})  # Clear existing data

    for item in material_data:
        await collection.insert_one(item)
        logger.info(f"Inserted test material: {item['material_name']}")

    return test_db

@pytest.fixture
async def matcher(mock_db):
    """创建物料匹配器实例"""
    return await MaterialMatcher.create()

@pytest.mark.asyncio
async def test_exact_match(matcher):
    """测试完全匹配"""
    text = "首联湿式报警阀DN100"
    result = await matcher.match_material(text)
    assert result is not None
    assert result.match_type == "exact"
    assert result.confidence >= 0.9
    assert result.material_info is not None
    assert result.material_info.material_code == "M001"

@pytest.mark.asyncio
async def test_specification_match(matcher):
    """测试规格匹配"""
    text = "球阀"
    spec = "DN50"
    result = await matcher.match_material(text, spec)
    assert result is not None
    assert result.match_type == "specification"
    assert result.confidence >= 0.7
    assert result.material_info is not None
    assert result.material_info.material_code == "M002"

@pytest.mark.asyncio
async def test_fuzzy_match(matcher):
    """测试模糊匹配"""
    text = "湿式阀DN100"  # 同义词匹配
    result = await matcher.match_material(text)
    assert result is not None
    assert result.match_type == "synonym"
    assert result.confidence >= 0.7
    assert result.material_info is not None
    assert result.material_info.material_code == "M001"

@pytest.mark.asyncio
async def test_category_match(matcher):
    """测试分类匹配"""
    text = "闸阀"
    result = await matcher.match_material(text)
    assert result is not None
    assert result.match_type == "category"
    assert result.confidence >= 0.6
    assert result.material_info is not None
    assert result.material_info.material_code == "M003"

@pytest.mark.asyncio
async def test_no_match(matcher):
    """测试无匹配情况"""
    text = "不存在的物料XXYYZZ"
    result = await matcher.match_material(text)
    assert result is not None
    assert result.match_type == "none"
    assert result.confidence == 0.0
    assert result.material_info is not None
    assert result.material_info.material_code == ""
    assert result.material_info.unit == "个"

@pytest.mark.asyncio
async def test_unit_standardization(matcher):
    """测试单位标准化"""
    text = "铸铁法兰闸阀"
    result = await matcher.match_material(text)
    assert result.material_info.unit in ["个", "台", "件", "套"]

@pytest.mark.asyncio
async def test_price_validation(matcher):
    """测试价格有效性"""
    text = "首联湿式报警阀DN100"
    result = await matcher.match_material(text)
    assert result.material_info.factory_price is not None
    assert result.material_info.factory_price > 0

@pytest.mark.asyncio
async def test_real_material_variations(matcher):
    """测试实际物料名称变体"""
    test_cases = [
        ("湿式阀DN100", "M001"),      # 同义词匹配
        ("球阀DN50", "M002"),         # 规格匹配
        ("闸阀2寸", "M003"),          # 规格匹配
        ("止回阀DN80", "M004"),       # 精确匹配
        ("蝶阀DN200", "M005"),        # 精确匹配
        ("法兰DN100", "M006")         # 精确匹配
    ]

    for input_text, expected_code in test_cases:
        result = await matcher.match_material(input_text)
        assert result is not None
        assert result.match_type in ["exact", "synonym", "specification"]
        assert result.confidence >= 0.6
        assert result.material_info is not None
        assert result.material_info.material_code == expected_code

@pytest.mark.asyncio
async def test_specification_variations(matcher):
    """测试规格型号变体"""
    test_cases = [
        ("球阀", "DN50", "M002"),     # 基本规格
        ("闸阀", "2寸", "M003"),      # 英寸规格
        ("止回阀", "DN80", "M004"),   # 规格匹配
        ("蝶阀", "DN200", "M005"),    # 规格匹配
    ]

    for base_name, spec, expected_code in test_cases:
        result = await matcher.match_material(base_name, spec)
        assert result is not None
        assert result.match_type in ["specification", "category"]
        assert result.confidence >= 0.6
        assert result.material_info is not None
        assert result.material_info.material_code == expected_code

@pytest.mark.asyncio
async def test_unit_variations(matcher):
    """测试单位变体"""
    test_cases = [
        ("首联湿式报警阀DN100", "台"),
        ("球阀DN50", "个"),
        ("闸阀2寸", "台"),
        ("止回阀DN80", "个"),
        ("蝶阀DN200", "台")
    ]

    for material_name, expected_unit in test_cases:
        result = await matcher.match_material(material_name)
        assert result is not None
        assert result.material_info is not None
        assert result.material_info.unit == expected_unit
