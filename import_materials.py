from app.utils.excel_parser import read_and_process_excel
from app.core.database import get_database, COLLECTIONS, close_database
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def import_materials():
    try:
        file_path = os.path.expanduser('~/attachments/material-list-20241207.xlsx')
        logger.info(f"开始读取Excel文件: {file_path}")
        df = read_and_process_excel(file_path)
        logger.info(f"成功读取 {len(df)} 条记录")

        db = await get_database()
        collection = db[COLLECTIONS["materials"]]

        await collection.delete_many({})
        logger.info("已清除现有数据")

        materials = []
        for _, row in df.iterrows():
            material = row.to_dict()
            material['category'] = {
                'type': material.get('material_type', ''),
                'group': material.get('material_group', '')
            }
            material['attributes'] = {
                'brand': material.get('brand', ''),
                'model': material.get('model', ''),
                'size': material.get('size', '')
            }
            materials.append(material)

        for material in materials:
            try:
                await collection.update_one(
                    {"material_code": material["material_code"]},
                    {"$set": material},
                    upsert=True
                )
            except Exception as e:
                logger.error(f"导入物料 {material['material_code']} 时出错: {str(e)}")

        logger.info(f"成功导入 {len(materials)} 个物料")
    except Exception as e:
        logger.error(f"导入过程出错: {str(e)}")
        raise
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(import_materials()) 