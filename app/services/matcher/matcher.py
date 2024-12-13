import re
import logging
from typing import List, Optional, Dict
from rapidfuzz import fuzz
from app.models.material import MaterialBase, MaterialMatch
from app.core.database import Database, COLLECTIONS
from app.services.matcher.synonym_service import SynonymService

logger = logging.getLogger(__name__)

class MaterialMatcher:
    def __init__(self):
        self.db = Database.get_db()
        self.collection = self.db[COLLECTIONS["materials"]]
        self.min_confidence = 0.5
        self.synonym_service = SynonymService()

    async def match_material(self, text: str, spec: Optional[str] = None) -> MaterialMatch:
        """
        匹配物料信息

        参数:
            text: 物料名称文本
            spec: 规格型号（可选）

        返回:
            MaterialMatch对象
        """
        # 1. 尝试完全匹配
        exact_match = await self._exact_match(text)
        if exact_match:
            return MaterialMatch(
                original_text=text,
                matched_code=exact_match.material_code,
                confidence=1.0,
                match_type="exact",
                material_info=exact_match
            )

        # 2. 尝试分类限定匹配
        category_match = await self._category_match(text)
        if category_match:
            return MaterialMatch(
                original_text=text,
                matched_code=category_match.material_code,
                confidence=0.8,
                match_type="category",
                material_info=category_match
            )

        # 3. 尝试同义词匹配
        synonym_match = await self._synonym_match(text)
        if synonym_match:
            return MaterialMatch(
                original_text=text,
                matched_code=synonym_match.material_code,
                confidence=0.9,
                match_type="synonym",
                material_info=synonym_match
            )

        # 4. 如果有规格信息，尝试规格解析匹配
        if spec:
            spec_match = await self._spec_match(text, spec)
            if spec_match:
                return MaterialMatch(
                    original_text=text,
                    matched_code=spec_match.material_code,
                    confidence=0.7,
                    match_type="specification",
                    material_info=spec_match
                )

        # 5. 模糊匹配
        fuzzy_match = await self._fuzzy_match(text)
        if fuzzy_match:
            return MaterialMatch(
                original_text=text,
                matched_code=fuzzy_match["material_code"],
                confidence=fuzzy_match["confidence"],
                match_type="fuzzy",
                material_info=fuzzy_match["material"]
            )

        # 6. 没有找到匹配
        return MaterialMatch(
            original_text=text,
            matched_code="",
            confidence=0.0,
            match_type="none",
            material_info=None
        )

    async def _exact_match(self, text: str) -> Optional[MaterialBase]:
        """完全匹配"""
        doc = await self.collection.find_one({"material_name": text})
        if doc:
            return MaterialBase(**doc)
        return None

    async def _synonym_match(self, text: str) -> Optional[MaterialBase]:
        """同义词匹配"""
        # 使用同义词服务进行匹配
        synonym_group = await self.synonym_service.find_synonym(text, category="material_name")
        if synonym_group:
            # 获取关联的物料信息
            doc = await self.collection.find_one({"material_code": synonym_group.material_code})
            if doc:
                return MaterialBase(**doc)
        return None

    async def _spec_match(self, text: str, spec: str) -> Optional[MaterialBase]:
        """规格匹配"""
        # 1. 尝试精确规格匹配
        cursor = self.collection.find({
            "material_name": {"$regex": text, "$options": "i"},
            "specification": spec
        })
        async for doc in cursor:
            return MaterialBase(**doc)

        # 2. 尝试规格解析匹配
        parsed_spec = self._parse_specification(spec)
        if parsed_spec:
            cursor = self.collection.find({
                "material_name": {"$regex": text, "$options": "i"},
                "specification": {"$regex": parsed_spec, "$options": "i"}
            })
            async for doc in cursor:
                return MaterialBase(**doc)

        return None

    async def _fuzzy_match(self, text: str) -> Optional[Dict]:
        """模糊匹配"""
        best_match = None
        highest_ratio = 0

        cursor = self.collection.find({})
        async for doc in cursor:
            ratio = fuzz.ratio(text.lower(), doc["material_name"].lower())
            if ratio > highest_ratio and ratio >= 60:  # 60%的相似度阈值
                highest_ratio = ratio
                best_match = {
                    "material": MaterialBase(**doc),
                    "confidence": ratio / 100,
                    "material_code": doc["material_code"]
                }

        return best_match if highest_ratio >= 60 else None

    async def _category_match(self, text: str) -> Optional[MaterialBase]:
        """分类限定匹配"""
        # 从文本中提取可能的分类信息
        categories = self._extract_categories(text)
        if not categories:
            return None

        # 基于分类进行匹配
        for category in categories:
            cursor = self.collection.find({
                "material_name": {"$regex": text, "$options": "i"},
                "$or": [
                    {"category.level1": category},
                    {"category.level2": category}
                ]
            })
            try:
                async for doc in cursor:
                    material = MaterialBase(**doc)
                    return material
            except Exception as e:
                logger.error(f"分类匹配查询出错: {str(e)}")
                continue
        return None

    def _extract_categories(self, text: str) -> List[str]:
        """从文本中提取可能的分类信息"""
        categories = []
        # 常见物料分类关键词
        category_keywords = {
            "阀门": ["球阀", "闸阀", "蝶阀", "截止阀", "止回阀", "调节阀", "减压阀", "安全阀"],
            "管件": ["弯头", "三通", "四通", "变径", "接头", "管帽", "管箍"],
            "法兰": ["盲板", "法兰盘", "法兰片"],
            "紧固件": ["螺栓", "螺母", "垫片", "密封"],
            "仪表": ["压力表", "温度计", "流量计", "液位计"],
            "泵": ["离心泵", "往复泵", "螺杆泵", "隔膜泵"],
            "电气": ["电机", "开关", "继电器", "变频器"]
        }

        # 检查文本中是否包含分类关键词
        for main_category, sub_categories in category_keywords.items():
            if main_category in text:
                categories.append(main_category)
            for sub_category in sub_categories:
                if sub_category in text:
                    categories.append(main_category)
                    categories.append(sub_category)
                    break

        return list(set(categories))  # 去重

    def _parse_specification(self, spec: str) -> Optional[str]:
        """解析规格型号"""
        if not spec:
            return None

        # 移除常见的无意义词
        spec = re.sub(r'型号|规格|型|号', '', spec)

        # 统一格式化
        spec = re.sub(r'\s+', '', spec)  # 移除空白字符
        spec = spec.upper()  # 转换为大写

        # 处理常见的规格表示方式
        patterns = {
            # 1. 尺寸类
            r'DN(\d+)': r'DN\1',  # 公称通径
            r'PN(\d+)': r'PN\1',  # 压力等级
            r'G(\d+)': r'G\1',    # 螺纹规格
            r'(\d+)"': r'\1"',    # 英寸
            r'(\d+)(MM|MM2)': r'\1\2',  # 毫米

            # 2. 材质类
            r'(304L?|316L?|201|202|321)': r'\1',  # 不锈钢
            r'(Q235|Q345|20#|45#)': r'\1',  # 碳钢
            r'(HT200|QT400-18|ZG270-500)': r'\1',  # 铸铁

            # 3. 连接方式
            r'(法兰|螺纹|焊接|卡箍|快装)': r'\1',

            # 4. 驱动方式
            r'(电动|手动|气动|液动)': r'\1',

            # 5. 结构特征
            r'(单向|双向|单作用|双作用)': r'\1',
            r'(软密封|硬密封|金属密封)': r'\1'
        }

        # 应用所有模式
        for pattern, replacement in patterns.items():
            spec = re.sub(pattern, replacement, spec)

        return spec if spec else None     