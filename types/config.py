from typing import Dict, Optional, Union

from pydantic import BaseModel


class Footer(BaseModel):
    text: Optional[str]
    icon_url: Optional[str]


class Author(BaseModel):
    name: Optional[str]
    icon: Optional[str]
    url: Optional[str]


class Entry(BaseModel):
    title: Optional[str]
    role_id: Optional[int]
    emoji_id: Optional[Union[int, str]]
    description: Optional[str]


class Message(BaseModel):
    title: str
    channel_id: int
    message_id: int
    title_url: Optional[str]
    description: Optional[str]
    color: Optional[str]
    thumbnail: Optional[str]
    author: Author
    footer: Footer

    entries: Optional[Dict[str, Entry]]


class Config(BaseModel):
    guild_id: int
    remove_role_when_owned: bool

    messages: Optional[Dict[str, Message]]
