"""
导入测试物料数据到MongoDB
用于准备本地测试环境
"""
import asyncio
import os
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.models.material import MaterialBase

async def import_materials():
    """导入物料数据到MongoDB"""
    print("开始导入物料数据...")

    # 连接MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]
    collection = db["materials"]

    # 清理已有数据
    await collection.delete_many({})

    # 读取Excel文件
    excel_path = os.path.expanduser("~/attachments/material-list-20241207.xlsx")
    df = pd.read_excel(excel_path)

    # 转换数据格式
    materials = []
    for _, row in df.iterrows():
        try:
            material = {
                "material_code": str(row["编码"]).strip(),
                "material_name": str(row["名称"]).strip(),
                "specification": str(row["规格型号"]).strip() if pd.notna(row["规格型号"]) else "",
                "unit": str(row["基本单位"]).strip(),
                "factory_price": float(row["厂价"]) if pd.notna(row["厂价"]) else 0.0,
                "status": True
            }
            # 只添加有效的物料数据
            if material["material_code"] and material["material_name"]:
                materials.append(material)
        except Exception as e:
            print(f"处理行数据出错: {row}, 错误: {str(e)}")

    # 批量插入数据
    if materials:
        result = await collection.insert_many(materials)
        print(f"成功导入 {len(result.inserted_ids)} 条物料数据")
    else:
        print("没有有效的物料数据可导入")

    # 创建索引
    await collection.create_index("material_code")
    await collection.create_index("material_name")
    await collection.create_index([("material_name", "text")])  # 添加全文索引用于搜索

    print("物料数据导入完成")

if __name__ == "__main__":
    asyncio.run(import_materials())
