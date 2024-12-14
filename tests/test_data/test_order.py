import pandas as pd
import os

# 创建测试数据
data = {
    'material_name': ['卡箍', '沟槽大小头', '沟槽弯头'],
    'specification': ['DN100', 'DN100*80', 'DN80*65'],
    'quantity': [10, 5, 8],
    'unit': ['个', '个', '个']
}

# 创建DataFrame
df = pd.DataFrame(data)

# 保存为Excel文件
output_path = os.path.join(os.path.dirname(__file__), 'test_order.xlsx')
df.to_excel(output_path, index=False)
print(f"Test Excel file created at: {output_path}")
