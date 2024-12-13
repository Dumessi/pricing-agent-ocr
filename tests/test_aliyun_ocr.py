import os
import asyncio
from pathlib import Path
from app.services.ocr.aliyun_ocr_service import AliyunOCRService
import pandas as pd

async def test_aliyun_ocr():
    # 初始化OCR服务
    ocr_service = AliyunOCRService()
    
    # 获取项目根目录
    base_dir = Path(__file__).resolve().parent.parent
    
    # 测试图片路径
    test_image_path = os.path.join(base_dir, "pricinglist-data", "WechatIMG112.jpg")
    
    # 确保测试图片存在
    if not os.path.exists(test_image_path):
        print(f"测试图片不存在: {test_image_path}")
        return
    
    print(f"\n开始识别图片: {test_image_path}")
    print("=" * 50)
    
    # 执行OCR识别
    result = await ocr_service.recognize_table(test_image_path)
    
    if result:
        print("\n识别成功!")
        print("=" * 50)
        
        # 打印表头信息
        if result.headers:
            print("\n表头信息:")
            print("-" * 30)
            for idx, header in enumerate(result.headers):
                print(f"列{idx}: {header}")
        
        # 打印单元格信息
        print(f"\n单元格内容 (共 {len(result.cells)} 个):")
        print("-" * 30)
        
        # 创建一个二维列表来存储表格数据
        max_row = max(cell.row for cell in result.cells) + 1
        max_col = max(cell.column for cell in result.cells) + 1
        table_data = [['' for _ in range(max_col)] for _ in range(max_row)]
        
        # 填充表格数据
        for cell in result.cells:
            table_data[cell.row][cell.column] = f"{cell.text} ({cell.confidence:.2f})"
        
        # 使用pandas创建表格显示
        df = pd.DataFrame(table_data)
        if result.headers:
            df.columns = result.headers
        
        print("\n表格内容:")
        print(df.to_string())
        
        # 保存为Excel文件
        output_dir = os.path.join(base_dir, "ocr_results")
        os.makedirs(output_dir, exist_ok=True)
        excel_path = os.path.join(output_dir, "aliyun_ocr_result.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"\n结果已保存至: {excel_path}")
        
    else:
        print("OCR识别失败")

if __name__ == "__main__":
    asyncio.run(test_aliyun_ocr()) 