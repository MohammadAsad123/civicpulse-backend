from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import os
import requests

security = HTTPBearer()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    print("AUTH FUNCTION CALLED")   # 👈 ADD THIS

    token = credentials.credentials

    try:
        payload = jwt.get_unverified_claims(token)

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # 🔥 Fetch role from profiles table
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}",
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}"
            }
        )

        data = res.json()
        print("SUPABASE RESPONSE:", data)

        if not data:
            raise HTTPException(status_code=401, detail="User not found")

        return {
            "id": user_id,
            "role": data[0]["role"]
        }

    except Exception as e:
        raise HTTPException(status_code=401, detail="Token verification failed")


# ✅ Citizen-only access
def require_citizen(user=Depends(get_current_user)):
    if user["role"] != "citizen":
        raise HTTPException(status_code=403, detail="Citizen access only")
    return user


# ✅ Authority-only access
def require_authority(user=Depends(get_current_user)):
    if user["role"] != "authority":
        raise HTTPException(status_code=403, detail="Authority access only")
    return user