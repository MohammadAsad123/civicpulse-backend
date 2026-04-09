from fastapi import APIRouter
from app.database.supabase_client import supabase

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats():

    response = supabase.table("complaints").select("status").execute()

    complaints = response.data

    total = len(complaints)
    submitted = len([c for c in complaints if c["status"] == "submitted"])
    assigned = len([c for c in complaints if c["status"] == "assigned"])
    in_progress = len([c for c in complaints if c["status"] == "in_progress"])
    resolved = len([c for c in complaints if c["status"] == "resolved"])

    return {
        "total_complaints": total,
        "submitted": submitted,
        "assigned": assigned,
        "in_progress": in_progress,
        "resolved": resolved
    }

@router.get("/heatmap")
def get_heatmap_data():

    response = supabase.table("complaints").select(
        "latitude, longitude, severity_score"
    ).execute()

    return response.data

@router.get("/inspectors")
def get_inspector_stats():

    response = supabase.table("inspectors").select("*").execute()

    inspectors = response.data

    return inspectors

@router.get("/sla-breaches")
def get_sla_breaches():

    response = supabase.table("complaints").select("*").eq("breach_flag", True).execute()

    return response.data