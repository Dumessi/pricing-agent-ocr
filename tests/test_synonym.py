import pytest
import logging
from app.models.material import MaterialBase
from app.services.matcher.matcher import MaterialMatcher
from app.services.matcher.synonym_service import SynonymService, SynonymCreate, SynonymGroup

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_synonym_service_basic():
    """同义词服务基础测试"""
    service = await SynonymService.create()

    # 清理已有数据
    await service.collection.delete_many({})

    # 创建测试数据
    test_cases = [
        {
            "standard_name": "首联湿式报警阀DN100",
            "synonyms": ["湿式报警阀DN100", "ZSFZ-100", "湿式阀"],
            "material_code": "M001",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 2000.0,
            "category": "material_name"
        },
        {
            "standard_name": "球阀",
            "synonyms": ["不锈钢球阀", "手动球阀", "铜球阀"],
            "material_code": "M002",
            "specification": "DN50",
            "unit": "个",
            "factory_price": 150.0,
            "category": "material_name"
        },
        {
            "standard_name": "法兰",
            "synonyms": ["法兰盘", "法兰片", "法兰环"],
            "material_code": "M006",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 300.0,
            "category": "material_name"
        }
    ]

    for case in test_cases:
        data = SynonymCreate(**case)
        group = await service.create_synonym_group(data)
        logger.info(f"Created synonym group for: {case['standard_name']}")

        # 验证创建结果
        assert group is not None
        assert group.standard_name == case["standard_name"]
        assert all(syn in group.synonyms for syn in case["synonyms"])
        assert group.material_code == case["material_code"]

@pytest.mark.asyncio
async def test_synonym_matching():
    """同义词匹配测试"""
    service = await SynonymService.create()

    # 清理已有数据
    await service.collection.delete_many({})

    # 创建测试数据
    test_cases = [
        {
            "standard_name": "首联湿式报警阀DN100",
            "synonyms": ["湿式报警阀DN100", "ZSFZ-100", "湿式阀"],
            "material_code": "M001",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 2000.0,
            "category": "material_name"
        },
        {
            "standard_name": "球阀",
            "synonyms": ["不锈钢球阀", "手动球阀", "铜球阀"],
            "material_code": "M002",
            "specification": "DN50",
            "unit": "个",
            "factory_price": 150.0,
            "category": "material_name"
        },
        {
            "standard_name": "法兰",
            "synonyms": ["法兰盘", "法兰片", "法兰环"],
            "material_code": "M006",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 300.0,
            "category": "material_name"
        }
    ]

    for case in test_cases:
        data = SynonymCreate(**case)
        group = await service.create_synonym_group(data)

        # 1. 精确匹配标准名称
        match1 = await service.find_synonym(case["standard_name"], "material_name")
        assert match1 is not None
        assert match1.material_code == case["material_code"]

        # 2. 精确匹配同义词
        for synonym in case["synonyms"]:
            match2 = await service.find_synonym(synonym, "material_name")
            assert match2 is not None
            assert match2.material_code == case["material_code"]

        # 3. 模糊匹配（添加规格信息）
        fuzzy_text = f"{case['synonyms'][0]} {case['specification']}"
        match3 = await service.find_synonym(fuzzy_text, "material_name")
        assert match3 is not None
        assert match3.material_code == case["material_code"]

@pytest.mark.asyncio
async def test_edge_cases():
    """边界情况测试"""
    service = await SynonymService.create()

    # 清理已有数据
    await service.collection.delete_many({})

    # 1. 测试空字符串
    empty_match = await service.find_synonym("", "material_name")
    assert empty_match is None

    # 2. 测试不同类别（先创建正确类别的组）
    await service.collection.delete_many({})
    category_data = SynonymCreate(
        standard_name="测试",
        synonyms=["test", "测试用例"],
        material_code="T001",
        unit="个",
        factory_price=100.0,
        specification="DN50",
        category="specification"  # 不同的类别
    )
    category_group = await service.create_synonym_group(category_data)
    category_match = await service.find_synonym("test", "material_name")  # 错误的类别
    assert category_match is None

    # 3. 测试特殊字符
    await service.collection.delete_many({})
    special_data = SynonymCreate(
        standard_name="特殊@符号",
        synonyms=["@符号", "#特殊", "$test"],
        material_code="S001",
        unit="个",
        factory_price=100.0,
        specification="DN50",
        category="material_name"
    )
    special_group = await service.create_synonym_group(special_data)
    special_match = await service.find_synonym("@符号", "material_name")
    assert special_match is not None
    assert special_match.material_code == "S001"

    # 4. 测试超长字符串
    await service.collection.delete_many({})
    long_text = "超" * 100
    long_match = await service.find_synonym(long_text, "material_name")
    assert long_match is None

    # 5. 测试重复同义词
    await service.collection.delete_many({})
    duplicate_data = SynonymCreate(
        standard_name="重复",
        synonyms=["重复", "重复", "重复测试"],
        material_code="D001",
        unit="个",
        factory_price=100.0,
        specification="DN50",
        category="material_name"
    )
    duplicate_group = await service.create_synonym_group(duplicate_data)
    assert len(set(duplicate_group.synonyms)) == len(duplicate_group.synonyms)

@pytest.mark.asyncio
async def test_material_matcher_with_synonym():
    """物料匹配器集成测试"""
    from app.services.matcher.matcher import MaterialMatcher

    # 创建同义词数据
    synonym_service = await SynonymService.create()

    # 清理已有数据
    await synonym_service.collection.delete_many({})

    # 创建测试数据
    test_data = [
        {
            "standard_name": "首联湿式报警阀DN100",
            "synonyms": ["湿式报警阀DN100", "ZSFZ-100", "湿式阀"],
            "material_code": "M001",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 2000.0,
            "category": "material_name"
        },
        {
            "standard_name": "球阀",
            "synonyms": ["不锈钢球阀", "手动球阀", "铜球阀"],
            "material_code": "M002",
            "specification": "DN50",
            "unit": "个",
            "factory_price": 150.0,
            "category": "material_name"
        },
        {
            "standard_name": "法兰",
            "synonyms": ["法兰盘", "法兰片", "法兰环"],
            "material_code": "M006",
            "specification": "DN100",
            "unit": "个",
            "factory_price": 300.0,
            "category": "material_name"
        }
    ]

    # 创建同义词组
    for data in test_data:
        group_data = SynonymCreate(**data)
        await synonym_service.create_synonym_group(group_data)
        logger.info(f"Created synonym group: {data['standard_name']}")

    test_cases = [
        ("湿式阀DN100", "M001", "synonym"),
        ("不锈钢球阀", "M002", "synonym"),
        ("法兰盘", "M006", "synonym"),
        ("首联湿式报警阀DN100", "M001", "exact"),
        ("球阀DN50", "M002", "exact"),
        ("DN100法兰", "M006", "specification")
    ]

    # 测试物料匹配器的同义词匹配
    matcher = await MaterialMatcher.create()

    for input_text, expected_code, expected_type in test_cases:
        result = await matcher.match_material(input_text)
        assert result is not None, f"No match found for '{input_text}'"
        assert result.match_type == expected_type, f"Failed matching '{input_text}'"
        assert result.material_code == expected_code, f"Wrong material code for '{input_text}'"
        if expected_type == "exact":
            assert result.confidence == 1.0
        else:
            assert result.confidence >= 0.7 