import pandas as pd
from typing import Dict, List
import re

class ExcelParser:
    @staticmethod
    def preview_excel(file_path: str) -> Dict:
        """预览Excel文件内容"""
        df = pd.read_excel(file_path)
        return {
            "columns": list(df.columns),
            "sample_rows": df.head().to_dict('records'),
            "total_rows": len(df)
        }

    @staticmethod
    def extract_specification_from_name(name: str) -> tuple:
        """从名称中提取规格信息"""
        # 匹配DN+数字的模式
        dn_pattern = r'DN\d+(?:\*\d+)?'
        dn_match = re.search(dn_pattern, name)
        
        # 如果在括号中有规格信息
        bracket_pattern = r'\((.*?)\)'
        bracket_match = re.search(bracket_pattern, name)
        
        spec = ""
        clean_name = name
        
        if dn_match:
            spec = dn_match.group()
            clean_name = name.replace(spec, '').strip()
        elif bracket_match:
            bracket_content = bracket_match.group(1)
            if any(char.isdigit() for char in bracket_content):  # 如果括号内容包含数字，可能是规格
                spec = bracket_content
                clean_name = name.replace(f"({spec})", '').strip()
        
        return clean_name, spec

    @staticmethod
    def map_columns(df: pd.DataFrame) -> pd.DataFrame:
        """映射列名到标准格式"""
        # 基本映射
        column_mapping = {
            '编码': 'material_code',
            '名称': 'material_name',
            '规格型号': 'specification',
            '基本单位': 'unit',
            '厂价': 'attr_price'
        }
        
        # 重命名存在的列
        existing_columns = {old: new for old, new in column_mapping.items() if old in df.columns}
        df = df.rename(columns=existing_columns)
        
        # 处理规格型号为空的情况，从名称中提取
        if 'specification' in df.columns:
            df['specification'] = df['specification'].fillna('')
            mask = df['specification'] == ''
            extracted = df.loc[mask, 'material_name'].apply(ExcelParser.extract_specification_from_name)
            df.loc[mask, 'material_name'] = extracted.apply(lambda x: x[0])
            df.loc[mask, 'specification'] = extracted.apply(lambda x: x[1])
        
        # 处理物料名称
        df['material_name'] = df['material_name'].str.strip()
        
        # 添加智能分类
        def get_category(name: str) -> tuple:
            # 常见物料类别映射
            categories = {
                '阀': ('管道系统', '阀门类'),
                '泵': ('机械设备', '泵类'),
                '管': ('管道系统', '管件类'),
                '螺': ('紧固件', '螺栓类'),
                '法兰': ('管道系统', '法兰类'),
                '接头': ('管道系统', '接头类'),
                '传感': ('仪器仪表', '传感器'),
                '仪表': ('仪器仪表', '仪表类'),
                '电机': ('机械设备', '电机类'),
                '开关': ('电气设备', '开关类'),
                '电缆': ('电气设备', '电缆类'),
                '线缆': ('电气设备', '电缆类'),
                '报警': ('消防系统', '报警设备'),
                '喷淋': ('消防系统', '喷淋设备'),
                '消防': ('消防系统', '消防设备'),
                '灭火': ('消防系统', '灭火设备')
            }
            
            for key, value in categories.items():
                if key in name:
                    return value
            return ('其他设备', '其他')

        # 添加分类列
        df['category_temp'] = df['material_name'].apply(get_category)
        df['category_level1'] = df['category_temp'].apply(lambda x: x[0])
        df['category_level2'] = df['category_temp'].apply(lambda x: x[1])
        df = df.drop('category_temp', axis=1)
        
        # 处理价格列
        if 'attr_price' in df.columns:
            df['attr_price'] = df['attr_price'].fillna(0).astype(float)
        
        # 确保所有必要的列都存在
        required_columns = ['material_code', 'material_name', 'specification', 'unit', 
                          'category_level1', 'category_level2']
        for col in required_columns:
            if col not in df.columns:
                df[col] = ''
        
        return df

    def parse_excel(self, file_path: str) -> pd.DataFrame:
        """读取并处理Excel文件"""
        df = pd.read_excel(file_path)
        return self.map_columns(df)

# 为了向后兼容，保留原有的函数接口
def read_and_process_excel(file_path: str) -> pd.DataFrame:
    """读取并处理Excel文件（兼容旧接口）"""
    parser = ExcelParser()
    return parser.parse_excel(file_path)

__all__ = ['ExcelParser', 'read_and_process_excel']