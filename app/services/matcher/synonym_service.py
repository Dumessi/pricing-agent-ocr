from typing import List, Optional, Dict
from uuid import uuid4
from app.models.material import SynonymGroup, SynonymCreate
from app.core.database import Database, COLLECTIONS
from app.core.monitoring import monitor_performance
from rapidfuzz import fuzz
import re

class SynonymService:
    def __init__(self):
        self.db = Database.get_db()
        self.collection = self.db[COLLECTIONS["synonyms"]]
        self.min_confidence = 0.8  # 同义词匹配的最小置信度

    @monitor_performance("create_synonym_group")
    async def create_synonym_group(self, synonym_data: SynonymCreate) -> SynonymGroup:
        """创建新的同义词组"""
        group = SynonymGroup(
            group_id=str(uuid4()),
            standard_name=synonym_data.standard_name,
            synonyms=list(set(synonym_data.synonyms)),  # 去重
            material_code=synonym_data.material_code,
            category=synonym_data.category,
            status=True
        )
        await self.collection.insert_one(group.model_dump())
        return group

    @monitor_performance("batch_create_synonyms")
    async def batch_create_synonyms(self, synonym_data_list: List[SynonymCreate]) -> List[SynonymGroup]:
        """批量创建同义词组"""
        groups = []
        for data in synonym_data_list:
            try:
                group = await self.create_synonym_group(data)
                groups.append(group)
            except Exception as e:
                print(f"Error creating synonym group for {data.standard_name}: {str(e)}")
        return groups

    @monitor_performance("import_from_excel")
    async def import_from_excel(self, excel_data: List[Dict]) -> List[SynonymGroup]:
        """从Excel数据导入同义词"""
        synonym_data_list = []
        for row in excel_data:
            try:
                # 假设Excel数据格式为：标准名称、同义词（逗号分隔）、物料编码、类别
                synonyms = [s.strip() for s in row["synonyms"].split(",") if s.strip()]
                data = SynonymCreate(
                    standard_name=row["standard_name"],
                    synonyms=synonyms,
                    material_code=row["material_code"],
                    category=row["category"]
                )
                synonym_data_list.append(data)
            except Exception as e:
                print(f"Error parsing row {row}: {str(e)}")
        
        return await self.batch_create_synonyms(synonym_data_list)

    @monitor_performance("get_synonym_group")
    async def get_synonym_group(self, group_id: str) -> Optional[SynonymGroup]:
        """获取同义词组"""
        doc = await self.collection.find_one({"group_id": group_id})
        return SynonymGroup(**doc) if doc else None

    @monitor_performance("update_synonym_group")
    async def update_synonym_group(self, group_id: str, synonyms: List[str]) -> Optional[SynonymGroup]:
        """更新同义词组"""
        result = await self.collection.update_one(
            {"group_id": group_id},
            {"$set": {"synonyms": list(set(synonyms))}}  # 去重
        )
        if result.modified_count:
            return await self.get_synonym_group(group_id)
        return None

    @monitor_performance("delete_synonym_group")
    async def delete_synonym_group(self, group_id: str) -> bool:
        """删除同义词组"""
        result = await self.collection.delete_one({"group_id": group_id})
        return bool(result.deleted_count)

    @monitor_performance("find_synonym")
    async def find_synonym(self, text: str, category: Optional[str] = None) -> Optional[SynonymGroup]:
        """查找同义词匹配"""
        if not text.strip():  # 处理空字符串
            return None
            
        # 1. 尝试精确匹配
        query = {"status": True}
        if category:
            query["category"] = category

        # 检查是否是标准名称
        doc = await self.collection.find_one({
            **query,
            "standard_name": text
        })
        if doc:
            return SynonymGroup(**doc)

        # 检查是否在同义词列表中
        doc = await self.collection.find_one({
            **query,
            "synonyms": text
        })
        if doc:
            return SynonymGroup(**doc)

        # 2. 尝试模糊匹配
        best_match = None
        highest_ratio = 0
        
        cursor = self.collection.find(query)
        async for doc in cursor:
            # 检查标准名称
            ratio = fuzz.ratio(text.lower(), doc["standard_name"].lower())
            if ratio > highest_ratio and ratio >= self.min_confidence * 100:
                highest_ratio = ratio
                best_match = doc
                continue

            # 检查同义词列表
            for synonym in doc["synonyms"]:
                ratio = fuzz.ratio(text.lower(), synonym.lower())
                if ratio > highest_ratio and ratio >= self.min_confidence * 100:
                    highest_ratio = ratio
                    best_match = doc
                    break

        return SynonymGroup(**best_match) if best_match else None

    @monitor_performance("get_all_synonyms")
    async def get_all_synonyms(self, category: Optional[str] = None) -> List[SynonymGroup]:
        """获取所有同义词组"""
        query = {"status": True}
        if category:
            query["category"] = category
            
        cursor = self.collection.find(query)
        groups = []
        async for doc in cursor:
            groups.append(SynonymGroup(**doc))
        return groups

