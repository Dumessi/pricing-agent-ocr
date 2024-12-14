"""
验证物料数据导入情况
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

async def verify_materials():
    """验证物料数据"""
    print("开始验证物料数据...")

    # 连接MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    collection = db["materials"]

    # 检查总数
    total = await collection.count_documents({})
    print(f"物料总数: {total}")

    # 查看几个样本数据
    print("\n样本数据:")
    async for doc in collection.find().limit(5):
        print("-" * 50)
        print(f"物料编码: {doc.get('material_code')}")
        print(f"物料名称: {doc.get('material_name')}")
        print(f"规格型号: {doc.get('specification')}")
        print(f"计量单位: {doc.get('unit')}")
        print(f"厂价: {doc.get('factory_price')}")

    # 搜索特定物料
    search_terms = ["阀", "球阀", "DN100"]
    print("\n搜索结果:")
    for term in search_terms:
        count = await collection.count_documents({"material_name": {"$regex": term}})
        print(f"包含'{term}'的物料数量: {count}")
        if count > 0:
            doc = await collection.find_one({"material_name": {"$regex": term}})
            print(f"示例: {doc.get('material_name')} ({doc.get('material_code')})")

if __name__ == "__main__":
    asyncio.run(verify_materials())
