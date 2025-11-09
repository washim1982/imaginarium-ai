from fastapi import Depends
from app.deps.auth import verify_token, User


def require_user(user: User = Depends(verify_token)) -> User:
    return user