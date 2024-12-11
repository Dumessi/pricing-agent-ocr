from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Optional
import pandas as pd
import io

from app.models.material import SynonymGroup, SynonymCreate
from app.services.matcher.synonym_service import SynonymService

router = APIRouter()
synonym_service = SynonymService()

@router.post("/synonyms/", response_model=SynonymGroup)
async def create_synonym_group(synonym_data: SynonymCreate):
    """创建新的同义词组"""
    return await synonym_service.create_synonym_group(synonym_data)

@router.post("/synonyms/batch", response_model=List[SynonymGroup])
async def batch_create_synonyms(synonym_data_list: List[SynonymCreate]):
    """批量创建同义词组"""
    return await synonym_service.batch_create_synonyms(synonym_data_list)

@router.post("/synonyms/import")
async def import_synonyms_from_excel(file: UploadFile = File(...)):
    """从Excel文件导入同义词"""
    if not file.filename.endswith(('.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="File must be an Excel file")
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # 验证必要的列是否存在
        required_columns = ["standard_name", "synonyms", "material_code", "category"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # 转换为字典列表
        excel_data = df.to_dict('records')
        groups = await synonym_service.import_from_excel(excel_data)
        
        return {
            "status": "success",
            "message": f"Successfully imported {len(groups)} synonym groups",
            "groups": groups
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/synonyms/", response_model=List[SynonymGroup])
async def get_all_synonyms(category: Optional[str] = None):
    """获取所有同义词组"""
    return await synonym_service.get_all_synonyms(category)

@router.get("/synonyms/{group_id}", response_model=SynonymGroup)
async def get_synonym_group(group_id: str):
    """获取同义词组信息"""
    group = await synonym_service.get_synonym_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    return group

@router.put("/synonyms/{group_id}", response_model=SynonymGroup)
async def update_synonym_group(group_id: str, synonyms: List[str]):
    """更新同义词组"""
    group = await synonym_service.update_synonym_group(group_id, synonyms)
    if not group:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    return group

@router.delete("/synonyms/{group_id}")
async def delete_synonym_group(group_id: str):
    """删除同义词组"""
    success = await synonym_service.delete_synonym_group(group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Synonym group not found")
    return {"status": "success", "message": "Synonym group deleted"} 