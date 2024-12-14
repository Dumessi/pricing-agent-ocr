import re
import logging
from typing import Optional, List, Dict, Tuple
from rapidfuzz import fuzz
from app.models.material import MaterialBase, MaterialMatch
from app.core.database import get_database, COLLECTIONS
from app.services.matcher.synonym_service import SynonymService

logger = logging.getLogger(__name__)

class MaterialMatcher:
    def __init__(self):
        """初始化物料匹配器"""
        self.db = None
        self.collection = None
        self.synonym_service = None

    @classmethod
    async def create(cls) -> 'MaterialMatcher':
        """Factory method to create a new MaterialMatcher instance"""
        matcher = cls()
        matcher.db = await get_database()
        matcher.collection = matcher.db[COLLECTIONS["materials"]]
        matcher.synonym_service = await SynonymService.create()
        return matcher

    async def match_material(self, text: str, spec: str = None) -> MaterialMatch:
        """匹配物料"""
        try:
            logger.debug(f"开始匹配物料: {text}")
            if not text or not isinstance(text, str):
                return MaterialMatch(
                    original_text=text or "",
                    matched_code="",
                    confidence=0.0,
                    match_type="none",
                    material_info=MaterialBase(
                        material_code="",
                        material_name="",
                        unit="个"  # 默认单位
                    )
                )

            # 1. 精确匹配
            exact_match = await self._exact_match(text)
            if exact_match and exact_match.confidence >= 0.85:  # Lowered from 0.9
                logger.info(f"找到精确匹配: {text} -> {exact_match.material_info.material_name}")
                return exact_match

            # 2. 提取规格信息（如果没有提供规格参数）
            if spec is None:
                base_name, extracted_spec = self._extract_specification(text)
                spec = extracted_spec
            else:
                base_name = text

            # 3. 规格匹配（如果有规格信息）
            if spec:
                spec_match = await self._specification_match(base_name, spec)
                if spec_match and spec_match.confidence >= 0.75:  # Lowered from 0.85
                    logger.info(f"找到规格匹配: {text} -> {spec_match.material_info.material_name}")
                    return spec_match

            # 4. 同义词匹配
            synonym_match = await self._synonym_match(text)
            if synonym_match and synonym_match.confidence >= 0.75:  # Lowered from 0.85
                logger.info(f"找到同义词匹配: {text} -> {synonym_match.material_info.material_name}")
                return synonym_match

            # 5. 类别匹配
            category_match = await self._category_match(text)
            if category_match and category_match.confidence >= 0.7:  # Lowered from 0.8
                logger.info(f"找到类别匹配: {text} -> {category_match.material_info.material_name}")
                return category_match

            # 6. 模糊匹配（作为最后的尝试）
            fuzzy_match = await self._fuzzy_match(text)
            if fuzzy_match and fuzzy_match.confidence >= 0.6:  # Lowered from 0.7
                logger.info(f"找到模糊匹配: {text} -> {fuzzy_match.material_info.material_name}")
                return fuzzy_match

            logger.info(f"未找到匹配: {text}")
            return MaterialMatch(
                original_text=text,
                matched_code="",
                confidence=0.0,
                match_type="none",
                material_info=MaterialBase(
                    material_code="",
                    material_name="",
                    unit="个"  # 默认单位
                )
            )

        except Exception as e:
            logger.error(f"匹配物料出错: {str(e)}")
            return MaterialMatch(
                original_text=text,
                matched_code="",
                confidence=0.0,
                match_type="error",
                material_info=MaterialBase(
                    material_code="",
                    material_name="",
                    unit="个"  # 默认单位
                )
            )

    async def _exact_match(self, text: str) -> Optional[MaterialMatch]:
        """精确匹配"""
        try:
            collection = self.db[COLLECTIONS["materials"]]
            # 尝试直接匹配
            material = await collection.find_one({
                "material_name": {"$regex": f"^{re.escape(text)}$", "$options": "i"},
                "status": True
            })

            if material:
                material_base = MaterialBase(**material)
                logger.info(f"找到精确匹配: {text} -> {material_base.material_name}")
                return MaterialMatch(
                    original_text=text,
                    matched_code=material_base.material_code,
                    confidence=1.0,
                    match_type="exact",
                    material_info=material_base
                )

            return None

        except Exception as e:
            logger.error(f"精确匹配出错: {str(e)}")
            return None

    async def _synonym_match(self, text: str) -> Optional[MaterialMatch]:
        """同义词匹配"""
        try:
            # 查找同义词
            synonym_group = await self.synonym_service.find_synonym(text)
            if not synonym_group:
                return None

            # 使用同义词组中的物料编码查找物料信息
            collection = self.db[COLLECTIONS["materials"]]
            material = await collection.find_one({
                "material_code": synonym_group.material_code,
                "status": True
            })

            if not material:
                logger.warning(f"同义词组 {synonym_group.group_id} 对应的物料编码 {synonym_group.material_code} 未找到")
                return None

            # 计算置信度
            confidence = fuzz.token_sort_ratio(text, synonym_group.standard_name) / 100.0

            # 创建物料匹配结果
            logger.info(f"找到同义词匹配: {text} -> {material['material_name']}")
            return MaterialMatch(
                original_text=text,
                matched_code=material["material_code"],
                confidence=confidence,
                match_type="synonym",
                material_info=MaterialBase(
                    material_code=material["material_code"],
                    material_name=material["material_name"],
                    specification=material.get("specification", ""),
                    unit=material.get("unit", "个"),
                    factory_price=material.get("factory_price", 0.0)
                )
            )

        except Exception as e:
            logger.error(f"同义词匹配出错: {str(e)}")
            return None

    async def _specification_match(self, base_name: str, spec: str) -> Optional[MaterialMatch]:
        """规格匹配"""
        try:
            collection = self.db[COLLECTIONS["materials"]]

            # 构建查询条件
            query = {
                "$and": [
                    {
                        "$or": [
                            {"material_name": {"$regex": f".*{base_name}.*", "$options": "i"}},
                            {"specification": {"$regex": f".*{base_name}.*", "$options": "i"}}
                        ]
                    },
                    {
                        "$or": [
                            {"material_name": {"$regex": f".*{spec}.*", "$options": "i"}},
                            {"specification": {"$regex": f".*{spec}.*", "$options": "i"}}
                        ]
                    },
                    {"status": True}
                ]
            }

            # 查找匹配的物料
            materials = await collection.find(query).to_list(None)

            if not materials:
                return None

            # 计算最佳匹配
            best_match = None
            best_score = 0.0

            for material in materials:
                # 计算匹配分数
                name_score = self._calculate_similarity(base_name, material["material_name"])
                spec_score = self._calculate_similarity(spec, material.get("specification", ""))

                # 综合评分
                total_score = (name_score * 0.7 + spec_score * 0.3)

                if total_score > best_score:
                    best_score = total_score
                    best_match = material

            if best_match and best_score >= 0.85:
                logger.info(f"找到规格匹配: {base_name} -> {best_match['material_name']}")
                return MaterialMatch(
                    original_text=f"{base_name}{spec}",
                    matched_code=best_match["material_code"],
                    confidence=best_score,
                    match_type="specification",
                    material_info=MaterialBase(**best_match)
                )

            return None

        except Exception as e:
            logger.error(f"规格匹配出错: {str(e)}")
            return None

    async def _fuzzy_match(self, text: str) -> Optional[MaterialMatch]:
        """模糊匹配"""
        try:
            collection = self.db[COLLECTIONS["materials"]]
            cursor = collection.find({"status": True})
            best_match = None
            highest_ratio = 0

            # 清理输入文本
            clean_text = text.lower().strip()

            async for material in cursor:
                # 计算相似度
                ratio = fuzz.token_sort_ratio(clean_text, material["material_name"].lower())

                # 如果找到更好的匹配
                if ratio > highest_ratio and ratio >= 85:  # 提高模糊匹配阈值
                    highest_ratio = ratio
                    best_match = material

            if best_match:
                material = MaterialBase(**best_match)
                return MaterialMatch(
                    original_text=text,
                    matched_code=material.material_code,
                    confidence=highest_ratio / 100,
                    match_type="fuzzy",
                    material_info=material
                )

            return None

        except Exception as e:
            logger.error(f"模糊匹配出错: {str(e)}")
            return None

    async def _category_match(self, text: str) -> Optional[MaterialMatch]:
        """类别匹配"""
        try:
            # 提取基础名称和规格信息
            base_name, spec = self._extract_specification(text)
            categories = self._extract_categories(base_name)  # 移除 await

            if not categories:
                return None

            logger.debug(f"类别匹配: text='{text}', base_name='{base_name}', categories={categories}")

            # 在物料集合中查找匹配项
            collection = self.db[COLLECTIONS["materials"]]
            best_match = None
            highest_score = 0

            # 对每个类别进行匹配（按类别长度排序以优先处理更具体的类别）
            for category in sorted(categories, key=len, reverse=True):
                cursor = collection.find({
                    "material_name": {"$regex": f".*{category}.*", "$options": "i"},
                    "status": True
                })

                async for material in cursor:
                    # 计算相似度分数
                    score = fuzz.token_sort_ratio(base_name, material["material_name"])

                    # 如果输入文本完全匹配类别，增加匹配分数
                    if category == base_name:
                        score += 20

                    # 如果有规格信息，增加规格匹配分数
                    if spec and "specification" in material:
                        if spec.upper() == material["specification"].upper():
                            score += 15
                        elif spec in material["specification"] or material["specification"] in spec:
                            score += 10

                    if score > highest_score:
                        highest_score = score
                        best_match = material

            if best_match and highest_score >= 70:  # 添加最低匹配阈值
                material_base = MaterialBase(**best_match)
                if not material_base.unit:
                    material_base.unit = "个"  # 默认单位

                logger.info(f"找到类别匹配: {text} -> {material_base.material_name}")
                return MaterialMatch(
                    original_text=text,
                    matched_code=material_base.material_code,
                    confidence=highest_score / 100,
                    match_type="category",  # 确保返回类别匹配类型
                    material_info=material_base
                )

            return None

        except Exception as e:
            logger.error(f"类别匹配出错: {str(e)}")
            return None

    def _extract_categories(self, text: str) -> List[str]:
        """提取分类关键词"""
        # 基础物料类型
        base_categories = ["阀", "法兰", "管件", "管材", "水泵", "仪表", "阀门"]

        # 具体阀门类型（按长度排序以确保优先匹配更具体的类型）
        valve_categories = sorted([
            "闸阀", "球阀", "蝶阀", "止回阀", "调节阀", "截止阀",
            "减压阀", "安全阀", "电磁阀", "疏水阀", "排气阀"
        ], key=len, reverse=True)

        # 材质类型
        material_categories = ["铸铁", "不锈钢", "碳钢", "铜", "铝", "塑料", "PVC"]

        # 连接方式
        connection_categories = ["法兰式", "螺纹", "焊接", "卡箍", "对夹"]

        # 所有类别组合（优先匹配具体类型）
        all_categories = valve_categories + base_categories + material_categories + connection_categories

        # 查找匹配的类别（返回最长匹配）
        found_categories = []
        remaining_text = text
        for category in all_categories:
            if category in remaining_text:
                found_categories.append(category)
                remaining_text = remaining_text.replace(category, '')  # 移除已匹配部分

        return found_categories

    def _extract_specification(self, text: str) -> Tuple[str, Optional[str]]:
        """提取规格信息"""
        try:
            # 常见规格前缀
            spec_prefixes = ["DN", "PN", "D", "φ"]

            # 查找规格信息
            for prefix in spec_prefixes:
                pattern = f"{prefix}\\d+(?:[-.×x]\\d+)?"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    spec = match.group(0)
                    base_name = text.replace(spec, "").strip()
                    return base_name, spec

            # 尝试提取数字规格（如：100mm）
            pattern = r"\d+(?:[-.×x]\d+)?(?:mm|m|inch|\")"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                spec = match.group(0)
                base_name = text.replace(spec, "").strip()
                return base_name, spec

            # 如果没有找到规格信息
            return text, None

        except Exception as e:
            logger.error(f"提取规格信息出错: {str(e)}")
            return text, None

    def _remove_specification(self, text: str) -> str:
        """移除规格信息"""
        try:
            # 规格模式匹配和移除
            patterns = [
                r'DN\d+',           # DN规格
                r'\d+寸',           # 寸规格
                r'\d+mm',           # 毫米规格
                r'\d+(?:inch|")',   # 英寸规格
                r'[A-Z]\d+',        # 字母数字组合规格
                r'PN\d+',           # PN规格
                r'\d+×\d+',         # 尺寸规格
                r'\d+\*\d+'         # 尺寸规格（使用*）
            ]

            cleaned_text = text
            for pattern in patterns:
                cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)

            # 清理多余的空格和标点
            cleaned_text = re.sub(r'[\s\-_]+', ' ', cleaned_text)
            cleaned_text = cleaned_text.strip()

            return cleaned_text or text  # 如果清理后为空，返回原文本

        except Exception as e:
            logger.error(f"移除规格信息出错: {str(e)}")
            return text                                                                 