import re
import logging
from typing import List, Optional, Dict, Tuple
from uuid import uuid4
from app.models.material import SynonymGroup, SynonymCreate, MaterialBase
from app.core.database import get_database, COLLECTIONS
from app.core.monitoring import monitor_performance
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

class SynonymService:
    """Service for managing material synonyms"""

    def __init__(self):
        self.db = None
        self.collection = None
        self.min_confidence = 0.5

    @classmethod
    async def create(cls):
        """Factory method to create a new SynonymService instance"""
        service = cls()
        service.db = await get_database()
        service.collection = service.db[COLLECTIONS["synonyms"]]
        return service

    @monitor_performance("create_synonym_group")
    async def create_synonym_group(self, synonym_data: SynonymCreate) -> SynonymGroup:
        """创建新的同义词组"""
        group = SynonymGroup(
            group_id=str(uuid4()),
            standard_name=synonym_data.standard_name,
            synonyms=list(set(synonym_data.synonyms)),  # 去重
            material_code=synonym_data.material_code,
            specification=synonym_data.specification,
            unit=synonym_data.unit,
            factory_price=synonym_data.factory_price,
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
                # 假设Excel数据格式为：标准名称、同义词（逗号分隔）、物料编码、规格型号、单位、厂价、类别
                synonyms = [s.strip() for s in row["synonyms"].split(",") if s.strip()]
                data = SynonymCreate(
                    standard_name=row["standard_name"],
                    synonyms=synonyms,
                    material_code=row["material_code"],
                    specification=row.get("specification"),
                    unit=row["unit"],
                    factory_price=row.get("factory_price"),
                    category=row.get("category", "material_name")
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

    def _extract_specification(self, text: str) -> Tuple[str, Optional[str]]:
        """提取规格信息"""
        if not text:
            return "", None

        # 规格模式
        spec_patterns = [
            r'DN\d+',  # DN规格
            r'\d+寸',   # 寸规格
            r'\d+mm',  # 毫米规格
            r'\d+inch' # 英寸规格
        ]

        # 尝试匹配所有规格模式
        for pattern in spec_patterns:
            match = re.search(pattern, text)
            if match:
                spec = match.group()
                # 移除规格信息得到基础名称
                base_name = text.replace(spec, '').strip()
                return base_name, spec

        return text, None

    @monitor_performance("find_synonym")
    async def find_synonym(self, text: str, category: str = "material_name") -> Optional[SynonymGroup]:
        """查找同义词"""
        try:
            logger.debug(f"查找同义词: text='{text}', category='{category}'")

            # 提取基础名称和规格
            base_name, spec = self._extract_specification(text)
            logger.debug(f"提取基础名称和规格: base_name='{base_name}', spec='{spec}'")

            # 1. 精确匹配
            exact_match = await self.collection.find_one({
                "synonyms": {"$regex": f"^{re.escape(text)}$", "$options": "i"},
                "category": category,
                "status": True
            })

            if exact_match:
                logger.info(f"找到精确匹配: {text} -> {exact_match['standard_name']}")
                return SynonymGroup(**exact_match)

            # 2. 基础名称匹配（不含规格）
            if base_name != text:
                base_match = await self.collection.find_one({
                    "$and": [
                        {"synonyms": {"$regex": f"^{re.escape(base_name)}$", "$options": "i"}},
                        {"category": category},
                        {"status": True}
                    ]
                })
                if base_match:
                    logger.info(f"找到基础名称匹配: {base_name} -> {base_match['standard_name']}")
                    return SynonymGroup(**base_match)

            # 3. 规格匹配
            if spec:
                spec_match = await self.collection.find_one({
                    "$and": [
                        {"synonyms": {"$regex": f".*{re.escape(base_name)}.*", "$options": "i"}},
                        {"specification": {"$regex": f".*{re.escape(spec)}.*", "$options": "i"}},
                        {"category": category},
                        {"status": True}
                    ]
                })
                if spec_match:
                    logger.info(f"找到规格匹配: {text} -> {spec_match['standard_name']}")
                    return SynonymGroup(**spec_match)

            # 4. 模糊匹配
            cursor = self.collection.find({
                "category": category,
                "status": True
            })

            best_match = None
            highest_score = 0

            async for doc in cursor:
                # 计算基础名称的相似度
                base_score = max(fuzz.token_sort_ratio(base_name, syn) for syn in doc["synonyms"])

                # 如果有规格，计算规格相似度
                spec_score = 100 if spec and doc.get("specification") and spec in doc["specification"] else 0

                # 综合评分：基础名称占70%，规格占30%
                total_score = base_score * 0.7 + spec_score * 0.3

                if total_score > highest_score:
                    highest_score = total_score
                    best_match = doc

            if best_match and highest_score >= 85:
                logger.info(f"找到模糊匹配: {text} -> {best_match['standard_name']} (分数: {highest_score})")
                return SynonymGroup(**best_match)

            logger.info(f"未找到同义词匹配: {text}")
            return None

        except Exception as e:
            logger.error(f"查找同义词出错: {str(e)}")
            return None

    @monitor_performance("find_fuzzy_synonym")
    async def find_fuzzy_synonym(self, text: str, category: str) -> Optional[SynonymGroup]:
        """模糊匹配同义词"""
        try:
            # 提取基础名称和规格
            base_name, spec = self._extract_specification(text)
            search_text = base_name if spec else text

            # 在指定类别中查找
            cursor = self.collection.find({
                "category": category,  # 只在指定类别中查找
                "status": True
            })

            best_match = None
            highest_ratio = 0

            async for group in cursor:
                # 检查标准名称
                standard_ratio = fuzz.token_sort_ratio(search_text.lower(),
                                                  group["standard_name"].lower())

                # 检查同义词
                synonym_ratios = [
                    fuzz.token_sort_ratio(search_text.lower(), syn.lower())
                    for syn in group["synonyms"]
                ]

                # 使用最高匹配分数
                max_ratio = max([standard_ratio] + synonym_ratios)

                # 如果有规格，检查规格是否匹配
                if spec and group.get("specification"):
                    if spec.upper() != group["specification"].upper():
                        continue

                # 更新最佳匹配
                if max_ratio > highest_ratio:
                    if max_ratio >= 90:  # 同义词匹配阈值
                        highest_ratio = max_ratio
                        best_match = group
                        logger.debug(f"更新最佳匹配: {text} -> {group['standard_name']} (分数: {max_ratio})")

            if best_match:
                logger.info(f"找到模糊匹配: {text} -> {best_match['standard_name']}")
                return SynonymGroup(**best_match)

            logger.info(f"未找到模糊匹配: {text}")
            return None

        except Exception as e:
            logger.error(f"模糊匹配出错: {str(e)}")
            return None

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

    # 2. 处理规格信息
    base_name = re.sub(r'DN\d+|\d+寸', '', name).strip()
    if base_name:
        synonyms.add(base_name)

        # 3. 添加规格变体
        if material.specification:
            # 空格变体
            synonyms.add(f"{base_name} {material.specification}")
            synonyms.add(f"{base_name}{material.specification}")

            # DN规格变体
            if 'DN' in material.specification.upper():
                dn_number = re.search(r'DN(\d+)', material.specification.upper())
                if dn_number:
                    number = dn_number.group(1)
                    synonyms.add(f"{base_name}DN{number}")
                    synonyms.add(f"{base_name} DN{number}")

            # 寸规格变体
            inch_match = re.search(r'(\d+)寸', material.specification)
            if inch_match:
                number = inch_match.group(1)
                synonyms.add(f"{base_name}{number}寸")
                synonyms.add(f"{base_name} {number}寸")

    # 4. 处理常见缩写和变体
    common_words = {
        "不锈钢": ["不锈", "SS"],
        "碳钢": ["CS"],
        "手动": ["手operated", "手动式"],
        "电动": ["电operated", "电动式"],
        "铸铁": ["cast iron", "铸铁制"],
        "法兰": ["法兰盘", "法兰片", "平面法兰"],
        "球阀": ["球型阀门", "球型阀"],
        "闸阀": ["闸式阀门", "闸式阀"],
        "蝶阀": ["蝶式阀门", "蝶式阀"],
        "止回阀": ["单向阀", "逆止阀"]
    }

    # 5. 生成变体
    for word, variants in common_words.items():
        if word in name:
            new_name = name
            for variant in variants:
                new_name = new_name.replace(word, variant)
                synonyms.add(new_name)
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
