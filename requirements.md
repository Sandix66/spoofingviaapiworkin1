# VoiceSpoof - Aplikasi Panggilan Suara dengan Caller ID Spoofing

## Original Problem Statement
Aplikasi panggilan spoofing dari API key Infobip untuk project kampus dengan fitur:
- Voice call dengan caller ID spoofing
- History/log panggilan
- Dashboard statistik penggunaan
- Text-to-speech untuk pesan suara otomatis
- Multi-user dengan autentikasi (login/register)
- UI modern & minimalis dengan dashboard style profesional

## Architecture

### Backend (FastAPI + MongoDB)
- **server.py**: Main FastAPI application dengan routes untuk auth dan voice calls
- **Authentication**: JWT-based dengan bcrypt password hashing
- **Database**: MongoDB untuk users dan calls collection
- **Infobip Integration**: TTS API untuk voice calls dengan caller ID spoofing

### Frontend (React + Shadcn UI)
- **LoginPage**: Halaman login/register dengan glassmorphism design
- **DashboardPage**: Overview statistik dan panggilan terakhir
- **MakeCallPage**: Form untuk membuat panggilan baru dengan TTS
- **HistoryPage**: Tabel riwayat panggilan dengan filter dan pagination
- **DashboardLayout**: Sidebar navigation dengan responsive design

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | User registration |
| `/api/auth/login` | POST | User login |
| `/api/auth/me` | GET | Get current user |
| `/api/voice/call` | POST | Send voice call |
| `/api/voice/history` | GET | Get call history |
| `/api/voice/stats` | GET | Get call statistics |
| `/api/voice/webhook/delivery-report` | POST | Infobip webhook |

## Tasks Completed ✅
1. Backend authentication system (JWT + bcrypt)
2. Voice call integration with Infobip TTS API
3. Call history and statistics endpoints
4. Frontend login/register pages
5. Dashboard with stats and recent calls
6. Make call page with full form
7. History page with search, filter, pagination
8. Responsive dark theme UI
9. Toast notifications

## Next Steps / Improvements
1. Add real-time call status updates via WebSocket
2. Implement call recording feature
3. Add user profile management
4. Add call templates/presets for quick calling
5. Export call history to CSV/PDF
6. Add rate limiting for API calls
7. Implement call scheduling feature
8. Add analytics dashboard with charts
