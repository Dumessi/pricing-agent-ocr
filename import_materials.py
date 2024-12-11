from app.utils.excel_parser import read_and_process_excel
from app.core.database import Database, COLLECTIONS
import asyncio

async def import_materials():
    # 读取并处理Excel文件
    file_path = '/Users/dumessi/Library/Mobile Documents/com~apple~CloudDocs/macos-sharing/cursor-project/pricing-agent-ocr-dic/material-list/material-list-20241207.xlsx'
    df = read_and_process_excel(file_path)
    
    # 获取数据库集合
    db = Database.get_db()
    collection = db[COLLECTIONS["materials"]]
    
    # 转换为字典列表
    materials = df.to_dict('records')
    
    # 批量更新数据
    for material in materials:
        try:
            await collection.update_one(
                {"material_code": material["material_code"]},
                {"$set": material},
                upsert=True
            )
        except Exception as e:
            print(f"Error importing material {material['material_code']}: {str(e)}")
    
    print(f"Successfully imported {len(materials)} materials")

# 运行导入
if __name__ == "__main__":
    asyncio.run(import_materials()) 