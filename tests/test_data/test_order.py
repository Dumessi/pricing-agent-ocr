import pandas as pd
import os

# 创建测试数据
data = {
    '序号': [1, 2, 3],
    '物料名称': ['卡箍', '沟槽大小头', '沟槽弯头'],
    '规格型号': ['DN100', 'DN100*80', 'DN80*65'],
    '单位': ['个', '个', '个'],
    '数量': [100, 14, 14],
    '连接方式': ['钢卡', '卡簧', '卡簧']
}

# 创建DataFrame
df = pd.DataFrame(data)

# 确保目录存在
os.makedirs('tests/test_data', exist_ok=True)

# 保存为Excel文件
df.to_excel('tests/test_data/test_order.xlsx', index=False) 