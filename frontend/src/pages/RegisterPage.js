import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Phone, Mail, Lock, User, Ticket } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RegisterPage = () => {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        confirmPassword: '',
        name: '',
        invitationCode: ''
    });
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();

    const handleRegister = async (e) => {
        e.preventDefault();

        if (formData.password !== formData.confirmPassword) {
            toast.error('Passwords do not match');
            return;
        }

        if (!formData.invitationCode) {
            toast.error('Invitation code is required');
            return;
        }

        setIsLoading(true);

        try {
            const response = await axios.post(`${API}/auth/register`, {
                email: formData.email,
                password: formData.password,
                name: formData.name,
                invitation_code: formData.invitationCode
            });

            const { access_token, user } = response.data;
            localStorage.setItem('token', access_token);
            
            toast.success(`Welcome ${user.name}! You have ${user.credits} credits.`);
            navigate('/dashboard');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Registration failed');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#0B0C15] via-[#12141F] to-[#0B0C15] flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-400 to-cyan-600 mb-4 shadow-lg shadow-cyan-500/50">
                        <Phone className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-5xl font-black mb-2" style={{
                        background: 'linear-gradient(135deg, #67e8f9 0%, #22d3ee 40%, #0891b2 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        filter: 'drop-shadow(0 0 12px rgba(103, 232, 249, 1)) drop-shadow(0 3px 6px rgba(251, 191, 36, 0.8))',
                        textShadow: '0 0 30px rgba(103, 232, 249, 0.8)'
                    }}>
                        DINOSAUROTP
                    </h1>
                    <p className="text-gray-400">Advanced Voice OTP Collection System</p>
                </div>

                <Card className="glass border-white/10">
                    <CardHeader>
                        <CardTitle className="text-2xl text-center text-white">Create Account</CardTitle>
                        <p className="text-center text-gray-400 text-sm mt-2">Register for DINOSAUROTP</p>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleRegister} className="space-y-4">
                            <div className="space-y-2">
                                <Label className="text-gray-300 flex items-center gap-2">
                                    <User className="w-4 h-4" />
                                    Username
                                </Label>
                                <Input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                                    className="bg-[#0F111A] border-white/10 text-white"
                                    placeholder="Choose a username"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="text-gray-300 flex items-center gap-2">
                                    <Mail className="w-4 h-4" />
                                    Email
                                </Label>
                                <Input
                                    type="email"
                                    value={formData.email}
                                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                                    className="bg-[#0F111A] border-white/10 text-white"
                                    placeholder="nama@email.com"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="text-gray-300 flex items-center gap-2">
                                    <Lock className="w-4 h-4" />
                                    Password
                                </Label>
                                <Input
                                    type="password"
                                    value={formData.password}
                                    onChange={(e) => setFormData({...formData, password: e.target.value})}
                                    className="bg-[#0F111A] border-white/10 text-white"
                                    placeholder="Choose a password"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="text-gray-300 flex items-center gap-2">
                                    <Lock className="w-4 h-4" />
                                    Confirm Password
                                </Label>
                                <Input
                                    type="password"
                                    value={formData.confirmPassword}
                                    onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                                    className="bg-[#0F111A] border-white/10 text-white"
                                    placeholder="Confirm your password"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="text-gray-300 flex items-center gap-2">
                                    <Ticket className="w-4 h-4" />
                                    Invitation Code
                                </Label>
                                <Input
                                    type="text"
                                    value={formData.invitationCode}
                                    onChange={(e) => setFormData({...formData, invitationCode: e.target.value.toUpperCase()})}
                                    className="bg-[#0F111A] border-white/10 text-white text-center text-lg tracking-widest"
                                    placeholder="Enter your invitation code"
                                    required
                                />
                                <p className="text-xs text-gray-500">Don't have a code? Contact admin</p>
                            </div>

                            <Button
                                type="submit"
                                className="w-full bg-gradient-to-r from-violet-600 to-cyan-500 hover:from-violet-500 hover:to-cyan-400"
                                disabled={isLoading}
                            >
                                {isLoading ? 'Creating Account...' : 'Register'}
                            </Button>
                        </form>

                        <div className="mt-6 text-center">
                            <Link to="/" className="text-sm text-violet-400 hover:text-violet-300">
                                Already have an account? Login
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default RegisterPage;
