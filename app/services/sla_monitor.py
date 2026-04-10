from datetime import datetime
from app.database.supabase_client import supabase


def check_sla_breaches():

    response = supabase.table("complaints").select("*").execute()

    complaints = response.data

    now = datetime.utcnow()

    for complaint in complaints:

        if complaint["sla_deadline"] and complaint["status"] != "resolved":

            deadline = datetime.fromisoformat(complaint["sla_deadline"])

            if deadline < now and not complaint["breach_flag"]:

                supabase.table("complaints").update(
                    {"breach_flag": True}
                ).eq("id", complaint["id"]).execute()

                print(f"SLA breach detected for complaint {complaint['id']}")