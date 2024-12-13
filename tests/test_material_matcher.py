import re
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.material import MaterialBase, MaterialMatch
from app.services.matcher.matcher import MaterialMatcher
from app.core.database import Database, COLLECTIONS
import logging

logger = logging.getLogger(__name__)

@pytest.fixture
async def material_data():
    """测试用物料数据"""
    return [
        {
            "material_code": "M001",
            "material_name": "消防镀锌钢管",
            "specification": "DN150",
            "unit": "米",
            "factory_price": 100.0,
            "status": True
        },
        {
            "material_code": "M002",
            "material_name": "湿式报警阀",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 2000.0,
            "status": True
        }
    ]

@pytest.fixture
async def mock_db(database, material_data):
    """Mock数据库"""
    # Insert test data into materials collection
    for item in material_data:
        await database[COLLECTIONS["materials"]].insert_one(item)
        logger.info(f"Inserted test material: {item['material_name']}")

    yield database

    # Cleanup
    await database[COLLECTIONS["materials"]].delete_many({})
    logger.info("Cleaned up test materials")

@pytest.fixture
async def matcher(mock_db):
    """创建物料匹配器实例"""
    return MaterialMatcher()

@pytest.mark.asyncio
async def test_exact_match(matcher):
    """测试完全匹配"""
    text = "首联湿式报警阀DN100"
    result = await matcher.match_material(text)
    assert result.match_type == "exact"
    assert result.confidence >= 0.9
    assert "DN100" in result.material_info.material_name

@pytest.mark.asyncio
async def test_specification_match(matcher):
    """测试规格匹配"""
    text = "湿式报警阀"
    spec = "DN100"
    result = await matcher.match_material(text, spec)
    assert result.match_type == "specification"
    assert result.confidence >= 0.7
    assert "DN100" in result.material_info.material_name

@pytest.mark.asyncio
async def test_fuzzy_match(matcher):
    """测试模糊匹配"""
    text = "湿式报警阀DN100型"  # 略微变形的名称
    result = await matcher.match_material(text)
    assert result.match_type in ["fuzzy", "specification"]
    assert result.confidence >= 0.6
    assert "报警阀" in result.material_info.material_name

@pytest.mark.asyncio
async def test_category_match(matcher):
    """测试分类匹配"""
    text = "球阀DN50"
    result = await matcher.match_material(text)
    assert result.match_type in ["category", "specification"]
    assert result.confidence >= 0.7
    assert "阀" in result.material_info.material_name

@pytest.mark.asyncio
async def test_no_match(matcher):
    """测试无匹配情况"""
    text = "不存在的物料XXYYZZ"
    result = await matcher.match_material(text)
    assert result.match_type == "none"
    assert result.confidence == 0.0
    assert result.material_info is None

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
        ("湿式报警阀 DN100", "首联湿式报警阀DN100"),  # 标准名称变体
        ("DN150湿式报警阀", "首联湿式报警阀DN150"),   # 规格位置变化
        ("雨淋报警阀（DN100）", "首联雨淋报警阀DN100"), # 带括号规格
        ("球阀 2寸", "不锈钢球阀DN50"),              # 英寸到DN转换
        ("304法兰球阀", "不锈钢法兰球阀"),           # 材质表示变化
    ]

    for input_text, expected_name in test_cases:
        result = await matcher.match_material(input_text)
        assert result.match_type in ["exact", "fuzzy", "specification"]
        assert result.confidence >= 0.6
        assert expected_name in result.material_info.material_name

@pytest.mark.asyncio
async def test_specification_variations(matcher):
    """测试规格型号变体"""
    test_cases = [
        ("球阀", "DN50", "PN16"),           # 基本规格
        ("闸阀", "2寸", "304"),             # 英寸规格
        ("止回阀", "DN80", "法兰"),         # 连接方式
        ("蝶阀", "DN200", "手动"),          # 驱动方式
        ("调节阀", "DN65", "单作用"),       # 结构特征
    ]

    for base_name, spec1, spec2 in test_cases:
        result = await matcher.match_material(base_name, f"{spec1} {spec2}")
        assert result.match_type in ["specification", "category"]
        assert result.confidence >= 0.6
        assert result.material_info is not None

@pytest.mark.asyncio
async def test_unit_variations(matcher):
    """测试单位变体"""
    test_cases = [
        ("球阀", "个"),
        ("闸阀", "台"),
        ("法兰", "件"),
        ("管件", "套"),
    ]

    for material_name, expected_unit in test_cases:
        result = await matcher.match_material(material_name)
        assert result.material_info.unit == expected_unit
