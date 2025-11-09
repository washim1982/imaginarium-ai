import json, time, urllib.request, os
from fastapi import Header, HTTPException
import jwt
from jwt import ExpiredSignatureError


AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
ALGO = os.getenv("AUTH0_ALGO", "RS256")
JWKS_CACHE = None
JWKS_EXP = 0

class User:
    def __init__(self, sub: str, email: str | None = None):
        self.sub = sub
        self.email = email or sub

def get_jwks():
    global JWKS_CACHE, JWKS_EXP
    now = time.time()
    if JWKS_CACHE and now < JWKS_EXP:
        return JWKS_CACHE
    url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    with urllib.request.urlopen(url) as resp:
        JWKS_CACHE = json.loads(resp.read())
        JWKS_EXP = now + 3600
        return JWKS_CACHE

# 🔧 this is the required function
def verify_token(auth_header: str = Header(..., alias="Authorization")) -> User:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.split(" ", 1)[1]
    unverified_header = jwt.get_unverified_header(token)
    jwks = get_jwks()
    key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
    if not key:
        raise HTTPException(status_code=401, detail="Invalid token key")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[ALGO],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
            leeway=60  # ⏰ 60-second tolerance
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired – please refresh login")
    return User(sub=payload.get("sub"), email=payload.get("email"))
