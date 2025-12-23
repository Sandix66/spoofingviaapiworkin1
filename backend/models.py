from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, Literal
from datetime import datetime

# ==================== USER MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["admin", "user"] = "user"
    credits: float = Field(default=0, ge=0)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    credits: Optional[float] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    credits: float
    is_active: bool
    created_at: str
    created_by: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class CreditUpdate(BaseModel):
    amount: float = Field(..., description="Amount to add (positive) or deduct (negative)")
    reason: Optional[str] = None

# ==================== ACTIVITY LOG MODELS ====================

class ActivityLog(BaseModel):
    id: str
    user_id: str
    action_type: Literal["login", "logout", "call_started", "call_ended", "credit_added", "credit_deducted", "user_created", "user_updated", "user_deleted"]
    details: dict = {}
    timestamp: str

# ==================== CALL HISTORY MODELS ====================

class CallHistory(BaseModel):
    id: str
    user_id: str
    session_id: str
    call_id: str
    recipient_number: str
    duration_seconds: int
    cost_credits: float
    status: str  # completed, failed, no_answer, busy
    voice_provider: str
    voice_name: str
    template_type: str
    recording_url: Optional[str] = None
    recording_file_id: Optional[str] = None
    created_at: str
    ended_at: Optional[str] = None

# ==================== STATS MODELS ====================

class UserStats(BaseModel):
    total_calls: int
    total_duration_seconds: int
    total_credits_spent: float
    successful_calls: int
    failed_calls: int

class AdminDashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_calls_today: int
    total_calls_all_time: int
    total_credits_distributed: float
    total_credits_spent: float
