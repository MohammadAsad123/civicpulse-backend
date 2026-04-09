from app.database.supabase_client import supabase


def calculate_priority_score(complaint_id, severity_score):

    # count upvotes
    response = supabase.table("upvotes").select("*").eq("complaint_id", complaint_id).execute()
    upvotes = len(response.data)

    priority_score = (severity_score * 0.7) + (upvotes * 0.3)

    return round(priority_score, 2)