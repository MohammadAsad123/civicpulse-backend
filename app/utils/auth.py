from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
import os

security = HTTPBearer()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_KEY")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
):

    token = credentials.credentials

    # test bypass
    if token == "test-user":
        return "00000000-0000-0000-0000-000000000001"

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )

        return payload["sub"]

    except Exception:
        raise HTTPException(status_code=401, detail="Token verification failed")