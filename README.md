# DINOSAUROTP - Enterprise Voice OTP Collection System

![DINOSAUROTP](https://img.shields.io/badge/DINOSAUROTP-Production%20Ready-cyan?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-Campus%20Project-green?style=for-the-badge)

## 🦖 Project Overview

**DINOSAUROTP** adalah sistem enterprise-grade untuk Voice OTP Collection menggunakan teknologi IVR (Interactive Voice Response), Multi-Provider Text-to-Speech, dan Answering Machine Detection. Sistem ini dilengkapi dengan multi-user management, payment gateway integration, dan real-time monitoring.

**Live Demo:** [https://ivrflow.preview.emergentagent.com](https://ivrflow.preview.emergentagent.com)

---

## 📋 Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [API Documentation](#api-documentation)
7. [Architecture](#architecture)

---

## ✨ Features

### Core OTP Bot Features
- **Multi-Step IVR System** - Interactive voice response dengan 3 steps
- **Multi-Provider TTS** - 35 voices dari Infobip, ElevenLabs, dan Deepgram
- **Voice Preview** - Test voice sebelum melakukan call
- **9 Professional Templates** - Pre-configured call scenarios
- **Custom Templates** - User dapat membuat template sendiri
- **Request Additional Info** - Capture SSN, DOB, CVV, Email OTP
- **AMD Detection** - 8 event types (HUMAN, MACHINE, FAX, BEEP, dll)
- **Call Recording** - Auto-record dengan playback & download
- **Real-time Monitoring** - WebSocket untuk live call logs

### Enterprise Features
- **Multi-User System** - Role-based access (Admin/User)
- **Credit System** - Per-minute billing ($1/minute)
- **Daily Plan System** - FUP-based unlimited calling
- **Payment Gateway** - Veripay QRIS auto-payment
- **Admin Panel** - User management, stats, approvals
- **Dashboard Analytics** - Call stats, success rate, AMD breakdown
- **Call History** - Complete tracking dengan OTP capture
- **Invitation System** - User referral dengan unique codes
- **Single Session Enforcement** - Force logout on new device
- **Activity Logging** - Complete audit trail
- **Telegram Integration** - OTP notifications dengan inline buttons

---

## 🛠️ Tech Stack

### Frontend
- **React.js** - UI framework
- **Tailwind CSS** - Styling
- **Shadcn UI** - Component library
- **Socket.IO Client** - Real-time communication
- **Axios** - HTTP client
- **React Router** - Navigation

### Backend
- **FastAPI** - Python web framework
- **Motor** - Async MongoDB driver
- **Socket.IO** - WebSocket server
- **JWT** - Authentication
- **Bcrypt** - Password hashing
- **HTTPX** - Async HTTP client

### External Services
- **Infobip** - Voice Calls API & TTS
- **ElevenLabs** - Premium TTS voices
- **Deepgram** - AI-powered TTS
- **Veripay** - Payment gateway (QRIS)
- **Telegram Bot API** - OTP notifications

### Database
- **MongoDB** - NoSQL database
- 7 Collections: users, otp_sessions, call_history, user_activities, invitation_codes, custom_templates, veripay_transactions

---

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone [your-github-repo-url]
cd dinosaurotp
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Configure .env file
uvicorn server:fastapi_app --host 0.0.0.0 --port 8001
```

### 3. Frontend Setup
```bash
cd frontend
yarn install
# Configure .env file
yarn start
```

### 4. Access Application
- Frontend: http://localhost:3000
- Backend: http://localhost:8001
- Admin: Admin@voip.com / 1234

---

## ⚙️ Environment Variables

### Backend (.env)
```bash
# Database
MONGO_URL=mongodb://localhost:27017
DB_NAME=dinosaurotp_db

# Infobip
INFOBIP_API_KEY=your_key
INFOBIP_BASE_URL=https://xxxxx.api.infobip.com
INFOBIP_CALLS_CONFIG_ID=your_config_id

# TTS Providers
ELEVENLABS_API_KEY=your_key
DEEPGRAM_API_KEY=your_key

# Payment
VERIPAY_API_KEY=your_key
VERIPAY_SECRET_KEY=your_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# JWT
JWT_SECRET_KEY=your_secret
JWT_ALGORITHM=HS256
```

### Frontend (.env)
```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

---

## 📊 Project Statistics

- **Total Features:** 25+ major systems
- **API Endpoints:** 70+ RESTful endpoints
- **Database Collections:** 7 collections
- **Frontend Pages:** 8 pages
- **Voice Options:** 35 TTS voices
- **Call Templates:** 9 default + unlimited custom
- **Lines of Code:** 10,000+ lines
- **External Integrations:** 5 services

---

## 🎯 Key Achievements

1. ✅ **Full-stack Development** - React frontend + FastAPI backend
2. ✅ **Real-time Communication** - WebSocket implementation
3. ✅ **Multi-provider Integration** - 5 external APIs
4. ✅ **Payment Processing** - QRIS auto-payment
5. ✅ **Security Implementation** - JWT, RBAC, encryption
6. ✅ **Database Design** - Optimized MongoDB schema
7. ✅ **Production Deployment** - Live & operational

---

## 📞 Demo Credentials

**Admin Account:**
```
Email: Admin@voip.com
Password: 1234
Role: Administrator
Credits: Unlimited
```

**Regular User:**
```
Email: testuser@example.com
Password: password
Role: User
Credits: 100
```

---

## 🔐 Security Notice

⚠️ **For Production Use:**
1. Change all default passwords
2. Use environment variables for secrets
3. Enable HTTPS
4. Configure CORS properly
5. Rate limiting
6. Database backups
7. Monitor logs

---

## 📝 License

Campus Project - Educational Use Only

---

## 🙏 Acknowledgments

Developed as a campus project demonstrating enterprise-level full-stack development capabilities.

**Special Thanks:**
- University Computer Science Department
- Project Supervisor
- Beta Testers

---

**© 2025 DINOSAUROTP - Campus Project**

**Contact:** @TTGamik (Telegram)
