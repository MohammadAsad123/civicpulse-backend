from fastapi import APIRouter
from pydantic import BaseModel
from app.database.supabase_client import supabase
from pydantic import BaseModel
from fastapi import Query
from app.utils.auth import get_current_user
from fastapi import Depends
from app.services.priority_service import calculate_priority_score
from app.services.ml_service import classify_image
from fastapi import UploadFile, File
from fastapi import Form
from datetime import datetime, timedelta

router = APIRouter()




@router.post("/complaints")
async def create_complaint(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    description: str | None = Form(None),
    user_id: str = Depends(get_current_user)
):

    # read image
    image_bytes = await file.read()

    # run ML classification
    ml_result = classify_image(image_bytes)

    predicted_class = ml_result["predicted_class"]
    severity_score = ml_result["severity_score"]
    manual_review = ml_result["needs_manual_review"]

    # map ML labels to backend issue types
    label_map = {
        "Garbage Dataset": "garbage_issue",
        "Road Dataset": "road_issue",
        "Street Light Dataset": "streetlight",
        "Water Issues Dataset": "water_issue",
        "No Issue Dataset": "no_issue"
    }

    issue_type = label_map.get(predicted_class, "unknown")

    # SLA hours based on issue type
    sla_map = {
    "garbage_issue": 24,
    "road_issue": 48,
    "water_issue": 12,
    "streetlight": 72,
    "no_issue": 24
    }
    sla_hours = sla_map.get(issue_type, 48)
    sla_deadline = datetime.utcnow() + timedelta(hours=sla_hours)

    # upload image to Supabase Storage
    file_path = f"complaints/{file.filename}"

    supabase.storage.from_("complaint-images").upload(
        file_path,
        image_bytes
    )

    image_url = supabase.storage.from_("complaint-images").get_public_url(file_path)

    # create complaint data
    data = {
        "user_id": user_id,
        "issue_type": issue_type,
        "description": description,
        "latitude": latitude,
        "longitude": longitude,
        "severity_score": severity_score,
        "priority_score": 0,
        "status": "submitted",
        "sla_deadline": sla_deadline.isoformat()
    }

    response = supabase.table("complaints").insert(data).execute()

    complaint_id = response.data[0]["id"]

    # calculate priority score
    priority_score = calculate_priority_score(complaint_id, severity_score)

    supabase.table("complaints").update({
        "priority_score": priority_score
    }).eq("id", complaint_id).execute()

    # save complaint image
    supabase.table("complaint_images").insert({
        "complaint_id": complaint_id,
        "image_url": image_url
    }).execute()

    return {
        "ticket_id": complaint_id,
        "predicted_issue": issue_type,
        "severity_score": severity_score,
        "manual_review": manual_review,
        "status": "submitted",
        "sla_deadline": sla_deadline.isoformat()
    }

    

@router.get("/complaints")
def get_complaints(
    issue_type: str | None = Query(None),
    status: str | None = Query(None),
    breach_flag: bool | None = Query(None),
    limit: int = Query(20),
    offset: int = Query(0)
):

    query = supabase.table("complaints").select("*")

    if issue_type:
        query = query.eq("issue_type", issue_type)

    if status:
        query = query.eq("status", status)

    if breach_flag is not None:
        query = query.eq("breach_flag", breach_flag)

    response = query.range(offset, offset + limit - 1).execute()

    return response.data

@router.get("/complaints/{complaint_id}")
def get_complaint_by_id(complaint_id: str):

    response = supabase.table("complaints").select("*").eq("id", complaint_id).execute()

    if not response.data:
        return {"error": "Complaint not found"}

    return response.data[0]



class StatusUpdate(BaseModel):
    status: str


@router.patch("/complaints/{complaint_id}/status")
def update_complaint_status(complaint_id: str, update: StatusUpdate):

    response = supabase.table("complaints").update(
        {"status": update.status}
    ).eq("id", complaint_id).execute()

    if not response.data:
        return {"error": "Complaint not found"}

    return {
        "message": "Complaint status updated",
        "complaint": response.data[0]
    }

@router.post("/complaints/{complaint_id}/upvote")
def upvote_complaint(
    complaint_id: str,
    user_id: str = Depends(get_current_user)
):

    data = {
        "complaint_id": complaint_id,
        "user_id": user_id
    }

    response = supabase.table("upvotes").insert(data).execute()

    if not response.data:
        return {"error": "Upvote failed"}

    # get complaint severity
    complaint = supabase.table("complaints").select("severity_score").eq("id", complaint_id).execute()

    severity_score = complaint.data[0]["severity_score"]

    # calculate new priority
    priority_score = calculate_priority_score(complaint_id, severity_score)

    # update complaint priority
    supabase.table("complaints").update({
        "priority_score": priority_score
    }).eq("id", complaint_id).execute()

    return {
        "message": "Complaint upvoted successfully",
        "priority_score": priority_score
    }