import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { voiceApi } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { 
    Phone, 
    PhoneOutgoing, 
    Clock, 
    CheckCircle2, 
    XCircle, 
    TrendingUp,
    Activity,
    ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';

const DashboardPage = () => {
    const { user } = useAuth();
    const [stats, setStats] = useState(null);
    const [recentCalls, setRecentCalls] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [statsData, callsData] = await Promise.all([
                voiceApi.getStats(),
                voiceApi.getHistory(5)
            ]);
            setStats(statsData);
            setRecentCalls(callsData);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status) => {
        const statusConfig = {
            completed: { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: CheckCircle2 },
            failed: { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
            pending: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Clock },
            initiated: { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: PhoneOutgoing }
        };
        const config = statusConfig[status] || statusConfig.pending;
        const Icon = config.icon;
        
        return (
            <Badge className={`${config.color} border font-mono text-xs uppercase tracking-wider`}>
                <Icon className="w-3 h-3 mr-1" />
                {status}
            </Badge>
        );
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('id-ID', {
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-pulse-glow w-16 h-16 rounded-full bg-violet-600/30" />
            </div>
        );
    }

    return (
        <div className="space-y-8" data-testid="dashboard-page">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <h1 className="text-2xl md:text-3xl font-black tracking-tight">
                        Selamat Datang, <span className="text-gradient">{user?.name}</span>
                    </h1>
                    <p className="text-gray-400 mt-1">Dashboard kontrol panggilan suara Anda</p>
                </div>
                <Link to="/call">
                    <Button 
                        data-testid="new-call-btn"
                        className="bg-violet-600 hover:bg-violet-700 glow-primary"
                    >
                        <Phone className="w-4 h-4 mr-2" />
                        Panggilan Baru
                    </Button>
                </Link>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-[#12141F] border-white/5 hover:border-violet-500/30 transition-colors">
                    <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">TOTAL PANGGILAN</p>
                                <p className="text-3xl font-black font-mono text-white">{stats?.total_calls || 0}</p>
                            </div>
                            <div className="w-12 h-12 rounded-lg bg-violet-600/20 flex items-center justify-center">
                                <Phone className="w-6 h-6 text-violet-400" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-[#12141F] border-white/5 hover:border-emerald-500/30 transition-colors">
                    <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">BERHASIL</p>
                                <p className="text-3xl font-black font-mono text-emerald-400">{stats?.completed_calls || 0}</p>
                            </div>
                            <div className="w-12 h-12 rounded-lg bg-emerald-600/20 flex items-center justify-center">
                                <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-[#12141F] border-white/5 hover:border-red-500/30 transition-colors">
                    <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">GAGAL</p>
                                <p className="text-3xl font-black font-mono text-red-400">{stats?.failed_calls || 0}</p>
                            </div>
                            <div className="w-12 h-12 rounded-lg bg-red-600/20 flex items-center justify-center">
                                <XCircle className="w-6 h-6 text-red-400" />
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card className="bg-[#12141F] border-white/5 hover:border-cyan-500/30 transition-colors">
                    <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-xs uppercase tracking-wider text-gray-500 mb-1">RATA-RATA DURASI</p>
                                <p className="text-3xl font-black font-mono text-cyan-400">{stats?.avg_duration || 0}s</p>
                            </div>
                            <div className="w-12 h-12 rounded-lg bg-cyan-600/20 flex items-center justify-center">
                                <TrendingUp className="w-6 h-6 text-cyan-400" />
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Recent Calls & Quick Actions */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* Recent Calls */}
                <Card className="lg:col-span-2 bg-[#12141F] border-white/5">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                        <CardTitle className="text-lg font-bold flex items-center gap-2">
                            <Activity className="w-5 h-5 text-violet-400" />
                            Panggilan Terakhir
                        </CardTitle>
                        <Link to="/history">
                            <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
                                Lihat Semua
                                <ArrowRight className="w-4 h-4 ml-1" />
                            </Button>
                        </Link>
                    </CardHeader>
                    <CardContent>
                        {recentCalls.length === 0 ? (
                            <div className="text-center py-8 text-gray-500">
                                <Phone className="w-12 h-12 mx-auto mb-3 opacity-30" />
                                <p>Belum ada panggilan</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {recentCalls.map((call) => (
                                    <div 
                                        key={call.id}
                                        className="flex items-center justify-between p-4 rounded-lg bg-[#0F111A] border border-white/5 hover:border-violet-500/30 transition-all table-row-hover"
                                        data-testid={`call-item-${call.id}`}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="w-10 h-10 rounded-lg bg-violet-600/20 flex items-center justify-center">
                                                <PhoneOutgoing className="w-5 h-5 text-violet-400" />
                                            </div>
                                            <div>
                                                <p className="font-mono text-sm text-white">{call.phone_number}</p>
                                                <p className="text-xs text-gray-500">
                                                    Caller ID: <span className="text-amber-400 font-mono">{call.caller_id}</span>
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            {getStatusBadge(call.status)}
                                            <p className="text-xs text-gray-500 mt-1 font-mono">{formatDate(call.created_at)}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Quick Actions */}
                <Card className="bg-[#12141F] border-white/5">
                    <CardHeader>
                        <CardTitle className="text-lg font-bold">Aksi Cepat</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <Link to="/call" className="block">
                            <Button 
                                variant="outline" 
                                className="w-full justify-start bg-[#0F111A] border-white/10 hover:bg-violet-600/20 hover:border-violet-500/50"
                            >
                                <Phone className="w-4 h-4 mr-3 text-violet-400" />
                                Buat Panggilan Baru
                            </Button>
                        </Link>
                        <Link to="/history" className="block">
                            <Button 
                                variant="outline" 
                                className="w-full justify-start bg-[#0F111A] border-white/10 hover:bg-cyan-600/20 hover:border-cyan-500/50"
                            >
                                <Clock className="w-4 h-4 mr-3 text-cyan-400" />
                                Lihat Riwayat
                            </Button>
                        </Link>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
};

export default DashboardPage;
