from typing import List, Optional, Dict
from app.core.database import Database, COLLECTIONS
from app.models.material import MaterialBase, MaterialCreate, MaterialInDB
import pandas as pd
from datetime import datetime
import uuid

class MaterialService:
    def __init__(self):
        self.db = Database.get_db()
        self.collection = self.db[COLLECTIONS["materials"]]
    
    async def import_from_excel(self, df: pd.DataFrame) -> Dict[str, int]:
        """从Excel导入物料数据"""
        total = len(df)
        success = 0
        failed = 0
        
        for _, row in df.iterrows():
            try:
                material = MaterialCreate(
                    material_code=str(row.get("物料编码", "")),
                    material_name=str(row.get("物料名称", "")),
                    specification=str(row.get("规格型号", "")),
                    unit=str(row.get("单位", "")),
                    category={
                        "level1": str(row.get("一级分类", "")),
                        "level2": str(row.get("二级分类", ""))
                    },
                    attributes={
                        "material": str(row.get("材质", "")),
                        "size": str(row.get("尺寸", "")),
                        "standard": str(row.get("执行标准", ""))
                    }
                )
                
                # 转换为数据库模型
                material_db = MaterialInDB(
                    **material.dict(),
                    _id=str(uuid.uuid4()),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # 插入数据库
                await self.collection.insert_one(material_db.dict(by_alias=True))
                success += 1
                
            except Exception as e:
                print(f"导入失败: {str(e)}")
                failed += 1
                
        return {
            "total": total,
            "success": success,
            "failed": failed
        }
    
    async def search_materials(
        self,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        specification: Optional[str] = None
    ) -> List[MaterialBase]:
        """搜索物料"""
        query = {}
        
        if keyword:
            query["$or"] = [
                {"material_code": {"$regex": keyword, "$options": "i"}},
                {"material_name": {"$regex": keyword, "$options": "i"}}
            ]
        
        if category:
            query["category.level1"] = category
            
        if specification:
            query["specification"] = {"$regex": specification, "$options": "i"}
            
        cursor = self.collection.find(query)
        materials = []
        
        async for doc in cursor:
            materials.append(MaterialBase(**doc))
            
        return materials
    
    async def get_material(self, material_code: str) -> Optional[MaterialBase]:
        """获取物料详情"""
        doc = await self.collection.find_one({"material_code": material_code})
        if doc:
            return MaterialBase(**doc)
        return None 