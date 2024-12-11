from app.utils.excel_parser import read_and_process_excel
import pandas as pd
import json

# 读取并处理Excel文件
file_path = '/Users/dumessi/Library/Mobile Documents/com~apple~CloudDocs/macos-sharing/cursor-project/pricing-agent-ocr-dic/material-list/material-list-20241207.xlsx'
df = read_and_process_excel(file_path)

# 1. 基本统计
print('=== 基本统计 ===')
print(f'总行数：{len(df)}')

# 2. 分类统计
print('\n=== 分类统计 ===')
category_stats = df.groupby(['category_level1', 'category_level2']).size()
print(category_stats)

# 3. 规格型号统计
print('\n=== 规格型号统计 ===')
spec_count = df[df.specification != ""].shape[0]
empty_spec_count = df[df.specification == ""].shape[0]
print(f'有规格型号的物料数：{spec_count}')
print(f'规格为空的物料数：{empty_spec_count}')

# 4. 规格型号模式分析
print('\n=== 规格型号模式分析 ===')
spec_patterns = df[df.specification != ""].specification.value_counts().head(10)
print("最常见的规格型号：")
print(spec_patterns)

# 5. 生成示例数据用于导入
print('\n=== 生成示例数据 ===')
sample_data = df.head(5).to_dict('records')
print(json.dumps(sample_data, ensure_ascii=False, indent=2)) 