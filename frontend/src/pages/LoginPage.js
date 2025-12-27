import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Phone, Shield, Zap } from 'lucide-react';
import { toast } from 'sonner';

const LoginPage = () => {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [isLoading, setIsLoading] = useState(false);
    
    // Login form state
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    const [captchaAnswer, setCaptchaAnswer] = useState('');
    
    // Generate random captcha
    const [captcha, setCaptcha] = useState({ num1: 0, num2: 0, answer: 0 });
    
    useEffect(() => {
        generateCaptcha();
    }, []);
    
    const generateCaptcha = () => {
        const num1 = Math.floor(Math.random() * 10) + 1;
        const num2 = Math.floor(Math.random() * 10) + 1;
        setCaptcha({ num1, num2, answer: num1 + num2 });
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        
        // Validate captcha
        if (parseInt(captchaAnswer) !== captcha.answer) {
            toast.error('Captcha incorrect! Please try again.');
            generateCaptcha();
            setCaptchaAnswer('');
            return;
        }
        
        setIsLoading(true);
        try {
            await login(loginEmail, loginPassword);
            toast.success('Login berhasil!');
            navigate('/dashboard');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Login gagal');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Background */}
            <div 
                className="absolute inset-0 bg-cover bg-center opacity-20"
                style={{
                    backgroundImage: `url('https://images.unsplash.com/photo-1706158449580-d4fd729c5f6e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1Nzh8MHwxfHNlYXJjaHwyfHxhYnN0cmFjdCUyMGN5YmVyJTIwbmV0d29yayUyMGRhdGElMjB2aXN1YWxpemF0aW9uJTIwZGFyayUyMGJhY2tncm91bmR8ZW58MHx8fGJsYWNrfDE3NjYzMzg2NDd8MA&ixlib=rb-4.1.0&q=85')`
                }}
            />
            <div className="absolute inset-0 bg-gradient-to-br from-[#0B0C15]/90 via-[#0B0C15]/95 to-[#0B0C15]" />
            
            <div className="relative z-10 w-full max-w-md">
                {/* Logo & Title */}
                <div className="text-center mb-8 animate-slide-up">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br from-cyan-400 to-cyan-600 mb-4 shadow-lg shadow-cyan-500/50">
                        <Phone className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-5xl font-black tracking-tight" style={{
                        background: 'linear-gradient(135deg, #67e8f9 0%, #22d3ee 40%, #0891b2 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        filter: 'drop-shadow(0 0 12px rgba(103, 232, 249, 1)) drop-shadow(0 3px 6px rgba(251, 191, 36, 0.8))',
                        textShadow: '0 0 30px rgba(103, 232, 249, 0.8)'
                    }}>
                        DINOSAUROTP
                    </h1>
                    <p className="text-gray-400 mt-2 text-sm">Advanced Voice OTP Collection System</p>
                </div>

                {/* Auth Card */}
                <Card className="glass border-white/5 animate-slide-up" style={{ animationDelay: '0.1s' }}>
                    {/* Login Form */}
                    <CardHeader className="pb-4">
                        <CardTitle className="text-xl">Welcome Back</CardTitle>
                        <CardDescription>Login to your account</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleLogin} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="login-email">Email</Label>
                                        <Input
                                            id="login-email"
                                            data-testid="login-email-input"
                                            type="email"
                                            placeholder="name@email.com"
                                            value={loginEmail}
                                            onChange={(e) => setLoginEmail(e.target.value)}
                                            className="bg-[#0F111A] border-white/10 focus:border-violet-500"
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="login-password">Password</Label>
                                        <Input
                                            id="login-password"
                                            data-testid="login-password-input"
                                            type="password"
                                            placeholder="••••••••"
                                            value={loginPassword}
                                            onChange={(e) => setLoginPassword(e.target.value)}
                                            className="bg-[#0F111A] border-white/10 focus:border-violet-500"
                                            required
                                        />
                                    </div>
                                    <Button 
                                        type="submit" 
                                        data-testid="login-submit-btn"
                                        className="w-full bg-violet-600 hover:bg-violet-700 glow-primary"
                                        disabled={isLoading}
                                    >
                                        {isLoading ? 'Processing...' : 'Login'}
                                    </Button>

                                    <div className="mt-6 text-center">
                                        <Link to="/register" className="text-sm text-violet-400 hover:text-violet-300">
                                            Don&apos;t have an account? Register with invitation code
                                        </Link>
                                    </div>
                                </form>
                            </CardContent>
                </Card>

                {/* Features */}
                <div className="mt-8 grid grid-cols-3 gap-4 text-center animate-slide-up" style={{ animationDelay: '0.2s' }}>
                    <div className="space-y-2">
                        <div className="w-10 h-10 mx-auto rounded-lg bg-violet-600/20 flex items-center justify-center">
                            <Phone className="w-5 h-5 text-violet-400" />
                        </div>
                        <p className="text-xs text-gray-400">Voice Call</p>
                    </div>
                    <div className="space-y-2">
                        <div className="w-10 h-10 mx-auto rounded-lg bg-cyan-600/20 flex items-center justify-center">
                            <Shield className="w-5 h-5 text-cyan-400" />
                        </div>
                        <p className="text-xs text-gray-400">Caller ID</p>
                    </div>
                    <div className="space-y-2">
                        <div className="w-10 h-10 mx-auto rounded-lg bg-emerald-600/20 flex items-center justify-center">
                            <Zap className="w-5 h-5 text-emerald-400" />
                        </div>
                        <p className="text-xs text-gray-400">TTS Engine</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
