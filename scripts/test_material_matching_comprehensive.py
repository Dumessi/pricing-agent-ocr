"""
全面的物料匹配测试脚本
使用实际报价单中的物料数据进行测试
"""
import asyncio
import logging
from typing import List, Dict
import pandas as pd
from app.core.database import get_database, COLLECTIONS
from app.services.matcher.matcher import MaterialMatcher
from app.services.matcher.synonym_service import SynonymService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试用例 - 从实际报价单中提取的物料
TEST_CASES = [
    {
        "text": "首联湿式报警阀DN100",
        "expected_code": "A0107001",  # 根据物料清单匹配
        "category": "material_name"
    },
    {
        "text": "不锈钢球阀DN50",
        "expected_code": "E2101066",
        "category": "material_name"
    },
    {
        "text": "法兰盘DN100",
        "expected_code": None,  # 需要通过同义词匹配
        "category": "material_name"
    },
    {
        "text": "铜球阀DN15",
        "expected_code": None,
        "category": "material_name"
    },
    {
        "text": "蝶阀DN80",
        "expected_code": "B0803004",  # 本兴对夹手柄蝶阀DN80
        "category": "material_name"
    },
    {
        "text": "首联雨淋报警阀DN100",
        "expected_code": "A0107004",  # 首联雨淋报警阀DN100（ZSFM）
        "category": "material_name"
    },
    {
        "text": "湿式阀门DN150",
        "expected_code": None,
        "category": "material_name"
    },
    {
        "text": "沟槽蝶阀DN100",
        "expected_code": None,
        "category": "material_name"
    },
    {
        "text": "信号蝶阀DN80",
        "expected_code": "B0803042",  # 本兴对夹信号蝶阀DN80
        "category": "material_name"
    }
]

async def load_material_data() -> List[Dict]:
    """从Excel加载物料数据"""
    df = pd.read_excel("/home/ubuntu/attachments/material-list-20241207.xlsx")
    materials = []
    for _, row in df.iterrows():
        material = {
            "material_code": str(row.get("物料编码", "")),
            "material_name": str(row.get("物料名称", "")),
            "specification": str(row.get("规格型号", "")),
            "unit": str(row.get("计量单位", "个")),
            "factory_price": float(row.get("厂价", 0.0)),
            "status": True
        }
        materials.append(material)
    return materials

async def run_comprehensive_tests():
    """运行全面测试"""
    logger.info("开始全面物料匹配测试...")

    # 初始化服务
    db = await get_database()
    collection = db[COLLECTIONS["materials"]]

    # 确保数据库中有测试数据
    materials = await load_material_data()
    if not await collection.count_documents({}):
        logger.info("导入测试物料数据...")
        await collection.insert_many(materials)

    # 创建匹配器
    matcher = await MaterialMatcher.create()

    # 运行测试用例
    print("\n=== 物料匹配测试结果 ===")
    print("=" * 50)

    for case in TEST_CASES:
        text = case["text"]
        expected_code = case["expected_code"]
        category = case["category"]

        logger.info(f"测试匹配: {text}")
        result = await matcher.match_material(text, category)

        print(f"\n输入文本: {text}")
        print(f"预期编码: {expected_code}")

        if result:
            print(f"匹配类型: {result.match_type}")
            print(f"匹配编码: {result.matched_code}")
            print(f"置信度: {result.confidence:.2f}")
            print(f"物料名称: {result.material_info.material_name}")
            print(f"规格型号: {result.material_info.specification}")
            print(f"计量单位: {result.material_info.unit}")
            print(f"厂价: {result.material_info.factory_price}")

            if expected_code:
                if result.matched_code == expected_code:
                    print("✓ 匹配正确")
                else:
                    print("✗ 匹配错误")
        else:
            print("未找到匹配")
            if expected_code:
                print("✗ 应该找到匹配")

        print("-" * 50)

    logger.info("物料匹配测试完成")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_tests())
