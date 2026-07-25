from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_user_id
from app.db.session import get_session
from app.services import upload as upload_service

router = APIRouter(prefix="/upload", tags=["文件上传模块"])


@router.post("/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    result = await upload_service.upload_image(request, session, user_id, file)
    return {
        "code": 200,
        "message": "上传成功",
        "data": {key: value for key, value in result.items() if key != "fileKey"},
    }


@router.post("/images")
async def upload_images(
    request: Request,
    files: list[UploadFile] = File(...),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    results = await upload_service.upload_images(request, session, user_id, files)
    return {
        "code": 200,
        "message": "操作成功",
        "data": {"files": results, "count": len(results)},
    }


@router.delete("/file")
async def delete_file(
    request: Request,
    file_key: str = Query(..., alias="fileKey"),
    user_id: int = Depends(current_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object | None]:
    deleted = await upload_service.delete_file(request, session, user_id, file_key)
    if not deleted:
        return {"code": 500, "message": "删除失败", "data": None}
    return {"code": 200, "message": "删除成功", "data": None}
