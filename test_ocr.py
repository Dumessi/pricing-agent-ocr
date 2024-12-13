import asyncio
import os
from app.services.ocr.ocr_service import OCRService
from app.models.ocr import FileType
import cv2
import numpy as np
from tabulate import tabulate
from typing import List, Dict, Tuple
import pandas as pd
import re

def normalize_text(text: str) -> str:
    """规范化文本内容"""
    if not text:
        return ""
    # 移除多余的空白字符
    text = " ".join(text.split())
    # 移除特殊字符
    text = text.strip(".,;:!?()[]{}\"'")
    # 统一全角字符到半角
    text = "".join([chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in text])
    return text.strip()

def extract_number(text: str) -> Tuple[str, str]:
    """提取数字和单位"""
    # 常见单位映射
    unit_patterns = {
        r'(?:个|套|件|PCS|pcs)': '个',
        r'(?:条|根)': '条',
        r'(?:块|片)': '块',
        r'(?:米|m|M)': 'm',
        r'(?:箱|盒)': '箱'
    }
    
    # 匹配数字和单位的模式
    number_unit_pattern = r'(\d+(?:\.\d+)?)\s*({})'.format('|'.join(unit_patterns.keys()))
    matches = list(re.finditer(number_unit_pattern, text))
    
    if matches:
        # 使用最后一个匹配（通常是数量）
        match = matches[-1]
        number, unit = match.groups()
        # 规范化单位
        for pattern, std_unit in unit_patterns.items():
            if re.match(pattern, unit):
                return number, std_unit
    
    # 如果没有找到带单位的数字，尝试只匹配数字
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    if numbers:
        # 使用最后一个数字（通常是数量）
        return numbers[-1], ""
    
    return "", ""

def extract_spec(text: str) -> str:
    """提取规格型号"""
    # DN规格模式
    dn_patterns = [
        r'DN\s*\d+(?:\s*[×xX*]\s*\d+)*',  # 标准DN规格
        r'[Dd]\s*\d+(?:\s*[×xX*]\s*\d+)*',  # 简写形式
        r'(?<!N)\d+\s*[×xX*]\s*\d+(?:\s*[×xX*]\s*\d+)*'  # 纯数字规格
    ]
    
    all_specs = []
    for pattern in dn_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            spec = match.group()
            # 规范化格式
            spec = re.sub(r'[dD](?!N)', 'DN', spec)  # 将d/D替换为DN
            spec = re.sub(r'\s+', '', spec)  # 移除空格
            spec = re.sub(r'[xX]', '×', spec)  # 统一乘号
            all_specs.append(spec)
    
    # 返回最长的规格（通常是最完整的）
    return max(all_specs, key=len) if all_specs else ""

def clean_material_name(text: str) -> str:
    """清理物料名称"""
    # 移除常见无关文本
    remove_patterns = [
        r'\d+(?:\.\d+)?',  # 数字
        r'DN\s*\d+(?:\s*[×xX*]\s*\d+)*',  # DN规格
        r'[Dd]\s*\d+(?:\s*[×xX*]\s*\d+)*',  # 简写规格
        r'(?:个|条|套|件|PCS|pcs|块|片|米|m|M|箱|盒)',  # 单位
        r'[#\-_]+',  # 特殊字符
        r'\s+',  # 多余空格
        r'[wW]\s*-',  # 特殊标记
        r'[a-zA-Z]+',  # 英文字符
    ]
    
    # 需要保留的关键词
    keep_words = [
        "沟槽", "卡箍", "三通", "四通", "弯头", "大小头", "闸阀", "蝶阀",
        "管卡", "丝接", "镀锌", "不锈钢", "碳钢", "铸铁", "法兰", "螺栓",
        "垫片", "密封圈", "水流指示器", "报警阀", "信号", "明杆", "湿式",
        "钢卡", "建支"
    ]
    
    # 保护关键词（添加特殊标记）
    for word in keep_words:
        text = text.replace(word, f"___{word}___")
    
    # 移除无关文本
    for pattern in remove_patterns:
        text = re.sub(pattern, ' ', text)
    
    # 恢复关键词
    text = text.replace("___", "")
    
    # 清理和规范化
    text = normalize_text(text)
    
    # 移除重复词
    words = text.split()
    unique_words = []
    for word in words:
        if word not in unique_words and len(word) > 1:  # 只保留长度大于1的词
            unique_words.append(word)
    text = ' '.join(unique_words)
    
    return text

