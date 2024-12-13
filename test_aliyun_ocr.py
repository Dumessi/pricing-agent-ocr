import asyncio
import os
from app.services.ocr.aliyun_ocr_service import AliyunOCRService
from tabulate import tabulate
import pandas as pd

async def test_aliyun_ocr():
    # 创建OCR服务实例
    ocr_service = AliyunOCRService()
    
    # 测试图片路径
    image_path = "pricinglist-data/WechatIMG112.jpg"
    
    print(f"\n{'='*50}")
    print(f"测试图片: {image_path}")
    print(f"{'='*50}")
    
    try:
        # 调用OCR识别
        result = await ocr_service.recognize_table(image_path)
        
        if result:
            print("\n识别成功!")
            
            # 输出原始识别文本
            print("\n原始识别文本:")
            print(result.raw_text)
            
            # 创建DataFrame
            data = []
            current_row = []
            current_row_idx = 0
            
            for cell in sorted(result.cells, key=lambda x: (x.row, x.column)):
                if cell.row > current_row_idx:
                    if current_row:
                        data.append(current_row)
                    current_row = []
                    current_row_idx = cell.row
                current_row.append(cell.text)
            
            if current_row:
                data.append(current_row)
            
            # 创建DataFrame
            df = pd.DataFrame(data)
            
            # 输出表格
            print("\n表格内容:")
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
            
            # 输出置信度统计
            confidences = [cell.confidence for cell in result.cells]
            if confidences:
                avg_conf = sum(confidences) / len(confidences)
                print(f"\n置信度统计:")
                print(f"平均置信度: {avg_conf:.2f}")
                print(f"最高置信度: {max(confidences):.2f}")
                print(f"最低置信度: {min(confidences):.2f}")
            
            # 保存为Excel文件
            output_dir = "ocr_results"
            os.makedirs(output_dir, exist_ok=True)
            excel_path = os.path.join(output_dir, f"aliyun_ocr_result_{os.path.basename(image_path)}.xlsx")
            df.to_excel(excel_path, index=False)
            print(f"\n结果已保存至: {excel_path}")
        else:
            print("识别失败: 未返回结果")
            
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_aliyun_ocr()) 