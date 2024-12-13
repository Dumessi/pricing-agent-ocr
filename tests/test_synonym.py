import pytest
from app.services.matcher.synonym_service import SynonymService
from app.models.material import SynonymCreate, SynonymGroup
from app.core.database import Database

@pytest.fixture(autouse=True)
async def setup_database():
    """设置数据库连接"""
    yield
    Database.close_connection()

@pytest.mark.asyncio
async def test_synonym_service_basic():
    """基本功能测试"""
    service = SynonymService()

    # 测试创建同义词组
    synonym_data = SynonymCreate(
        standard_name="首联湿式报警阀DN100",
        synonyms=["湿式报警阀DN100", "ZSFZ-100", "湿式阀"],
        material_code="A0107001",
        specification="DN100",
        unit="台",
        factory_price=329.90,
        category="material_name"
    )
    group = await service.create_synonym_group(synonym_data)
    assert group.standard_name == "首联湿式报警阀DN100"
    assert len(group.synonyms) == 3
    assert group.material_code == "A0107001"
    assert group.unit == "台"
    assert group.factory_price == 329.90

    # 测试获取同义词组
    retrieved_group = await service.get_synonym_group(group.group_id)
    assert retrieved_group is not None
    assert retrieved_group.standard_name == group.standard_name

    # 清理测试数据
    await service.delete_synonym_group(group.group_id)

@pytest.mark.asyncio
async def test_synonym_matching():
    """同义词匹配测试"""
    service = SynonymService()

    # 创建测试数据
    data = SynonymCreate(
        standard_name="首联雨淋报警阀DN100",
        synonyms=["雨淋报警阀DN100", "ZSFM-100", "雨淋阀"],
        material_code="A0107004",
        specification="DN100",
        unit="台",
        factory_price=649.48,
        category="material_name"
    )
    group = await service.create_synonym_group(data)

    # 1. 精确匹配标准名称
    match1 = await service.find_synonym("首联雨淋报警阀DN100", "material_name")
    assert match1 is not None
    assert match1.material_code == "A0107004"

    # 2. 精确匹配同义词
    match2 = await service.find_synonym("雨淋报警阀DN100", "material_name")
    assert match2 is not None
    assert match2.material_code == "A0107004"

    # 3. 模糊匹配
    match3 = await service.find_synonym("DN100雨淋阀", "material_name")
    assert match3 is not None
    assert match3.material_code == "A0107004"

    # 4. 不匹配的情况
    match4 = await service.find_synonym("完全不相关的词", "material_name")
    assert match4 is None

    # 清理测试数据
    await service.delete_synonym_group(group.group_id)

@pytest.mark.asyncio
async def test_edge_cases():
    """边界情况测试"""
    service = SynonymService()

    # 1. 测试空字符串
    empty_match = await service.find_synonym("", "material_name")
    assert empty_match is None

    # 2. 测试特殊字符
    special_data = SynonymCreate(
        standard_name="特殊@符号",
        synonyms=["@符号", "#特殊", "$test"],
        material_code="S001",
        unit="个",
        category="material_name"
    )
    special_group = await service.create_synonym_group(special_data)
    special_match = await service.find_synonym("@符号", "material_name")
    assert special_match is not None
    assert special_match.material_code == "S001"

    # 3. 测试超长字符串
    long_text = "超" * 100
    long_match = await service.find_synonym(long_text, "material_name")
    assert long_match is None

    # 4. 测试重复同义词
    duplicate_data = SynonymCreate(
        standard_name="重复",
        synonyms=["重复", "重复", "重复测试"],
        material_code="D001",
        unit="个",
        category="material_name"
    )
    duplicate_group = await service.create_synonym_group(duplicate_data)
    assert len(set(duplicate_group.synonyms)) == len(duplicate_group.synonyms)

    # 5. 测试不同类别
    category_data = SynonymCreate(
        standard_name="测试",
        synonyms=["test", "测试用例"],
        material_code="T001",
        unit="个",
        category="specification"  # 不同的类别
    )
    category_group = await service.create_synonym_group(category_data)
    category_match = await service.find_synonym("test", "material_name")  # 错误的类别
    assert category_match is None

    # 清理测试数据
    await service.delete_synonym_group(special_group.group_id)
    await service.delete_synonym_group(duplicate_group.group_id)
    await service.delete_synonym_group(category_group.group_id)

@pytest.mark.asyncio
async def test_material_matcher_with_synonym():
    """物料匹配器集成测试"""
    from app.services.matcher.matcher import MaterialMatcher

    # 创建同义词数据
    synonym_service = SynonymService()
    synonym_data = SynonymCreate(
        standard_name="消防镀锌钢管",
        synonyms=["镀锌钢管", "消防管", "DN150管"],
        material_code="P001",
        specification="DN150",
        unit="米",
        factory_price=None,
        category="material_name"
    )
    group = await synonym_service.create_synonym_group(synonym_data)

    # 测试物料匹配器的同义词匹配
    matcher = MaterialMatcher()

    # 1. 使用同义词进行匹配
    result1 = await matcher.match_material("镀锌钢管")
    assert result1.match_type == "synonym"
    assert result1.confidence >= 0.9
    assert result1.matched_code == "P001"

    # 2. 使用标准名称进行匹配
    result2 = await matcher.match_material("消防镀锌钢管")
    assert result2.match_type == "exact"
    assert result2.confidence == 1.0
    assert result2.matched_code == "P001"

    # 3. 使用模糊匹配
    result3 = await matcher.match_material("DN150镀锌管")
    assert result3.match_type == "fuzzy"
    assert result3.confidence >= 0.7

    # 清理测试数据
    await synonym_service.delete_synonym_group(group.group_id) 