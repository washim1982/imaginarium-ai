from fastapi import APIRouter, Depends
from app.core.security import require_user

router = APIRouter()

@router.get("/me")
def me(user = Depends(require_user)):
    return {"sub": user.sub, "email": user.email}
