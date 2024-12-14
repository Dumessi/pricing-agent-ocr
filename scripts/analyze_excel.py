"""
分析Excel文件结构
"""
import pandas as pd
import os

def analyze_excel():
    """分析Excel文件结构和内容"""
    print("开始分析Excel文件...")

    excel_path = os.path.expanduser("~/attachments/material-list-20241207.xlsx")
    df = pd.read_excel(excel_path)

    print("\n=== Excel文件基本信息 ===")
    print(f"总行数: {len(df)}")
    print(f"总列数: {len(df.columns)}")
    print("\n列名:")
    for col in df.columns:
        print(f"- {col}")

    print("\n=== 样本数据 ===")
    print(df.head().to_string())

    print("\n=== 数据统计 ===")
    for col in df.columns:
        null_count = df[col].isnull().sum()
        print(f"\n列 '{col}':")
        print(f"- 空值数量: {null_count}")
        print(f"- 空值比例: {(null_count/len(df))*100:.2f}%")
        if df[col].dtype == 'object':
            print(f"- 唯一值数量: {df[col].nunique()}")
            print("- 样本值:")
            for val in df[col].dropna().head(3).values:
                print(f"  * {val}")

if __name__ == "__main__":
    analyze_excel()
