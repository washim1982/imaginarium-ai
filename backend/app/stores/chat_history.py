from typing import Dict, List
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Chat:
    id: str
    user_sub: str
    title: str
    messages: List[Message] = field(default_factory=list)


_CHAT_STORE: Dict[str, Chat] = {}