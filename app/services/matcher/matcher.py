from typing import List, Optional, Dict
from rapidfuzz import fuzz
from app.models.material import MaterialBase, MaterialMatch
from app.core.database import Database, COLLECTIONS
from app.services.matcher.synonym_service import SynonymService

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

        # 2. 尝试同义词匹配
        synonym_match = await self._synonym_match(text)
        if synonym_match:
            return MaterialMatch(
                original_text=text,
                matched_code=synonym_match.material_code,
                confidence=0.9,
                match_type="synonym",
                material_info=synonym_match
            )

        # 3. 如果有规格信息，尝试规格匹配
        if spec:
            spec_match = await self._spec_match(text, spec)
            if spec_match:
                return MaterialMatch(
                    original_text=text,
                    matched_code=spec_match.material_code,
                    confidence=0.8,
                    match_type="specification",
                    material_info=spec_match
                )

        # 4. 模糊匹配
        fuzzy_match = await self._fuzzy_match(text)
        if fuzzy_match:
            return MaterialMatch(
                original_text=text,
                matched_code=fuzzy_match["material_code"],
                confidence=fuzzy_match["confidence"],
                match_type="fuzzy",
                material_info=fuzzy_match["material"]
            )

        # 5. 没有找到匹配
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
        cursor = self.collection.find({
            "material_name": {"$regex": text, "$options": "i"},
            "specification": spec
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