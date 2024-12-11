from fastapi import APIRouter
from app.api import ocr, materials

router = APIRouter()

router.include_router(ocr.router, prefix="/ocr", tags=["OCR识别"])
router.include_router(materials.router, prefix="/materials", tags=["物料管理"]) 