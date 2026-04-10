from fastapi import APIRouter, UploadFile, File
from app.database.supabase_client import supabase
import uuid

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.post("/image")
async def upload_image(file: UploadFile = File(...)):

    file_ext = file.filename.split(".")[-1]
    file_name = f"{uuid.uuid4()}.{file_ext}"

    file_bytes = await file.read()

    supabase.storage.from_("complaint-images").upload(file_name, file_bytes)

    public_url = supabase.storage.from_("complaint-images").get_public_url(file_name)

    return {
        "image_url": public_url
    }