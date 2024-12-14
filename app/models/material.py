from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime

class MaterialBase(BaseModel):
    material_code: str = Field(..., description="物料编码")
    material_name: str = Field(..., description="标准物料名称")
    specification: Optional[str] = Field(None, description="规格型号")
    unit: str = Field(default="个", description="基本单位")
    quantity: Optional[float] = Field(None, description="数量")
    factory_price: Optional[float] = Field(None, description="厂价")
    status: bool = Field(True, description="启用状态")
    match_type: Optional[str] = Field(None, description="匹配类型")
    confidence: Optional[float] = Field(None, description="匹配置信度")
    category: Optional[Dict[str, str]] = Field(default_factory=dict, description="物料类别")
    attributes: Optional[Dict[str, str]] = Field(default_factory=dict, description="物料属性")
    material_type: Optional[str] = Field(None, description="物料类型")
    material_group: Optional[str] = Field(None, description="物料组")

class MaterialCreate(MaterialBase):
    pass

class MaterialInDB(MaterialBase):
    id: str = Field(..., alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True

class MaterialMatch(BaseModel):
    original_text: str = Field(..., description="原始文本")
    matched_code: str = Field(..., description="匹配到的物料编码")
    confidence: float = Field(..., description="匹配置信度")
    match_type: str = Field(..., description="匹配类型")
    material_info: Optional[MaterialBase] = Field(None, description="匹配到的物料信息")

    @property
    def material_code(self) -> str:
        return self.matched_code

    @property
    def unit(self) -> str:
        if self.material_info and self.material_info.unit:
            return self.material_info.unit
        return "个"

    @property
    def factory_price(self) -> Optional[float]:
        if self.material_info:
            return self.material_info.factory_price
        return None

    @property
    def specification(self) -> Optional[str]:
        if self.material_info:
            return self.material_info.specification
        return None

class SynonymGroup(BaseModel):
    group_id: str = Field(..., description="同义词组ID")
    standard_name: str = Field(..., description="标准名称")
    synonyms: List[str] = Field(default_factory=list, description="同义词列表")
    material_code: str = Field(..., description="关联的物料编码")
    specification: Optional[str] = Field(None, description="规格型号")
    unit: str = Field(default="个", description="基本单位")
    factory_price: Optional[float] = Field(None, description="厂价")
    category: str = Field(default="material_name", description="同义词组类别")
    status: bool = Field(True, description="是否启用")

class SynonymCreate(BaseModel):
    standard_name: str = Field(..., description="标准名称")
    synonyms: List[str] = Field(..., description="同义词列表")
    material_code: str = Field(..., description="关联的物料编码")
    specification: Optional[str] = Field(None, description="规格型号")
    unit: str = Field(default="个", description="基本单位")
    factory_price: Optional[float] = Field(None, description="厂价")
    category: str = Field(default="material_name", description="同义词组类别") 