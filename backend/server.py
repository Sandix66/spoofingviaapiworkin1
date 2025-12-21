from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import jwt
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Infobip configuration
INFOBIP_API_KEY = os.environ.get('INFOBIP_API_KEY')
INFOBIP_BASE_URL = os.environ.get('INFOBIP_BASE_URL')
INFOBIP_CALLS_CONFIG_ID = os.environ.get('INFOBIP_CALLS_CONFIG_ID')

# JWT configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default_secret')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 1440))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Voice Spoof API", version="1.0.0")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
voice_router = APIRouter(prefix="/voice", tags=["Voice Calls"])

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class CallRequest(BaseModel):
    phone_number: str = Field(..., description="Target phone number with country code")
    caller_id: str = Field(..., description="Display caller ID (spoofed number)")
    message_text: str = Field(..., description="Text-to-speech message")
    language: str = Field(default="en", description="Language code for TTS")
    speech_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    repeat_count: int = Field(default=2, ge=1, le=5, description="How many times to repeat the message")

class CallRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    phone_number: str
    caller_id: str
    message_text: str
    language: str
    speech_rate: float
    status: str
    infobip_message_id: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None

class CallStats(BaseModel):
    total_calls: int
    completed_calls: int
    failed_calls: int
    pending_calls: int
    total_duration: int
    avg_duration: float

# ==================== AUTH HELPERS ====================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== AUTH ROUTES ====================

@auth_router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": hash_password(user_data.password),
        "created_at": now
    }
    
    await db.users.insert_one(user_doc)
    
    access_token = create_access_token({"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user_id,
            email=user_data.email,
            name=user_data.name,
            created_at=now
        )
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token({"sub": user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            created_at=user["created_at"]
        )
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"]
    )

# ==================== VOICE ROUTES ====================

@voice_router.post("/call", response_model=CallRecord)
async def send_voice_call(request: CallRequest, current_user: dict = Depends(get_current_user)):
    """Send a voice call with text-to-speech message using Infobip API"""
    
    call_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Create call record in database
    call_doc = {
        "id": call_id,
        "user_id": current_user["id"],
        "phone_number": request.phone_number,
        "caller_id": request.caller_id,
        "message_text": request.message_text,
        "language": request.language,
        "speech_rate": request.speech_rate,
        "status": "pending",
        "infobip_message_id": None,
        "created_at": now,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None
    }
    
    await db.calls.insert_one(call_doc)
    
    # Prepare Infobip request
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Use Infobip Voice TTS API with correct format
    payload = {
        "messages": [
            {
                "from": request.caller_id,
                "destinations": [
                    {"to": request.phone_number}
                ],
                "text": request.message_text,
                "language": request.language,
                "speechRate": request.speech_rate
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            # Build correct URL - INFOBIP_BASE_URL is just the domain
            api_url = f"https://{INFOBIP_BASE_URL}/tts/3/advanced" if not INFOBIP_BASE_URL.startswith('http') else f"{INFOBIP_BASE_URL}/tts/3/advanced"
            logger.info(f"Calling Infobip API: {api_url}")
            
            response = await http_client.post(
                api_url,
                headers=headers,
                json=payload
            )
            
            logger.info(f"Infobip response status: {response.status_code}")
            logger.info(f"Infobip response: {response.text}")
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                infobip_message_id = None
                
                if response_data.get("messages"):
                    infobip_message_id = response_data["messages"][0].get("messageId")
                
                # Update call record
                await db.calls.update_one(
                    {"id": call_id},
                    {"$set": {
                        "status": "initiated",
                        "infobip_message_id": infobip_message_id
                    }}
                )
                
                call_doc["status"] = "initiated"
                call_doc["infobip_message_id"] = infobip_message_id
            else:
                error_msg = f"Infobip error: {response.text}"
                await db.calls.update_one(
                    {"id": call_id},
                    {"$set": {
                        "status": "failed",
                        "error_message": error_msg
                    }}
                )
                call_doc["status"] = "failed"
                call_doc["error_message"] = error_msg
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error sending call: {error_msg}")
        await db.calls.update_one(
            {"id": call_id},
            {"$set": {
                "status": "failed",
                "error_message": error_msg
            }}
        )
        call_doc["status"] = "failed"
        call_doc["error_message"] = error_msg
    
    # Remove MongoDB _id before returning
    call_doc.pop("_id", None)
    return CallRecord(**call_doc)

@voice_router.get("/history", response_model=List[CallRecord])
async def get_call_history(
    limit: int = 50,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get call history for current user"""
    calls = await db.calls.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return [CallRecord(**call) for call in calls]

@voice_router.get("/stats", response_model=CallStats)
async def get_call_stats(current_user: dict = Depends(get_current_user)):
    """Get call statistics for current user"""
    pipeline = [
        {"$match": {"user_id": current_user["id"]}},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "completed_calls": {
                "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
            },
            "failed_calls": {
                "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
            },
            "pending_calls": {
                "$sum": {"$cond": [{"$in": ["$status", ["pending", "initiated"]]}, 1, 0]}
            },
            "total_duration": {
                "$sum": {"$ifNull": ["$duration_seconds", 0]}
            }
        }}
    ]
    
    result = await db.calls.aggregate(pipeline).to_list(1)
    
    if result:
        stats = result[0]
        avg_duration = stats["total_duration"] / stats["completed_calls"] if stats["completed_calls"] > 0 else 0
        return CallStats(
            total_calls=stats["total_calls"],
            completed_calls=stats["completed_calls"],
            failed_calls=stats["failed_calls"],
            pending_calls=stats["pending_calls"],
            total_duration=stats["total_duration"],
            avg_duration=round(avg_duration, 2)
        )
    
    return CallStats(
        total_calls=0,
        completed_calls=0,
        failed_calls=0,
        pending_calls=0,
        total_duration=0,
        avg_duration=0
    )

@voice_router.get("/call/{call_id}", response_model=CallRecord)
async def get_call_detail(call_id: str, current_user: dict = Depends(get_current_user)):
    """Get specific call details"""
    call = await db.calls.find_one(
        {"id": call_id, "user_id": current_user["id"]},
        {"_id": 0}
    )
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return CallRecord(**call)

# Webhook for delivery reports
@voice_router.post("/webhook/delivery-report")
async def handle_delivery_report(report: dict):
    """Handle delivery report webhook from Infobip"""
    logger.info(f"Received delivery report: {report}")
    
    results = report.get("results", [])
    for result in results:
        message_id = result.get("messageId")
        status_text = result.get("status", {}).get("name", "").lower()
        
        # Map Infobip status to our status
        status_mapping = {
            "delivered": "completed",
            "failed": "failed",
            "rejected": "failed",
            "expired": "failed",
            "pending": "pending"
        }
        
        new_status = status_mapping.get(status_text, "completed")
        
        await db.calls.update_one(
            {"infobip_message_id": message_id},
            {"$set": {
                "status": new_status,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": result.get("callDuration", 0)
            }}
        )
    
    return {"status": "received"}

# ==================== MAIN ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "Voice Spoof API v1.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "voice-spoof-api"}

# Include routers
api_router.include_router(auth_router)
api_router.include_router(voice_router)
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
