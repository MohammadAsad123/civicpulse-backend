from fastapi import APIRouter, UploadFile, File
from app.services.ml_service import classify_image

router = APIRouter(prefix="/ml", tags=["ML"])


@router.post("/classify")
async def classify(file: UploadFile = File(...)):

    image_bytes = await file.read()

    result = classify_image(image_bytes)

    return result