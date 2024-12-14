import pandas as pd
import json
from pathlib import Path

def analyze_material_list():
    # Read the Excel file
    excel_path = Path('/home/ubuntu/attachments/material-list-20241207.xlsx')
    df = pd.read_excel(excel_path)
    
    # Print basic information
    print("数据结构分析:")
    print("-" * 50)
    print(f"总行数: {len(df)}")
    print(f"列名: {df.columns.tolist()}")
    print("\n前5行数据示例:")
    print("-" * 50)
    print(df.head().to_string())
    
    # Analyze data types
    print("\n数据类型:")
    print("-" * 50)
    print(df.dtypes)

if __name__ == "__main__":
    analyze_material_list()
