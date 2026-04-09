from fastapi import APIRouter
from pydantic import BaseModel
from app.database.supabase_client import supabase
from pydantic import BaseModel
from fastapi import Query
from app.utils.auth import get_current_user
from fastapi import Depends
from app.services.priority_service import calculate_priority_score

router = APIRouter()


class ComplaintCreate(BaseModel):
    issue_type: str
    description: str | None = None
    latitude: float
    longitude: float
    image_urls: list[str] | None = []


@router.post("/complaints")
def create_complaint(
    complaint: ComplaintCreate,
    user_id: str = Depends(get_current_user)
):

    data = {
        "user_id": user_id,  # temporary user
        "issue_type": complaint.issue_type,
        "description": complaint.description,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "severity_score": 0.5,
        "priority_score": 0.5,
        "status": "submitted"
    }

    response = supabase.table("complaints").insert(data).execute()
    complaint_id = response.data[0]["id"]
    # Save images
    if complaint.image_urls:
        for url in complaint.image_urls:
            supabase.table("complaint_images").insert({
                "complaint_id": complaint_id,
                "image_url": url
            }).execute()

    return {
        "ticket_id": response.data[0]["id"],
        "status": "submitted"
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