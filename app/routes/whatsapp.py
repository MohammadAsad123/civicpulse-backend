from fastapi import APIRouter, Request, Response
from twilio.twiml.messaging_response import MessagingResponse
import requests
from requests.auth import HTTPBasicAuth
import os

from app.services.ml_service import classify_image
from app.database.supabase_client import supabase
from datetime import datetime, timedelta

router = APIRouter()

# Conversation state store (phone_number -> state)
conversation_state = {}

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


# -----------------------------------------
# Helper: Create Complaint in Database
# -----------------------------------------

def create_complaint(phone, issue_type, latitude, longitude):

    BOT_USER_ID = "00000000-0000-0000-0000-000000000001"

    # simple SLA rules
    sla_rules = {
        "Road Issue": 48,
        "Garbage Issue": 24,
        "Street Light Issue": 72,
        "Water Issue": 24,
        "No Issue Detected": 24
    }

    hours = sla_rules.get(issue_type, 24)

    sla_deadline = datetime.utcnow() + timedelta(hours=hours)

    data = {
        "user_id": BOT_USER_ID,
        "issue_type": issue_type,
        "description": f"Reported via WhatsApp bot {phone}",
        "latitude": latitude,
        "longitude": longitude,
        "severity_score": 5,
        "priority_score": 5,
        "status": "submitted",
        "sla_deadline": sla_deadline.isoformat()
    }

    res = supabase.table("complaints").insert(data).execute()

    return res.data[0]


# -----------------------------------------
# Helper: Get Latest Complaint by Phone
# -----------------------------------------

def get_latest_complaint():

    res = supabase.table("complaints")\
        .select("*")\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()

    if res.data:
        return res.data[0]

    return None


# -----------------------------------------
# WhatsApp Webhook Endpoint
# -----------------------------------------

@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):

    form = await request.form()

    phone = form.get("From")
    message = form.get("Body", "").strip().upper()

    num_media = int(form.get("NumMedia", 0))
    media_url = form.get("MediaUrl0")

    latitude = form.get("Latitude")
    longitude = form.get("Longitude")

    resp = MessagingResponse()

    # -----------------------------------------
    # IMAGE RECEIVED
    # -----------------------------------------

    if num_media > 0:

        img_bytes = requests.get(
        media_url,
        auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        ).content

        result = classify_image(img_bytes)

        predicted_class = result["predicted_class"]

        label_map = {
        "Garbage Dataset": "Garbage Issue",
        "Road Dataset": "Road Issue",
        "Street Light Dataset": "Street Light Issue",
        "Water Issues Dataset": "Water Issue",
        "No Issue Dataset": "No Issue Detected"
        }

        detected_issue = label_map.get(predicted_class, predicted_class)

        conversation_state[phone] = {
            "step": "awaiting_confirmation",
            "issue_type": detected_issue
        }

        resp.message(
            f"I detected a *{detected_issue}*.\n"
            "Reply YES to confirm or NO to cancel."
        )

        return Response(str(resp), media_type="application/xml")

    # -----------------------------------------
    # USER CONFIRMS ISSUE TYPE
    # -----------------------------------------

    state = conversation_state.get(phone)

    if message == "YES" and state and state["step"] == "awaiting_confirmation":

        state["step"] = "awaiting_location"

        resp.message(
            "Please share your location so we can register the complaint."
        )

        return Response(str(resp), media_type="application/xml")

    # -----------------------------------------
    # LOCATION RECEIVED
    # -----------------------------------------

    if latitude and longitude:

        state = conversation_state.get(phone)

        if state and state["step"] == "awaiting_location":

            issue_type = state["issue_type"]

            complaint = create_complaint(
                phone,
                issue_type,
                float(latitude),
                float(longitude)
            )

            ticket_id = complaint["id"]

            resp.message(
                f"Complaint registered successfully.\n"
                f"Ticket ID: {ticket_id}\n"
                "Expected resolution within SLA time."
            )

            conversation_state.pop(phone, None)

            return Response(str(resp), media_type="application/xml")

    # -----------------------------------------
    # STATUS COMMAND
    # -----------------------------------------

    if message == "STATUS":

        complaint = get_latest_complaint()

        if not complaint:

            resp.message("No complaints found.")

        else:

            resp.message(
                f"Complaint {complaint['id']} status:\n"
                f"{complaint['status']}\n"
                f"SLA Deadline: {complaint['sla_deadline']}"
            )

        return Response(str(resp), media_type="application/xml")

    # -----------------------------------------
    # RESOLVED COMMAND
    # -----------------------------------------

    if message == "RESOLVED":

        complaint = get_latest_complaint()

        if complaint:

            supabase.table("complaints")\
                .update({"status": "resolved"})\
                .eq("id", complaint["id"])\
                .execute()

            resp.message(
                "Thank you! The complaint has been marked as resolved."
            )

        else:

            resp.message("No complaint found to mark resolved.")

        return Response(str(resp), media_type="application/xml")

    # -----------------------------------------
    # HELP MENU
    # -----------------------------------------

    resp.message(
        "Welcome to CivicPulse WhatsApp Bot\n\n"
        "Send a photo of a civic issue to report it.\n\n"
        "Commands:\n"
        "STATUS - Check complaint status\n"
        "RESOLVED - Confirm issue fixed"
    )

    return Response(str(resp), media_type="application/xml")