from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict
import pandas as pd
import io
from app.models.material import MaterialBase, MaterialCreate
from app.core.database import get_database, COLLECTIONS
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/materials/import")
async def import_materials_from_excel(file: UploadFile = File(...)):
    """从Excel文件导入物料数据"""
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="File must be an Excel file")

    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))

        # 验证必要的列是否存在
        required_columns = ["material_code", "material_name", "specification", "unit"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )

        # 转换为字典列表并处理数据
        materials = []
        errors = []
        for index, row in df.iterrows():
            try:
                # 处理类别和属性列
                category = {}
                if "category_level1" in df.columns:
                    category["level1"] = row["category_level1"]
                if "category_level2" in df.columns:
                    category["level2"] = row["category_level2"]

                # 处理属性列（假设属性列以 "attr_" 开头）
                attributes = {}
                for col in df.columns:
                    if col.startswith("attr_"):
                        attr_name = col[5:]  # 移除 "attr_" 前缀
                        if pd.notna(row[col]):  # 只添加非空值
                            attributes[attr_name] = str(row[col])

                material = MaterialBase(
                    material_code=str(row["material_code"]),
                    material_name=str(row["material_name"]),
                    specification=str(row["specification"]),
                    unit=str(row["unit"]),
                    category=category,
                    attributes=attributes,
                    status=True
                )
                materials.append(material.model_dump())
            except Exception as e:
                errors.append({
                    "row": index + 2,  # Excel行号从1开始，且有标题行
                    "error": str(e)
                })

        if materials:
            db = await get_database()
            collection = db[COLLECTIONS["materials"]]
            for material in materials:
                await collection.update_one(
                    {"material_code": material["material_code"]},
                    {"$set": material},
                    upsert=True
                )

        return {
            "status": "success",
            "message": f"Successfully processed {len(materials)} materials",
            "errors": errors if errors else None,
            "total_rows": len(df),
            "successful_rows": len(materials),
            "failed_rows": len(errors)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/materials/", response_model=List[MaterialBase])
async def get_all_materials():
    """获取所有物料"""
    db = await get_database()
    collection = db[COLLECTIONS["materials"]]
    cursor = collection.find({"status": True})
    materials = []
    async for doc in cursor:
        materials.append(MaterialBase(**doc))
    return materials

@router.get("/materials/{material_code}", response_model=MaterialBase)
async def get_material(material_code: str):
    """获取单个物料信息"""
    db = await get_database()
    collection = db[COLLECTIONS["materials"]]
    doc = await collection.find_one({"material_code": material_code})
    if not doc:
        raise HTTPException(status_code=404, detail="Material not found")
    return MaterialBase(**doc)

@router.post("/materials/generate-synonyms")
async def generate_synonyms():
    """根据现有物料生成同义词组"""
    from app.services.matcher.synonym_service import SynonymService
    from app.models.material import SynonymCreate

    db = await get_database()
    collection = db[COLLECTIONS["materials"]]
    synonym_service = SynonymService()

    # 获取所有物料
    materials = []
    async for doc in collection.find({"status": True}):
        materials.append(MaterialBase(**doc))

    # 生成同义词组
    created_groups = []
    for material in materials:
        # 基于物料名称生成同义词
        synonyms = generate_material_synonyms(material)

        try:
            # 创建同义词组
            synonym_data = SynonymCreate(
                standard_name=material.material_name,
                synonyms=synonyms,
                material_code=material.material_code,
                category="material_name"
            )
            group = await synonym_service.create_synonym_group(synonym_data)
            created_groups.append(group)

            # 如果有规格型号，也创建规格同义词组
            if material.specification:
                spec_synonyms = generate_specification_synonyms(material.specification)
                spec_data = SynonymCreate(
                    standard_name=material.specification,
                    synonyms=spec_synonyms,
                    material_code=material.material_code,
                    category="specification"
                )
                spec_group = await synonym_service.create_synonym_group(spec_data)
                created_groups.append(spec_group)

        except Exception as e:
            print(f"Error creating synonym group for {material.material_name}: {str(e)}")

    return {
        "status": "success",
        "message": f"Generated {len(created_groups)} synonym groups",
        "groups": created_groups
    }

def generate_material_synonyms(material: MaterialBase) -> List[str]:
    """生成物料名称的同义词"""
    synonyms = set()
    name = material.material_name

    # 1. 添加原始名称
    synonyms.add(name)

    # 2. 常见缩写和变体
    # 例如：螺栓 -> 螺丝、螺丝钉
    replacements = {
        "螺栓": ["螺丝", "螺丝钉"],
        "法兰": ["凸缘", "法兰盘"],
        "阀门": ["阀", "闸阀"],
        "管件": ["管配件", "配件"],
        # 可以添加更多的替换规则
    }

    for key, values in replacements.items():
        if key in name:
            for value in values:
                new_name = name.replace(key, value)
                synonyms.add(new_name)

    # 3. 添加类别相关的同义词
    if material.category:
        if "level2" in material.category:
            synonyms.add(material.category["level2"])

    # 4. 添加属性相关的同义词
    if material.attributes:
        if "material" in material.attributes:  # 材质
            synonyms.add(f"{material.attributes['material']}{name}")

    return list(synonyms)

def generate_specification_synonyms(specification: str) -> List[str]:
    """生成规格型号的同义词"""
    synonyms = set()
    spec = specification.upper()

    # 1. 添加原始规格
    synonyms.add(spec)

    # 2. 常见格式变体
    # 例如：DN100 -> DN 100、D100
    if spec.startswith("DN"):
        synonyms.add(spec.replace("DN", "DN "))  # 添加空格
        synonyms.add(spec.replace("DN", "D"))    # DN -> D

    # 3. 处理乘号
    if "*" in spec:
        synonyms.add(spec.replace("*", "×"))  # 替换为中文乘号
        synonyms.add(spec.replace("*", "X"))  # 替换为英文X
    if "×" in spec:
        synonyms.add(spec.replace("×", "*"))
        synonyms.add(spec.replace("×", "X"))
    if "X" in spec:
        synonyms.add(spec.replace("X", "*"))
        synonyms.add(spec.replace("X", "×"))

    return list(synonyms) 