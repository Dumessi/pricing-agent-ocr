from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

class MaterialBase(BaseModel):
    material_code: str = Field(..., description="物料编码")
    material_name: str = Field(..., description="标准物料名称")
    specification: str = Field(..., description="规格型号")
    unit: str = Field(..., description="基本单位")
    category: Dict[str, str] = Field(..., description="物料分类")
    attributes: Dict[str, str] = Field(..., description="物料属性")
    status: bool = Field(True, description="启用状态")

class MaterialCreate(MaterialBase):
    pass

class MaterialInDB(MaterialBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True

class MaterialMatch(BaseModel):
    original_text: str = Field(..., description="原始文本")
    matched_code: str = Field(..., description="匹配到的物料编码")
    confidence: float = Field(..., description="匹配置信度")
    match_type: str = Field(..., description="匹配类型")
    material_info: Optional[MaterialBase] = Field(None, description="匹配到的物料信息")

class SynonymGroup(BaseModel):
    """同义词组模型"""
    group_id: str = Field(..., description="同义词组ID")
    standard_name: str = Field(..., description="标准名称")
    synonyms: List[str] = Field(..., description="同义词列表")
    material_code: str = Field(..., description="关联的物料编码")
    category: str = Field(..., description="同义词组类别")
    status: bool = Field(True, description="是否启用")

class SynonymCreate(BaseModel):
    """创建同义词组的请求模型"""
    standard_name: str = Field(..., description="标准名称")
    synonyms: List[str] = Field(..., description="同义词列表")
    material_code: str = Field(..., description="关联的物料编码")
    category: str = Field(..., description="同义词组类别") 