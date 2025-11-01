
from sqlmodel import Field, SQLModel
from typing import Optional
from datetime import datetime 
import uuid

MAX_SESSIONS = 10

class User(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = Field(default=None, index=True)
    score: int = Field(default=0)
    wallet_address: Optional[str] = Field(default=None, unique=False)

    game_sessions: int = Field(default=MAX_SESSIONS)
    last_session_recharge: datetime = Field(default_factory=datetime.utcnow)

    tap_level: int = Field(default=1) 
    farming_rate: int = Field(default=100) 

    last_claim_time: datetime = Field(default_factory=datetime.utcnow)
    referral_code: str = Field(default_factory=lambda: str(uuid.uuid4()), unique=True, index=True)
    referred_by_id: Optional[int] = Field(default=None, foreign_key="user.id")




class Task(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    points: int
    link: str 
    icon: str 

class UserTask(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    task_id: int = Field(foreign_key="task.id", primary_key=True)
