"""
验证物料数据库中的数据
检查测试用例是否存在于导入的数据中
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_material_data():
    """验证物料数据"""
    # 连接数据库
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    collection = db["materials"]

    # 测试用例
    test_cases = [
        "首联湿式报警阀DN100",
        "湿式报警阀DN100",
        "不锈钢球阀DN50",
        "法兰盘DN100",
        "铜球阀",
        "蝶阀DN80",
        "首联雨淋报警阀DN100",
        "湿式阀门DN150"
    ]

    # 检查数据库中的总记录数
    total_count = await collection.count_documents({})
    logger.info(f"数据库中总记录数: {total_count}")

    # 检查每个测试用例的相似匹配
    for text in test_cases:
        # 使用正则表达式进行模糊查询
        regex_pattern = f".*{text}.*"
        similar_materials = await collection.find({
            "material_name": {"$regex": regex_pattern, "$options": "i"}
        }).to_list(None)

        print(f"\n测试用例: {text}")
        print(f"找到 {len(similar_materials)} 个相似匹配:")

        for material in similar_materials:
            print(f"- 物料编码: {material.get('material_code')}")
            print(f"  物料名称: {material.get('material_name')}")
            print(f"  规格型号: {material.get('specification', 'N/A')}")
            print(f"  计量单位: {material.get('unit', 'N/A')}")
            print(f"  厂价: {material.get('factory_price', 'N/A')}")
            print("---")

    # 检查一些常见的物料类别
    categories = ["报警阀", "球阀", "法兰", "蝶阀"]
    print("\n物料类别统计:")
    for category in categories:
        count = await collection.count_documents({
            "material_name": {"$regex": category, "$options": "i"}
        })
        print(f"- {category}: {count} 条记录")

if __name__ == "__main__":
    asyncio.run(verify_material_data())