def generate_material_synonyms(material: MaterialBase) -> list:
    """生成物料名称的同义词"""
    synonyms = set()
    name = material.material_name
    
    # 1. 添加原始名称
    synonyms.add(name)
    
    # 2. 常见缩写和变体
    replacements = {
        # 阀门类
        "阀门": ["阀", "闸阀", "阀体"],
        "球阀": ["球形阀", "球型阀", "球"],
        "闸阀": ["闸门", "闸", "闸式阀门"],
        "蝶阀": ["蝶形阀", "蝶式阀", "蝶"],
        "截止阀": ["截止", "截流阀"],
        "止回阀": ["单向阀", "逆止阀", "止逆阀"],
        "调节阀": ["调节", "调控阀"],
        "减压阀": ["减压器", "调压阀"],
        "安全阀": ["泄压阀", "安全泄压阀"],
        
        # 管件类
        "管件": ["管配件", "配件"],
        "弯头": ["弯管", "弯", "弯接"],
        "三通": ["T型管", "三叉", "三岔"],
        "四通": ["十字管", "四叉", "四岔"],
        "变径": ["异径", "大小头", "异径管"],
        "接头": ["连接头", "接口", "连接器"],
        "管帽": ["堵头", "封头"],
        "管箍": ["套管", "管套"],
        
        # 法兰类
        "法兰": ["凸缘", "法兰盘", "法兰片"],
        "盲板": ["盲法兰", "堵板"],
        
        # 紧固件
        "螺栓": ["螺丝", "螺丝钉"],
        "螺母": ["螺帽", "六角螺母"],
        "垫片": ["垫圈", "密封垫"],
        "密封": ["密封圈", "密封垫", "密封件"],
        
        # 其他
        "补偿器": ["膨胀节", "伸缩节", "补偿管"],
        "过滤器": ["过滤", "滤", "过滤装置"],
        
        # 驱动方式
        "电动": ["电动式", "电动型", "电气动"],
        "手动": ["手动式", "手动型", "手扳"],
        "气动": ["气动式", "气动型", "气压式"],
        "液动": ["液动式", "液动型", "液压式"],
        
        # 新增的同义词映射
        "直通": ["管古"],
        "内接": ["同径外丝"],
        "堵头": ["管堵"],
        "活接": ["油任"],
        "侧大四通": ["三变四通"],
        "侧大三通": ["三变三通"],
        "补芯": ["补心"],
        "内外牙弯头": ["内外丝弯头"],
        "内外牙直通": ["内外丝管古"],
        "刚卡": ["刚性卡箍"],
        "挠卡": ["挠性卡箍"],
        "机三S": ["螺纹机械三通"],
        "机三G": ["沟槽机械三通"],
        "机四S": ["螺纹机械四通"],
        "机四G": ["沟槽机械四通"],
        "转换法兰": ["法兰短管"],
        "异径三通S": ["沟槽螺纹异径三通"],
        "异径三通G": ["沟槽异径三通"],
        "异径四通S": ["沟槽螺纹异径四通"],
        "异径四通G": ["沟槽异径四通"],
        "机三下片": ["机械三通底座"],
        "偏心大小头": ["偏心异径管箍"],
        "大小头G": ["异径管箍"],
        "大小头S": ["螺纹异径管箍"]
    }
    
    # 处理替换
    for key, values in replacements.items():
        if key in name:
            base_name = name
            # 处理品牌信息
            brand_match = re.search(r'\((.*?)\)', name)
            if brand_match:
                brand = brand_match.group(1)
                base_name = name.replace(f"({brand})", "").strip()
            
            # 生成变体
            for value in values:
                new_name = base_name.replace(key, value)
                synonyms.add(new_name)
                # 如果有品牌，也生成带品牌的变体
                if brand_match:
                    synonyms.add(f"{new_name}({brand})")
                    synonyms.add(f"{brand}{new_name}")
    
    # 3. 处理品牌信息
    brand_match = re.search(r'\((.*?)\)', name)
    if brand_match:
        brand = brand_match.group(1)
        # 添加不带品牌的名称
        clean_name = name.replace(f"({brand})", "").strip()
        synonyms.add(clean_name)
        # 添加品牌在前面的变体
        synonyms.add(f"{brand}{clean_name}")
        # 添加不同格式的品牌标注
        synonyms.add(f"{clean_name}-{brand}")
        synonyms.add(f"{clean_name}/{brand}")
    
    # 4. 添加类别相关的同义词
    if material.category:
        if "level2" in material.category:
            category_name = material.category["level2"].replace("类", "")
            synonyms.add(f"{category_name}{name}")
            # 如果有品牌，也生成不带品牌的类别同义词
            if brand_match:
                synonyms.add(f"{category_name}{clean_name}")
    
    # 5. 添加材质相关的同义词
    if material.attributes and "material" in material.attributes:
        material_type = material.attributes["material"]
        synonyms.add(f"{material_type}{name}")
        # 处理常见材质缩写
        material_mapping = {
            "不锈钢": ["SS", "304", "316", "316L", "201", "202", "321", "2520"],
            "碳钢": ["CS", "Q235", "20#", "45#", "A3", "碳素钢", "普通钢"],
            "铸铁": ["Cast Iron", "HT200", "QT400", "QT500", "灰铸铁", "球墨铸铁"],
            "铸钢": ["Cast Steel", "WCB", "ZG230-450", "ZG270-500"],
            "铜": ["Brass", "Bronze", "Cu", "紫铜", "黄铜", "青铜"],
            "塑料": ["PP", "PE", "PVC", "UPVC", "CPVC", "ABS", "PPR", "HDPE"],
            "铝": ["Al", "铝合金", "ADC12", "A356"],
            "合金钢": ["Alloy Steel", "35CrMo", "42CrMo", "40Cr", "合金"],
            "双相钢": ["2205", "2507", "S31803", "S32750"],
            "镍基合金": ["Inconel", "因科镍", "哈氏合金", "Hastelloy"]
        }
        
        # 添加材质变体
        for std_material, variants in material_mapping.items():
            if std_material in material_type:
                for variant in variants:
                    synonyms.add(f"{variant}{clean_name}")
                    # 添加带连接方式的变体
                    if "连接方式" in material.attributes:
                        conn_type = material.attributes["连接方式"]
                        synonyms.add(f"{variant}{conn_type}{clean_name}")

    # 6. 处理规格相关的同义词
    if material.specification:
        spec = material.specification.upper()
        
        # DN系列处理
        if "DN" in spec:
            base_name = name.replace(spec, "").strip()
            number = re.search(r'\d+', spec)
            if number:
                num = number.group()
                # 基本变体
                synonyms.add(f"{base_name}{num}")
                synonyms.add(f"{base_name}DN{num}")
                synonyms.add(f"{base_name}D{num}")
                synonyms.add(f"{base_name}Φ{num}")
                
                # 添加公制和英制转换
                try:
                    mm = int(num)
                    inch = round(mm / 25.4, 1)
                    if inch.is_integer():
                        inch = int(inch)
                    # 英制表示
                    synonyms.add(f"{base_name}{inch}\"")
                    synonyms.add(f"{base_name}{inch}寸")
                    # 公制表示
                    synonyms.add(f"{base_name}{mm}mm")
                    synonyms.add(f"{base_name}{mm}毫米")
                    # 特殊表示
                    if inch == 0.5:
                        synonyms.add(f"{base_name}1/2寸")
                    elif inch == 0.75:
                        synonyms.add(f"{base_name}3/4寸")
                    elif inch == 1.25:
                        synonyms.add(f"{base_name}1-1/4寸")
                    elif inch == 1.5:
                        synonyms.add(f"{base_name}1-1/2寸")
                except:
                    pass

        # 处理压力等级
        pressure_classes = {
            "PN": ["#", "CLASS", "级", "公斤"],
            "CLASS": ["CL", "级", "磅级"],
            "KG": ["公斤", "KG/CM2", "kg/cm²"]
        }
        for std_class, variants in pressure_classes.items():
            if std_class in spec:
                pressure_num = re.search(r'\d+', spec)
                if pressure_num:
                    num = pressure_num.group()
                    for variant in variants:
                        synonyms.add(f"{base_name}{variant}{num}")
                        synonyms.add(f"{base_name} {variant}{num}")

    # 7. 处理连接方式相关的同义词
    if material.attributes and "连接方式" in material.attributes:
        conn_type = material.attributes["连接方式"]
        connection_mapping = {
            "法兰": ["FF", "RF", "带颈对焊", "WN", "SO", "SW", "承插焊"],
            "螺纹": ["丝扣", "NPT", "PT", "BSPT", "RC", "RP", "G螺纹", "英制螺纹"],
            "焊接": ["对焊", "承插焊", "BW", "SW", "套焊"],
            "卡箍": ["卡套", "卡扣", "快装", "卡盘", "抱箍"],
            "沟槽": ["槽接", "沟槽式", "GROOVE", "GR"],
            "承插": ["插接", "套接", "承插式"],
            "压接": ["压扣", "压装", "卡压"],
            "活接": ["活动连接", "活动接头", "活接头"]
        }
        
        # 添加连接方式变体
        for std_conn, variants in connection_mapping.items():
            if std_conn in conn_type:
                for variant in variants:
                    synonyms.add(f"{variant}{clean_name}")
                    # 添加带材质的变体
                    if "material" in material.attributes:
                        material_type = material.attributes["material"]
                        synonyms.add(f"{material_type}{variant}{clean_name}")

    # 8. 处理常见缩写和简写
    abbreviations = {
        "不锈钢": "不锈",
        "碳钢": "碳",
        "铸铁": "铸",
        "螺纹": "丝",
        "法兰": "法",
        "活接": "活",
        "承插": "承",
        "焊接": "焊",
        "压力": "压",
        "温度": "温",
        "直通": "直",
        "弯头": "弯",
        "三通": "三",
        "四通": "四",
        "异径": "异",
        "内丝": "内",
        "外丝": "外"
    }
    
    # 处理缩写
    for full, abbr in abbreviations.items():
        if full in name:
            new_name = name.replace(full, abbr)
            synonyms.add(new_name)
            # 如果有规格，也生成带规格的缩写形式
            if material.specification:
                synonyms.add(f"{new_name} {material.specification}")
                synonyms.add(f"{new_name}{material.specification}")
    
    return list(synonyms)

