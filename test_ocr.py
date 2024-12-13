import os
import asyncio
from app.services.ocr.aliyun_ocr_service import AliyunOCRService

async def test_ocr():
    # 初始化OCR服务
    ocr_service = AliyunOCRService()
    
    # 测试图片路径
    test_image = "test_images/WechatIMG112.jpg"
    
    if not os.path.exists(test_image):
        print(f"测试图片 {test_image} 不存在")
        return
    
    try:
        # 执行OCR识别
        result = await ocr_service.recognize_table(test_image)
        
        if result:
            print("\n识别结果:")
            print("=" * 50)
            print(f"表头: {result.headers}")
            print("\n单元格内容:")
            
            # 按行列组织单元格
            cells_by_row = {}
            for cell in result.cells:
                if cell.row not in cells_by_row:
                    cells_by_row[cell.row] = {}
                cells_by_row[cell.row][cell.column] = cell
            
            # 打印表格内容
            for row in sorted(cells_by_row.keys()):
                row_cells = cells_by_row[row]
                row_content = []
                for col in sorted(row_cells.keys()):
                    cell = row_cells[col]
                    row_content.append(f"{cell.text}({cell.confidence:.2f})")
                print(f"行 {row}: {' | '.join(row_content)}")
            
            print("\n原始文本:")
            print(result.raw_text)
        else:
            print("识别失败，未返回结果")
            
    except Exception as e:
        print(f"OCR识别出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ocr()) 