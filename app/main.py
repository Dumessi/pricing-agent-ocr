from fastapi import FastAPI
from app.api import ocr, materials, synonyms
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# 注册路由
app.include_router(ocr.router, prefix="/api", tags=["OCR"])
app.include_router(materials.router, prefix="/api", tags=["Materials"])
app.include_router(synonyms.router, prefix="/api", tags=["Synonyms"])

@app.get("/")
async def root():
    return {"message": "Welcome to Pricing Agent OCR System"} 