def generate_specification_synonyms(specification: str) -> list:
    """生成规格型号的同义词"""
    if not specification:
        return []
        
    synonyms = set()
    spec = specification.upper()
    
    # 1. 添加原始规格
    synonyms.add(spec)
    
    # 2. DN系列处理
    if spec.startswith("DN"):
        # 添加空格变体：DN100 -> DN 100
        synonyms.add(spec.replace("DN", "DN "))
        # 添加D变体：DN100 -> D100
        synonyms.add(spec.replace("DN", "D"))
        # 添加直径变体：DN100 -> Φ100
        synonyms.add(spec.replace("DN", "Φ"))
        # 添加数字变体：DN100 -> 100
        number = re.search(r'\d+', spec)
        if number:
            num = number.group()
            synonyms.add(num)
            synonyms.add(f"{num}mm")
            # 添加英制转换
            try:
                mm = int(num)
                inch = round(mm / 25.4, 1)
                if inch.is_integer():
                    inch = int(inch)
                synonyms.add(f"{inch}\"")
                synonyms.add(f"{inch}寸")
            except:
                pass
    
    # 3. 处理乘号变体
    if "*" in spec or "×" in spec or "X" in spec:
        variants = [
            spec.replace("*", "×"),
            spec.replace("*", "X"),
            spec.replace("×", "*"),
            spec.replace("×", "X"),
            spec.replace("X", "*"),
            spec.replace("X", "×")
        ]
        synonyms.update(variants)
        
        # 处理带空格的变体
        for variant in variants:
            synonyms.add(variant.replace("*", " * "))
            synonyms.add(variant.replace("×", " × "))
            synonyms.add(variant.replace("X", " X "))
    
    # 4. 处理带空格的变体
    if not " " in spec:
        # 在字母和数字之间添加空格
        spaced_spec = re.sub(r'([A-Za-z])(\d)', r'\1 \2', spec)
        if spaced_spec != spec:
            synonyms.add(spaced_spec)
    
    # 5. 处理单位变体
    units = {
        "MM": ["mm", "毫米", "㎜"],
        "M": ["米", "m"],
        "INCH": ["寸", "\"", "英寸"],
        "KG": ["kg", "公斤", "千克"],
        "G": ["g", "克"],
        "L": ["l", "升", "㎡"],
        "ML": ["ml", "毫升", "㎖"]
    }
    
    for std_unit, variants in units.items():
        if std_unit in spec:
            base_spec = spec.replace(std_unit, "").strip()
            for variant in variants:
                synonyms.add(f"{base_spec}{variant}")
                synonyms.add(f"{base_spec} {variant}")
    
    return list(synonyms)