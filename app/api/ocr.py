from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from app.models.ocr import OCRResponse, TaskStatus
from app.utils.file_handler import is_valid_file, save_upload_file, get_file_type
from app.services.ocr.ocr_service import OCRService
import uuid

router = APIRouter()
ocr_service = OCRService()

@router.post("/upload", response_model=OCRResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """
    上传文件接口
    
    参数:
    - files: 上传的文件列表（支持图片或Excel）
    
    返回:
    - task_id: 任务ID
    - status: 任务状态
    - message: 处理消息
    """
    # 验证文件数量
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="一次最多上传5个文件")
    
    # 验证每个文件
    for file in files:
        if not is_valid_file(file):
            raise HTTPException(
                status_code=400, 
                detail=f"文件 {file.filename} 格式不正确或超出大小限制"
            )
    
    # 保存文件并创建OCR任务
    saved_files = []
    file_types = []
    
    try:
        for file in files:
            file_path = await save_upload_file(file)
            file_type = get_file_type(file.filename)
            saved_files.append(file_path)
            file_types.append(file_type)
        
        # 创建OCR任务
        task_id = await ocr_service.create_task(saved_files, file_types)
        
        return OCRResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="文件上传成功，开始处理"
        )
        
    except Exception as e:
        # TODO: 清理已上传的文件
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/task/{task_id}", response_model=OCRResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态接口
    
    参数:
    - task_id: 任务ID
    
    返回:
    - task_id: 任务ID
    - status: 任务状态
    - message: 处理消息
    - result: 识别结果（如果完成）
    """
    task = await ocr_service.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    message = {
        TaskStatus.PENDING: "等待处理",
        TaskStatus.PROCESSING: "正在处理中",
        TaskStatus.COMPLETED: "处理完成",
        TaskStatus.FAILED: "处理失败"
    }.get(task.status, "未知状态")
    
    return OCRResponse(
        task_id=task_id,
        status=task.status,
        message=message,
        result=task.result
    ) 