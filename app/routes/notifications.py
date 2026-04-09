from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.database.supabase_client import supabase
from app.utils.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationCreate(BaseModel):
    user_id: str
    message: str


@router.post("")
def create_notification(notification: NotificationCreate):

    response = supabase.table("notifications").insert({
        "user_id": notification.user_id,
        "message": notification.message,
        "status": "unread"
    }).execute()

    return response.data[0]


@router.get("")
def get_notifications(user_id: str = Depends(get_current_user)):

    response = supabase.table("notifications")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("created_at", desc=True)\
        .execute()

    return response.data


@router.patch("/{notification_id}/read")
def mark_notification_read(notification_id: str):

    response = supabase.table("notifications").update({
        "status": "read"
    }).eq("id", notification_id).execute()

    return response.data[0]