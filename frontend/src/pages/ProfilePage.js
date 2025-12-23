import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { User, CreditCard, Phone, Lock, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProfilePage = () => {
    const [profile, setProfile] = useState(null);
    const [stats, setStats] = useState({});
    const [calls, setCalls] = useState([]);
    const [myInvite, setMyInvite] = useState(null);
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const navigate = useNavigate();

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [profileRes, statsRes, callsRes, inviteRes] = await Promise.all([
                axios.get(`${API}/user/profile`, { headers: getAuthHeaders() }),
                axios.get(`${API}/user/stats`, { headers: getAuthHeaders() }),
                axios.get(`${API}/user/calls?limit=20`, { headers: getAuthHeaders() }),
                axios.get(`${API}/user/my-invite`, { headers: getAuthHeaders() })
            ]);

            setProfile(profileRes.data);
            setStats(statsRes.data || {});
            setCalls(callsRes.data.calls || []);
            setMyInvite(inviteRes.data.code);
        } catch (error) {
            toast.error('Failed to load profile');
        }
    };



    const handleGenerateMyInvite = async () => {
        try {
            const response = await axios.post(`${API}/user/generate-invite`, {}, { headers: getAuthHeaders() });
            setMyInvite(response.data.code);
            toast.success(response.data.message || 'Invitation code generated!');
        } catch (error) {
            toast.error('Failed to generate invitation code');
        }
    };

    const handleCopyInvite = () => {
        if (myInvite?.code) {
            navigator.clipboard.writeText(myInvite.code);
            toast.success('Invitation code copied!');
        }
    };

    const handleChangePassword = async () => {
        if (newPassword !== confirmPassword) {
            toast.error('Passwords do not match');
            return;
        }

        try {
            await axios.put(
                `${API}/user/password`,
                { current_password: currentPassword, new_password: newPassword },
                { headers: getAuthHeaders() }
            );
            toast.success('Password changed successfully!');
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to change password');
        }
    };

    if (!profile) return <div className="text-white p-6">Loading...</div>;

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
            <div className="max-w-6xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-white">My Profile</h1>
                        <p className="text-gray-400 mt-1">{profile.email}</p>
                    </div>
                    <Button onClick={() => navigate('/')} variant="outline">Back to OTP Bot</Button>
                </div>

                {/* Profile Info & Credits */}
                <div className="grid grid-cols-2 gap-6">
                    <Card className="bg-gray-800 border-gray-700">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <User className="w-5 h-5" />
                                Account Information
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <div>
                                <p className="text-sm text-gray-400">Name</p>
                                <p className="text-lg text-white font-medium">{profile.name}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-400">Email</p>
                                <p className="text-lg text-white font-medium">{profile.email}</p>
                            </div>
                            <div>
                                <p className="text-sm text-gray-400">Account Type</p>
                                <span className={`px-3 py-1 rounded text-sm ${profile.role === 'admin' ? 'bg-purple-600' : 'bg-blue-600'} text-white`}>
                                    {profile.role === 'admin' ? 'Administrator' : 'Regular User'}
                                </span>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="bg-gray-800 border-gray-700">
                        <CardHeader>
                            <CardTitle className="text-white flex items-center gap-2">
                                <CreditCard className="w-5 h-5" />
                                Credits & Usage
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="bg-gradient-to-r from-yellow-600 to-orange-600 p-4 rounded-lg">
                                <p className="text-sm text-yellow-100">Available Credits</p>
                                <p className="text-4xl font-bold text-white mt-1">{profile.credits?.toFixed(0)}</p>
                                <p className="text-xs text-yellow-100 mt-2">1 credit = 1 minute call</p>
                            </div>
                            <div className="grid grid-cols-2 gap-3 text-center">
                                <div className="bg-gray-900 p-3 rounded">
                                    <p className="text-2xl font-bold text-white">{stats.total_calls || 0}</p>
                                    <p className="text-xs text-gray-400">Total Calls</p>
                                </div>
                                <div className="bg-gray-900 p-3 rounded">
                                    <p className="text-2xl font-bold text-white">{stats.total_credits_spent?.toFixed(0) || 0}</p>
                                    <p className="text-xs text-gray-400">Credits Spent</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>


                {/* My Invitation Code */}
                <Card className="bg-gray-800 border-gray-700">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Ticket className="w-5 h-5" />
                            My Invitation Code
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {myInvite ? (
                            <div className="p-6 bg-purple-900/20 border border-purple-500/30 rounded-lg text-center">
                                <p className="text-sm text-gray-300 mb-3">Share this code to invite friends:</p>
                                <div className="flex items-center justify-center gap-3">
                                    <code className="text-3xl font-mono font-bold text-purple-400 tracking-widest">
                                        {myInvite.code}
                                    </code>
                                    <Button onClick={handleCopyInvite} className="bg-purple-600">
                                        <Copy className="w-4 h-4 mr-2" />
                                        Copy
                                    </Button>
                                </div>
                                <p className="text-xs text-gray-400 mt-4">
                                    Status: {myInvite.is_used ? (
                                        <span className="text-red-400">Used</span>
                                    ) : (
                                        <span className="text-green-400">Available</span>
                                    )}
                                </p>
                                {myInvite.is_used && (
                                    <p className="text-xs text-gray-500 mt-1">
                                        Used on {new Date(myInvite.used_at).toLocaleDateString()}
                                    </p>
                                )}
                            </div>
                        ) : (
                            <div className="text-center py-6">
                                <p className="text-gray-400 mb-4">You haven't generated an invitation code yet</p>
                                <Button onClick={handleGenerateMyInvite} className="bg-purple-600">
                                    <Ticket className="w-4 h-4 mr-2" />
                                    Generate My Invite Code
                                </Button>
                            </div>
                        )}
                    </CardContent>
                </Card>


                {/* Change Password */}
                <Card className="bg-gray-800 border-gray-700">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Lock className="w-5 h-5" />
                            Change Password
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="max-w-md space-y-4">
                            <div>
                                <Label className="text-gray-300">Current Password</Label>
                                <Input
                                    type="password"
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="bg-gray-900 border-gray-600 text-white"
                                />
                            </div>
                            <div>
                                <Label className="text-gray-300">New Password</Label>
                                <Input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="bg-gray-900 border-gray-600 text-white"
                                />
                            </div>
                            <div>
                                <Label className="text-gray-300">Confirm New Password</Label>
                                <Input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="bg-gray-900 border-gray-600 text-white"
                                />
                            </div>
                            <Button onClick={handleChangePassword} className="bg-blue-600">Change Password</Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Call History */}
                <Card className="bg-gray-800 border-gray-700">
                    <CardHeader>
                        <CardTitle className="text-white">My Call History</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow className="border-gray-700">
                                    <TableHead className="text-gray-400">Recipient</TableHead>
                                    <TableHead className="text-gray-400">Duration</TableHead>
                                    <TableHead className="text-gray-400">Cost</TableHead>
                                    <TableHead className="text-gray-400">Voice</TableHead>
                                    <TableHead className="text-gray-400">Status</TableHead>
                                    <TableHead className="text-gray-400">Time</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {calls.map(call => (
                                    <TableRow key={call.id} className="border-gray-700">
                                        <TableCell className="text-white">{call.recipient_number}</TableCell>
                                        <TableCell className="text-gray-300">
                                            {Math.floor(call.duration_seconds / 60)}m {call.duration_seconds % 60}s
                                        </TableCell>
                                        <TableCell className="text-yellow-400">{call.cost_credits} credits</TableCell>
                                        <TableCell className="text-gray-300 text-xs">
                                            {call.voice_provider === 'elevenlabs' && '⚡'}
                                            {call.voice_provider === 'deepgram' && '🌊'}
                                            {call.voice_provider === 'infobip' && '🎙️'}
                                        </TableCell>
                                        <TableCell>
                                            <span className={`px-2 py-1 rounded text-xs ${
                                                call.status === 'completed' ? 'bg-green-600' : 'bg-red-600'
                                            }`}>
                                                {call.status}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-gray-400 text-xs">
                                            {new Date(call.created_at).toLocaleString()}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                        {calls.length === 0 && (
                            <p className="text-center text-gray-400 py-8">No call history yet</p>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default ProfilePage;
