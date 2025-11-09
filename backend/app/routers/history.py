from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import require_user
from app.stores.chat_history import _CHAT_STORE, Chat, Message
import uuid


router = APIRouter()


class ChatCreate(BaseModel):
    title: str
class SaveMessage(BaseModel):
    role: str
    content: str


@router.post("")
def create_chat(body: ChatCreate, user=Depends(require_user)):
    cid = str(uuid.uuid4())
    _CHAT_STORE[cid] = Chat(id=cid, user_sub=user.sub, title=body.title or "Untitled")
    return {"chatId": cid}


@router.get("")
def list_chats(user=Depends(require_user)):
    return [{"id": c.id, "title": c.title} for c in _CHAT_STORE.values() if c.user_sub==user.sub]


@router.get("/{cid}")
def get_chat(cid: str, user=Depends(require_user)):
    chat = _CHAT_STORE.get(cid)
    if not chat or chat.user_sub != user.sub:
        raise HTTPException(404, "Not found")
    return {"id": chat.id, "title": chat.title, "messages": [m.__dict__ for m in chat.messages]}


@router.delete("/{cid}")
def delete_chat(cid: str, user=Depends(require_user)):
    chat = _CHAT_STORE.get(cid)
    if chat and chat.user_sub == user.sub:
        del _CHAT_STORE[cid]
    return {"ok": True}


@router.post("/{cid}/messages")
def add_message(cid: str, body: SaveMessage, user=Depends(require_user)):
    chat = _CHAT_STORE.get(cid)
    if not chat or chat.user_sub != user.sub:
        raise HTTPException(404, "Not found")
    chat.messages.append(Message(role=body.role, content=body.content))
    return {"ok": True}