def format_table_result(cells, headers) -> pd.DataFrame:
    """将OCR结果格式化为标准表格"""
    # 标准列名
    standard_columns = [
        "序号",
        "物料名称",
        "规格型号",
        "单位",
        "数量",
        "备注"
    ]
    
    # 合并所有文本
    full_text = " ".join([normalize_text(cell.text) for cell in cells])
    
    # 预处理：移除表头信息
    header_patterns = [
        r'产品清单明细表',
        r'货物\(劳务\)名称',
        r'连接方式',
        r'单位',
        r'数量',
        r'序号',
        r'口径',
    ]
    
    for pattern in header_patterns:
        full_text = re.sub(pattern, '', full_text)
    
    # 分割成行
    rows = []
    current_row = []
    current_number = ""
    
    # 使用空格分割文本
    tokens = full_text.split()
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # 如果是序号（1-3位数字）
        if re.match(r'^\d{1,3}$', token):
            if current_row:
                rows.append((current_number, ' '.join(current_row)))
            current_number = token
            current_row = []
        else:
            current_row.append(token)
        i += 1
    
    # 添加最后一行
    if current_row:
        rows.append((current_number, ' '.join(current_row)))
    
    # 处理每一行
    all_texts = []
    for row_num, content in rows:
        # 提取规格型号
        spec = extract_spec(content)
        # 提取数量和单位
        number, unit = extract_number(content)
        # 清理物料名称
        material_name = clean_material_name(content)
        
        if material_name or spec or number or unit:
            all_texts.append({
                "序号": row_num,
                "物料名称": material_name,
                "规格型号": spec,
                "单位": unit,
                "数量": number,
                "备注": ""
            })
    
    # 创建DataFrame
    if all_texts:
        df = pd.DataFrame(all_texts)
        
        # 重新排序列
        df = df[standard_columns]
        
        # 清理空行
        df = df.dropna(subset=["物料名称", "规格型号", "单位", "数量"], how="all")
        
        # 填充空值
        df = df.fillna("")
        
        # 按序号排序
        df["序号"] = pd.to_numeric(df["序号"], errors="coerce")
        df = df.sort_values("序号").reset_index(drop=True)
        df["序号"] = df["序号"].astype(str)
        
        return df
    else:
        # 返回空DataFrame
        return pd.DataFrame(columns=standard_columns)

async def test_ocr():
    # 创建OCR服务实例
    ocr_service = OCRService()
    
    # 测试图片路径
    image_path = "pricinglist-data/WechatIMG112.jpg"
    
    print(f"\n{'='*50}")
    print(f"测试图片: {image_path}")
    print(f"{'='*50}")
    
    try:
        # 创建OCR任务
        task_id = await ocr_service.create_task([image_path], [FileType.IMAGE])
        print(f"任务ID: {task_id}")
        
        # 等待任务完成
        while True:
            task = await ocr_service.get_task_status(task_id)
            if task.status in ['completed', 'failed']:
                break
            print("处理中...")
            await asyncio.sleep(1)
        
        # 输出结果
        if task.status == 'completed':
            print("\n识别成功!")
            
            # 格式化表格结果
            if task.result:
                df = format_table_result(task.result.cells, task.result.headers)
                
                # 输出原始识别结果
                print("\n原始识别文本:")
                for cell in task.result.cells:
                    print(f"文本: {cell.text:<50} | 置信度: {cell.confidence:.2f}")
                
                # 输出处理后的表格
                print("\n表格内容:")
                print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))
                
                # 输出置信度统计
                confidences = [cell.confidence for cell in task.result.cells]
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    print(f"\n置信度统计:")
                    print(f"平均置信度: {avg_conf:.2f}")
                    print(f"最高置信度: {max(confidences):.2f}")
                    print(f"最低置信度: {min(confidences):.2f}")
                
                # 保存为Excel文件
                output_dir = "ocr_results"
                os.makedirs(output_dir, exist_ok=True)
                excel_path = os.path.join(output_dir, f"ocr_result_{os.path.basename(image_path)}.xlsx")
                df.to_excel(excel_path, index=False)
                print(f"\n结果已保存至: {excel_path}")
            
        else:
            print(f"处理失败: {task.error_message}")
            
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ocr()) 