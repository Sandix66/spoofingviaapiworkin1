import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Phone, Shield, Zap } from 'lucide-react';
import { toast } from 'sonner';

const LoginPage = () => {
    const navigate = useNavigate();
    const { login, register } = useAuth();
    const [isLoading, setIsLoading] = useState(false);
    
    // Login form state
    const [loginEmail, setLoginEmail] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    
    // Register form state
    const [registerName, setRegisterName] = useState('');
    const [registerEmail, setRegisterEmail] = useState('');
    const [registerPassword, setRegisterPassword] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
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

    const handleRegister = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            await register(registerEmail, registerPassword, registerName);
            toast.success('Registrasi berhasil!');
            navigate('/dashboard');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Registrasi gagal');
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
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 mb-4 glow-primary">
                        <Phone className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-black tracking-tight">
                        <span className="text-gradient">Voice</span>
                        <span className="text-white">Spoof</span>
                    </h1>
                    <p className="text-gray-400 mt-2 text-sm">Sistem Panggilan Suara dengan Caller ID</p>
                </div>

                {/* Auth Card */}
                <Card className="glass border-white/5 animate-slide-up" style={{ animationDelay: '0.1s' }}>
                    <Tabs defaultValue="login" className="w-full">
                        <TabsList className="grid w-full grid-cols-2 bg-[#0F111A]">
                            <TabsTrigger 
                                value="login" 
                                data-testid="login-tab"
                                className="data-[state=active]:bg-violet-600 data-[state=active]:text-white"
                            >
                                Masuk
                            </TabsTrigger>
                            <TabsTrigger 
                                value="register"
                                data-testid="register-tab"
                                className="data-[state=active]:bg-violet-600 data-[state=active]:text-white"
                            >
                                Daftar
                            </TabsTrigger>
                        </TabsList>

                        {/* Login Tab */}
                        <TabsContent value="login">
                            <CardHeader className="pb-4">
                                <CardTitle className="text-xl">Selamat Datang</CardTitle>
                                <CardDescription>Masuk ke akun Anda</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleLogin} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="login-email">Email</Label>
                                        <Input
                                            id="login-email"
                                            data-testid="login-email-input"
                                            type="email"
                                            placeholder="nama@email.com"
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
                                        {isLoading ? 'Memproses...' : 'Masuk'}
                                    </Button>

                                    <div className="mt-6 text-center">
                                        <Link to="/register" className="text-sm text-violet-400 hover:text-violet-300">
                                            Don't have an account? Register with invitation code
                                        </Link>
                                    </div>
                                </form>
                            </CardContent>
                        </TabsContent>

                        {/* Register Tab */}
                        <TabsContent value="register">
                            <CardHeader className="pb-4">
                                <CardTitle className="text-xl">Buat Akun</CardTitle>
                                <CardDescription>Daftar akun baru</CardDescription>
                            </CardHeader>
                            <CardContent>
                                <form onSubmit={handleRegister} className="space-y-4">
                                    <div className="space-y-2">
                                        <Label htmlFor="register-name">Nama Lengkap</Label>
                                        <Input
                                            id="register-name"
                                            data-testid="register-name-input"
                                            type="text"
                                            placeholder="Nama Anda"
                                            value={registerName}
                                            onChange={(e) => setRegisterName(e.target.value)}
                                            className="bg-[#0F111A] border-white/10 focus:border-violet-500"
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="register-email">Email</Label>
                                        <Input
                                            id="register-email"
                                            data-testid="register-email-input"
                                            type="email"
                                            placeholder="nama@email.com"
                                            value={registerEmail}
                                            onChange={(e) => setRegisterEmail(e.target.value)}
                                            className="bg-[#0F111A] border-white/10 focus:border-violet-500"
                                            required
                                        />
                                    </div>
                                    <div className="space-y-2">
                                        <Label htmlFor="register-password">Password</Label>
                                        <Input
                                            id="register-password"
                                            data-testid="register-password-input"
                                            type="password"
                                            placeholder="••••••••"
                                            value={registerPassword}
                                            onChange={(e) => setRegisterPassword(e.target.value)}
                                            className="bg-[#0F111A] border-white/10 focus:border-violet-500"
                                            required
                                            minLength={6}
                                        />
                                    </div>
                                    <Button 
                                        type="submit"
                                        data-testid="register-submit-btn"
                                        className="w-full bg-violet-600 hover:bg-violet-700 glow-primary"
                                        disabled={isLoading}
                                    >
                                        {isLoading ? 'Memproses...' : 'Daftar'}
                                    </Button>
                                </form>
                            </CardContent>
                        </TabsContent>
                    </Tabs>
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
