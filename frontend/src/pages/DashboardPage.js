import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Phone, CheckCircle2, XCircle, TrendingUp, Clock, DollarSign, Activity } from 'lucide-react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DashboardPage = () => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    useEffect(() => {
        loadStats();
        const interval = setInterval(loadStats, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const loadStats = async () => {
        try {
            const response = await axios.get(`${API}/user/dashboard-stats`, { headers: getAuthHeaders() });
            setStats(response.data);
        } catch (error) {
            toast.error('Failed to load dashboard stats');
        } finally {
            setLoading(false);
        }
    };

    const formatDuration = (seconds) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    };

    if (loading || !stats) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    const statsCards = [
        {
            title: 'Total Calls',
            value: stats.total_calls,
            icon: Phone,
            color: 'text-violet-400',
            bgColor: 'bg-violet-500/10'
        },
        {
            title: 'Successful',
            value: stats.successful,
            subtitle: `${stats.success_rate}%`,
            icon: CheckCircle2,
            color: 'text-green-400',
            bgColor: 'bg-green-500/10'
        },
        {
            title: 'Failed',
            value: stats.failed,
            icon: XCircle,
            color: 'text-red-400',
            bgColor: 'bg-red-500/10'
        },
        {
            title: 'OTP Captured',
            value: stats.otp_captured,
            subtitle: 'Total OTPs',
            icon: TrendingUp,
            color: 'text-cyan-400',
            bgColor: 'bg-cyan-500/10'
        },
        {
            title: 'Avg Duration',
            value: `${stats.avg_duration_seconds}s`,
            icon: Clock,
            color: 'text-orange-400',
            bgColor: 'bg-orange-500/10'
        },
        {
            title: 'Total Cost',
            value: `$${(stats.total_cost_credits * 1.0).toFixed(2)}`,
            icon: DollarSign,
            color: 'text-yellow-400',
            bgColor: 'bg-yellow-500/10'
        }
    ];

    const statusBreakdown = [
        { label: 'Answered', count: stats.successful, icon: CheckCircle2, color: 'text-green-400' },
        { label: 'Failed', count: stats.failed, icon: XCircle, color: 'text-red-400' },
        { label: 'Voicemail', count: stats.voicemail, icon: Phone, color: 'text-purple-400' },
        { label: 'Busy', count: stats.busy, icon: Phone, color: 'text-yellow-400' },
        { label: 'No Answer', count: stats.no_answer, icon: XCircle, color: 'text-orange-400' },
        { label: 'Fax', count: stats.fax, icon: XCircle, color: 'text-gray-400' },
        { label: 'Music', count: stats.music, icon: XCircle, color: 'text-blue-400' }
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-4xl font-bold text-white">Dashboard</h1>
                <p className="text-gray-400 mt-2">System calls overview</p>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                {statsCards.map((stat, index) => (
                    <Card key={index} className="bg-gray-800/50 border-gray-700 backdrop-blur">
                        <CardContent className="p-6">
                            <div className="flex items-center justify-between mb-3">
                                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                                    <stat.icon className={`w-5 h-5 ${stat.color}`} />
                                </div>
                            </div>
                            <div>
                                <p className="text-sm text-gray-400 mb-1">{stat.title}</p>
                                <p className="text-3xl font-bold text-white">{stat.value}</p>
                                {stat.subtitle && (
                                    <p className="text-sm text-green-400 mt-1">{stat.subtitle}</p>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            {/* Bottom Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Status Breakdown */}
                <Card className="bg-gray-800/50 border-gray-700 backdrop-blur">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Activity className="w-5 h-5" />
                            Status Breakdown
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {statusBreakdown.map((item, index) => (
                            <div key={index} className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <item.icon className={`w-5 h-5 ${item.color}`} />
                                    <span className="text-gray-300">{item.label}</span>
                                </div>
                                <span className="text-2xl font-bold text-white">{item.count}</span>
                            </div>
                        ))}
                    </CardContent>
                </Card>

                {/* Performance Metrics */}
                <Card className="bg-gray-800/50 border-gray-700 backdrop-blur">
                    <CardHeader>
                        <CardTitle className="text-white flex items-center gap-2">
                            <TrendingUp className="w-5 h-5" />
                            Performance Metrics
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <Clock className="w-4 h-4 text-gray-400" />
                                <span className="text-sm text-gray-400">Total Duration</span>
                            </div>
                            <p className="text-4xl font-bold text-white">{formatDuration(stats.total_duration_seconds)}</p>
                        </div>
                        
                        <div>
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm text-gray-400">Success Rate</span>
                            </div>
                            <div className="relative w-full h-8 bg-gray-700 rounded-full overflow-hidden">
                                <div 
                                    className="absolute top-0 left-0 h-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-500"
                                    style={{ width: `${stats.success_rate}%` }}
                                />
                            </div>
                            <p className="text-right text-2xl font-bold text-green-400 mt-2">{stats.success_rate}%</p>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default DashboardPage;
