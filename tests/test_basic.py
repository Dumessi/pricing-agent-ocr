import asyncio
import json
from app.services.ocr.ocr_service import OCRService
from app.services.matcher.matcher import MaterialMatcher
from app.models.ocr import FileType
from app.core.database import Database, COLLECTIONS
import os

async def setup_database():
    """设置测试数据库"""
    db = Database.get_db()
    
    # 清空集合
    await db[COLLECTIONS["materials"]].delete_many({})
    await db[COLLECTIONS["ocr_tasks"]].delete_many({})
    
    # 导入测试数据
    with open('tests/test_data/materials.json', 'r') as f:
        materials = json.load(f)
        await db[COLLECTIONS["materials"]].insert_many(materials)

async def test_excel_processing():
    """测试Excel处理"""
    # 创建OCR服务
    ocr_service = OCRService()
    
    # 创建任务
    file_path = 'tests/test_data/test_order.xlsx'
    task_id = await ocr_service.create_task([file_path], [FileType.EXCEL])
    
    # 等待任务完成
    while True:
        task = await ocr_service.get_task_status(task_id)
        if task.status in ['completed', 'failed']:
            break
        await asyncio.sleep(1)
    
    print(f"Excel处理结果: {task.result}")
    return task

async def test_material_matching():
    """测试物料匹配"""
    matcher = MaterialMatcher()
    
    # 测试完全匹配
    result = await matcher.match_material("卡箍", "DN100")
    print(f"完全匹配结果: {result}")
    
    # 测试模糊匹配
    result = await matcher.match_material("卡箍接头", "DN100")
    print(f"模糊匹配结果: {result}")

async def main():
    """主测试函数"""
    # 连接数据库
    await Database.connect_db()
    
    try:
        # 设置测试数据
        await setup_database()
        
        # 生成测试Excel文件
        os.system('python tests/test_data/test_order.py')
        
        # 测试Excel处理
        task = await test_excel_processing()
        
        # 如果Excel处理成功，测试物料匹配
        if task.status == 'completed':
            await test_material_matching()
            
    finally:
        # 关闭数据库连接
        await Database.close_db()

if __name__ == "__main__":
    asyncio.run(main()) 