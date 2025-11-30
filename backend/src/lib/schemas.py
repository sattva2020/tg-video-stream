from pydantic import BaseModel
from typing import Optional


class CurrentUser(BaseModel):
    id: str
    email: str
    role: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None
