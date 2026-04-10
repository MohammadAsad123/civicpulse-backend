from fastapi import APIRouter
from pydantic import BaseModel
from app.database.supabase_client import supabase

router = APIRouter(prefix="/work-orders", tags=["Work Orders"])


class WorkOrderCreate(BaseModel):
    complaint_id: str
    inspector_id: str


@router.post("")
def create_work_order(order: WorkOrderCreate):

    response = supabase.table("work_orders").insert({
        "complaint_id": order.complaint_id,
        "inspector_id": order.inspector_id,
        "status": "assigned"
    }).execute()

    # update complaint inspector
    supabase.table("complaints").update({
        "inspector_id": order.inspector_id,
        "status": "assigned"
    }).eq("id", order.complaint_id).execute()

    # create notification for the citizen
    complaint = supabase.table("complaints")\
    .select("user_id")\
    .eq("id", order.complaint_id)\
    .execute()

    user_id = complaint.data[0]["user_id"]

    supabase.table("notifications").insert({
    "user_id": user_id,
    "message": "Your complaint has been assigned to an inspector."
    }).execute()

    return response.data[0]




@router.get("")
def get_work_orders():

    response = supabase.table("work_orders").select("*").execute()

    return response.data


@router.get("/{order_id}")
def get_work_order(order_id: str):

    response = supabase.table("work_orders").select("*").eq("id", order_id).execute()

    if not response.data:
        return {"error": "Work order not found"}

    return response.data[0]


class WorkOrderUpdate(BaseModel):
    status: str


@router.patch("/{order_id}/status")
def update_work_order_status(order_id: str, update: WorkOrderUpdate):

    response = supabase.table("work_orders").update({
        "status": update.status
    }).eq("id", order_id).execute()

    if not response.data:
        return {"error": "Work order not found"}

    # if resolved update complaint
    if update.status == "completed":

        order = response.data[0]

        supabase.table("complaints").update({
            "status": "resolved"
        }).eq("id", order["complaint_id"]).execute()

        # notify citizen that complaint is resolved
        complaint = supabase.table("complaints")\
        .select("user_id")\
        .eq("id", order["complaint_id"])\
        .execute()

        user_id = complaint.data[0]["user_id"]

        supabase.table("notifications").insert({
        "user_id": user_id,
        "message": "Your complaint has been resolved."
    }).execute()



    return response.data[0]