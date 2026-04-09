from fastapi import APIRouter
from pydantic import BaseModel
from app.database.supabase_client import supabase

router = APIRouter(prefix="/inspectors", tags=["Inspectors"])


class InspectorCreate(BaseModel):
    name: str
    ward: str


@router.post("")
def create_inspector(inspector: InspectorCreate):

    response = supabase.table("inspectors").insert({
        "name": inspector.name,
        "ward": inspector.ward,
        "performance_score": 100
    }).execute()

    return response.data[0]

@router.get("")
def get_inspectors():

    response = supabase.table("inspectors").select("*").execute()

    return response.data


@router.get("/{inspector_id}")
def get_inspector(inspector_id: str):

    response = supabase.table("inspectors").select("*").eq("id", inspector_id).execute()

    if not response.data:
        return {"error": "Inspector not found"}

    return response.data[0]


@router.get("/{inspector_id}/complaints")
def get_inspector_complaints(inspector_id: str):

    response = supabase.table("complaints").select("*").eq("inspector_id", inspector_id).execute()

    return response.data