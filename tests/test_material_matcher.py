import pytest
import pandas as pd
import re
import logging
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.matcher.matcher import MaterialMatcher
from app.models.material import MaterialBase, MaterialMatch
from app.core.database import Database, COLLECTIONS

@pytest.fixture
async def material_data() -> List[dict]:
    """加载金蝶物料清单作为测试数据"""
    df = pd.read_excel("/home/ubuntu/attachments/material-list-20241207.xlsx")
    materials = []
    for _, row in df.iterrows():
        material = {
            "material_code": row["编码"],
            "material_name": row["名称"],
            "specification": row["规格型号"] if pd.notna(row["规格型号"]) else None,
            "unit": row["基本单位"],
            "factory_price": float(row["厂价"]) if pd.notna(row["厂价"]) else None,
            "status": True
        }
        materials.append(material)
    return materials

@pytest.fixture
async def mock_db(material_data):
    """模拟MongoDB数据库"""
    class AsyncCursor:
        def __init__(self, items):
            self.items = items
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index >= len(self.items):
                raise StopAsyncIteration
            item = self.items[self.index]
            self.index += 1
            return item

    mock_collection = AsyncMock()

    # 设置find_one的返回值
    async def mock_find_one(query):
        for material in material_data:
            if (query.get("material_name") == material["material_name"] or
                query.get("material_code") == material["material_code"]):
                return material
        return None
    mock_collection.find_one.side_effect = mock_find_one

    # 设置find的返回值
    def mock_find(query=None):
        filtered_data = []
        if query:
            for material in material_data:
                # 处理正则表达式查询
                if "$regex" in query.get("material_name", {}):
                    pattern = query["material_name"]["$regex"]
                    if re.search(pattern, material["material_name"], re.IGNORECASE):
                        filtered_data.append(material)
                # 处理分类查询
                elif query.get("$or"):
                    for or_condition in query["$or"]:
                        if any(material.get("category", {}).get(k) == v
                              for k, v in or_condition.items()):
                            filtered_data.append(material)
                            break
                else:
                    if all(material.get(k) == v for k, v in query.items()):
                        filtered_data.append(material)
        else:
            filtered_data = material_data

        return AsyncCursor(filtered_data)

    mock_collection.find = MagicMock(side_effect=mock_find)

    with patch.object(Database, 'get_db') as mock_get_db:
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_collection
        mock_get_db.return_value = mock_db
        yield mock_db

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
