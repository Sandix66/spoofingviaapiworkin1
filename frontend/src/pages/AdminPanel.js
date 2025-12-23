import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Users, TrendingUp, Phone, CreditCard, Plus, Edit, Trash2, DollarSign, Key, Copy, Ticket } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AdminPanel = () => {
    const [users, setUsers] = useState([]);
    const [stats, setStats] = useState({});
    const [calls, setCalls] = useState([]);
    const [activities, setActivities] = useState([]);
    const [inviteCodes, setInviteCodes] = useState([]);
    const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
    const [isCreditDialogOpen, setIsCreditDialogOpen] = useState(false);
    const [isPasswordDialogOpen, setIsPasswordDialogOpen] = useState(false);
    const [isInviteDialogOpen, setIsInviteDialogOpen] = useState(false);
    const [selectedUser, setSelectedUser] = useState(null);
    const [generatedCode, setGeneratedCode] = useState(null);
    const navigate = useNavigate();

    const [newUser, setNewUser] = useState({
        email: '',
        password: '',
        name: '',
        role: 'user',
        credits: 10
    });

    const [creditAmount, setCreditAmount] = useState(0);
    const [newPassword, setNewPassword] = useState('');
    const [inviteCredits, setInviteCredits] = useState(10);


    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [usersRes, statsRes, callsRes, activitiesRes, inviteRes] = await Promise.all([
                axios.get(`${API}/admin/users`, { headers: getAuthHeaders() }),
                axios.get(`${API}/admin/stats`, { headers: getAuthHeaders() }),
                axios.get(`${API}/admin/calls?limit=50`, { headers: getAuthHeaders() }),
                axios.get(`${API}/admin/activities?limit=100`, { headers: getAuthHeaders() }),
                axios.get(`${API}/admin/invitation-codes`, { headers: getAuthHeaders() })
            ]);

            setUsers(usersRes.data.users || []);
            setStats(statsRes.data || {});
            setCalls(callsRes.data.calls || []);
            setActivities(activitiesRes.data.activities || []);
            setInviteCodes(inviteRes.data.codes || []);
        } catch (error) {
            if (error.response?.status === 403) {
                toast.error('Admin access required');
                navigate('/');
            } else {
                toast.error('Failed to load data');
            }
        }
    };

    const handleCreateUser = async () => {
        try {
            await axios.post(`${API}/admin/users`, newUser, { headers: getAuthHeaders() });
            toast.success('User created successfully!');
            setIsCreateDialogOpen(false);
            setNewUser({ email: '', password: '', name: '', role: 'user', credits: 10 });
            loadData();
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to create user');
        }
    };

    const handleDeleteUser = async (userId) => {
        if (!confirm('Are you sure you want to delete this user?')) return;
        
        try {
            await axios.delete(`${API}/admin/users/${userId}`, { headers: getAuthHeaders() });
            toast.success('User deleted');
            loadData();
        } catch (error) {
            toast.error('Failed to delete user');
        }
    };


    const handleResetPassword = async () => {
        if (!newPassword || newPassword.length < 4) {
            toast.error('Password must be at least 4 characters');
            return;
        }

        try {
            await axios.post(
                `${API}/admin/users/${selectedUser.id}/reset-password?new_password=${encodeURIComponent(newPassword)}`,
                {},
                { headers: getAuthHeaders() }
            );
            toast.success('Password reset successfully!');
            setIsPasswordDialogOpen(false);
            setNewPassword('');
            setSelectedUser(null);
        } catch (error) {
            toast.error('Failed to reset password');
        }
    };


    const handleGenerateInvite = async () => {
        try {
            const response = await axios.post(
                `${API}/admin/invitation-codes/generate?credits=${inviteCredits}`,
                {},
                { headers: getAuthHeaders() }
            );
            setGeneratedCode(response.data.code);
            toast.success('Invitation code generated!');
            loadData();
        } catch (error) {
            toast.error('Failed to generate code');
        }
    };

    const handleCopyCode = (code) => {
        navigator.clipboard.writeText(code);
        toast.success('Code copied to clipboard!');
    };


    const handleDeleteInviteCode = async (codeId) => {
        if (!confirm('Delete this invitation code?')) return;
        
        try {
            await axios.delete(`${API}/admin/invitation-codes/${codeId}`, { headers: getAuthHeaders() });
            toast.success('Invitation code deleted');
            loadData();
        } catch (error) {
            toast.error('Failed to delete code');
        }
    };




    const handleAddCredits = async () => {
        try {
            await axios.post(
                `${API}/admin/users/${selectedUser.id}/credits`,
                { amount: parseFloat(creditAmount), reason: 'Manual top-up by admin' },
                { headers: getAuthHeaders() }
            );
            toast.success(`${creditAmount} credits added!`);
            setIsCreditDialogOpen(false);
            setCreditAmount(0);
            setSelectedUser(null);
            loadData();
        } catch (error) {
            toast.error('Failed to add credits');
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-white">Admin Panel</h1>
                        <p className="text-gray-400 mt-1">Manage users, credits, and monitor activities</p>
                    </div>
                    <Button onClick={() => navigate('/')} variant="outline">Back to OTP Bot</Button>
                </div>

                {/* Stats Cards */}
                <div className="grid grid-cols-4 gap-4">
                    <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
                                <Users className="w-4 h-4" />
                                Total Users
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">{stats.total_users || 0}</div>
                            <p className="text-xs text-green-400 mt-1">{stats.active_users || 0} active</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
                                <Phone className="w-4 h-4" />
                                Calls Today
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">{stats.total_calls_today || 0}</div>
                            <p className="text-xs text-gray-400 mt-1">{stats.total_calls_all_time || 0} total</p>
                        </CardContent>
                    </Card>

                    <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
                                <CreditCard className="w-4 h-4" />
                                Credits Distributed
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">{stats.total_credits_distributed?.toFixed(0) || 0}</div>
                        </CardContent>
                    </Card>

                    <Card className="bg-gray-800 border-gray-700">
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
                                <TrendingUp className="w-4 h-4" />
                                Credits Spent
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-3xl font-bold text-white">{stats.total_credits_spent?.toFixed(0) || 0}</div>
                        </CardContent>
                    </Card>
                </div>



                {/* Invitation Codes */}
                <Card className="bg-gray-800 border-gray-700">
                    <CardHeader>
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-white flex items-center gap-2">
                                <Ticket className="w-5 h-5" />
                                Invitation Codes
                            </CardTitle>
                            <Dialog open={isInviteDialogOpen} onOpenChange={setIsInviteDialogOpen}>
                                <DialogTrigger asChild>
                                    <Button className="bg-purple-600 hover:bg-purple-700">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Generate Code
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="bg-gray-800 border-gray-700">
                                    <DialogHeader>
                                        <DialogTitle className="text-white">Generate Invitation Code</DialogTitle>
                                    </DialogHeader>
                                    <div className="space-y-4 mt-4">
                                        <div>
                                            <Label className="text-gray-300">Credits for New User</Label>
                                            <Input
                                                type="number"
                                                value={inviteCredits}
                                                onChange={(e) => setInviteCredits(e.target.value)}
                                                className="bg-gray-900 border-gray-600 text-white"
                                                placeholder="10"
                                            />
                                        </div>
                                        <Button onClick={handleGenerateInvite} className="w-full bg-purple-600">
                                            Generate Code
                                        </Button>
                                        {generatedCode && (
                                            <div className="p-4 bg-green-900/20 border border-green-500/30 rounded">
                                                <p className="text-sm text-gray-300 mb-2">New Invitation Code:</p>
                                                <div className="flex items-center gap-2">
                                                    <code className="text-2xl font-mono font-bold text-green-400 tracking-widest">
                                                        {generatedCode}
                                                    </code>
                                                    <Button
                                                        size="sm"
                                                        onClick={() => handleCopyCode(generatedCode)}
                                                        className="bg-green-600"
                                                    >
                                                        <Copy className="w-3 h-3" />
                                                    </Button>
                                                </div>
                                                <p className="text-xs text-gray-400 mt-2">Share this code with new users to register</p>
                                            </div>
                                        )}
                                    </div>
                                </DialogContent>
                            </Dialog>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                            {inviteCodes.filter(code => !code.is_used).slice(0, 9).map((code) => {
                                // Find creator name
                                const creator = users.find(u => u.id === code.created_by);
                                const creatorName = creator?.name || (code.created_by_role === 'admin' ? 'Admin' : 'Unknown');
                                
                                return (
                                <div
                                    key={code.id}
                                    className="p-4 rounded-lg border bg-purple-900/20 border-purple-500/30"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <code className="text-lg font-mono font-bold text-white tracking-wider">
                                            {code.code}
                                        </code>
                                        <div className="flex gap-1">
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => handleCopyCode(code.code)}
                                                className="h-6 w-6 p-0"
                                            >
                                                <Copy className="w-3 h-3" />
                                            </Button>
                                            <Button
                                                size="sm"
                                                variant="ghost"
                                                onClick={() => handleDeleteInviteCode(code.id)}
                                                className="h-6 w-6 p-0 text-red-400 hover:text-red-300"
                                            >
                                                <Trash2 className="w-3 h-3" />
                                            </Button>
                                        </div>
                                    </div>
                                    <div className="space-y-1 text-xs">
                                        <p className="text-gray-400">
                                            Created by: <span className="text-purple-400 font-semibold">{creatorName}</span>
                                        </p>
                                        <p className="text-gray-400">
                                            Status: <span className="text-green-400">Available</span>
                                        </p>
                                    </div>
                                </div>
                                );
                            })}
                        </div>
                        {inviteCodes.filter(c => !c.is_used).length === 0 && (
                            <p className="text-center text-gray-400 py-8">No available invitation codes</p>
                        )}
                    </CardContent>
                </Card>

                {/* User Management */}
                <Card className="bg-gray-800 border-gray-700">
                    <CardHeader>
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-white">User Management</CardTitle>
                            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
                                <DialogTrigger asChild>
                                    <Button className="bg-blue-600 hover:bg-blue-700">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Create User
                                    </Button>
                                </DialogTrigger>
                                <DialogContent className="bg-gray-800 border-gray-700">
                                    <DialogHeader>
                                        <DialogTitle className="text-white">Create New User</DialogTitle>
                                    </DialogHeader>
                                    <div className="space-y-4 mt-4">
                                        <div>
                                            <Label className="text-gray-300">Email</Label>
                                            <Input
                                                value={newUser.email}
                                                onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                                                className="bg-gray-900 border-gray-600 text-white"
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-gray-300">Name</Label>
                                            <Input
                                                value={newUser.name}
                                                onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                                                className="bg-gray-900 border-gray-600 text-white"
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-gray-300">Password</Label>
                                            <Input
                                                type="password"
                                                value={newUser.password}
                                                onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                                                className="bg-gray-900 border-gray-600 text-white"
                                            />
                                        </div>
                                        <div>
                                            <Label className="text-gray-300">Initial Credits</Label>
                                            <Input
                                                type="number"
                                                value={newUser.credits}
                                                onChange={(e) => setNewUser({...newUser, credits: parseFloat(e.target.value) || 0})}
                                                className="bg-gray-900 border-gray-600 text-white"
                                            />
                                        </div>
                                        <Button onClick={handleCreateUser} className="w-full bg-blue-600">Create</Button>
                                    </div>
                                </DialogContent>
                            </Dialog>
                        </div>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow className="border-gray-700">
                                    <TableHead className="text-gray-400">No</TableHead>
                                    <TableHead className="text-gray-400">Username</TableHead>
                                    <TableHead className="text-gray-400">Email</TableHead>
                                    <TableHead className="text-gray-400">Role</TableHead>
                                    <TableHead className="text-gray-400">Credits</TableHead>
                                    <TableHead className="text-gray-400">Status</TableHead>
                                    <TableHead className="text-gray-400">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {users.map((user, index) => (
                                    <TableRow key={user.id} className="border-gray-700">
                                        <TableCell className="text-gray-400">{index + 1}</TableCell>
                                        <TableCell className="text-white font-medium">{user.name}</TableCell>
                                        <TableCell className="text-gray-300">{user.email}</TableCell>
                                        <TableCell>
                                            <span className={`px-2 py-1 rounded text-xs ${user.role === 'admin' ? 'bg-purple-600' : 'bg-blue-600'}`}>
                                                {user.role}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-yellow-400 font-bold">{user.credits?.toFixed(0)}</TableCell>
                                        <TableCell>
                                            <span className={`px-2 py-1 rounded text-xs ${user.is_active ? 'bg-green-600' : 'bg-red-600'}`}>
                                                {user.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </TableCell>
                                        <TableCell>
                                            <div className="flex gap-2">
                                                <Button
                                                    size="sm"
                                                    onClick={() => {
                                                        setSelectedUser(user);
                                                        setIsCreditDialogOpen(true);
                                                    }}
                                                    className="bg-green-600 hover:bg-green-700"
                                                >
                                                    <DollarSign className="w-3 h-3" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    onClick={() => {
                                                        setSelectedUser(user);
                                                        setIsPasswordDialogOpen(true);
                                                    }}
                                                    className="bg-purple-600 hover:bg-purple-700"
                                                >
                                                    <Key className="w-3 h-3" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    onClick={() => handleDeleteUser(user.id)}
                                                    className="bg-red-600 hover:bg-red-700"
                                                    disabled={user.role === 'admin'}
                                                >
                                                    <Trash2 className="w-3 h-3" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>

                {/* Credit Dialog */}
                <Dialog open={isCreditDialogOpen} onOpenChange={setIsCreditDialogOpen}>
                    <DialogContent className="bg-gray-800 border-gray-700">
                        <DialogHeader>
                            <DialogTitle className="text-white">Add Credits to {selectedUser?.name}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 mt-4">
                            <div>
                                <Label className="text-gray-300">Current Credits: {selectedUser?.credits}</Label>
                            </div>
                            <div>
                                <Label className="text-gray-300">Amount to Add</Label>
                                <Input
                                    type="number"
                                    value={creditAmount}
                                    onChange={(e) => setCreditAmount(e.target.value)}
                                    className="bg-gray-900 border-gray-600 text-white"
                                    placeholder="Enter amount"
                                />
                            </div>
                            <Button onClick={handleAddCredits} className="w-full bg-green-600">Add Credits</Button>
                        </div>
                    </DialogContent>
                </Dialog>



                {/* Reset Password Dialog */}
                <Dialog open={isPasswordDialogOpen} onOpenChange={setIsPasswordDialogOpen}>
                    <DialogContent className="bg-gray-800 border-gray-700">
                        <DialogHeader>
                            <DialogTitle className="text-white">Reset Password for {selectedUser?.name}</DialogTitle>
                        </DialogHeader>
                        <div className="space-y-4 mt-4">
                            <div>
                                <Label className="text-gray-300">Email: {selectedUser?.email}</Label>
                            </div>
                            <div>
                                <Label className="text-gray-300">New Password</Label>
                                <Input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="bg-gray-900 border-gray-600 text-white"
                                    placeholder="Enter new password"
                                />
                            </div>
                            <Button onClick={handleResetPassword} className="w-full bg-purple-600">Reset Password</Button>
                        </div>
                    </DialogContent>
                </Dialog>

                {/* Recent Calls */}
                <Card className="bg-gray-800 border-gray-700">
                    <CardHeader>
                        <CardTitle className="text-white">Recent Calls</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow className="border-gray-700">
                                    <TableHead className="text-gray-400">User</TableHead>
                                    <TableHead className="text-gray-400">Recipient</TableHead>
                                    <TableHead className="text-gray-400">Duration</TableHead>
                                    <TableHead className="text-gray-400">Cost</TableHead>
                                    <TableHead className="text-gray-400">Status</TableHead>
                                    <TableHead className="text-gray-400">Time</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {calls.slice(0, 10).map(call => (
                                    <TableRow key={call.id} className="border-gray-700">
                                        <TableCell className="text-gray-300">
                                            {users.find(u => u.id === call.user_id)?.email || 'Unknown'}
                                        </TableCell>
                                        <TableCell className="text-white">{call.recipient_number}</TableCell>
                                        <TableCell className="text-gray-300">{Math.floor(call.duration_seconds / 60)}m {call.duration_seconds % 60}s</TableCell>
                                        <TableCell className="text-yellow-400">{call.cost_credits} credits</TableCell>
                                        <TableCell>
                                            <span className={`px-2 py-1 rounded text-xs ${call.status === 'completed' ? 'bg-green-600' : 'bg-red-600'}`}>
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
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default AdminPanel;
