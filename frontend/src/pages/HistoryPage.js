import React, { useState, useEffect } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Phone, Download, RefreshCw, Search } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const HistoryPage = () => {
    const [calls, setCalls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    useEffect(() => {
        fetchCalls();
    }, []);

    const fetchCalls = async () => {
        setLoading(true);
        try {
            const response = await fetch(`${API}/user/calls?limit=100`, {
                headers: getAuthHeaders()
            });
            const data = await response.json();
            setCalls(data.calls || []);
        } catch (error) {
            console.error('Error fetching calls:', error);
            toast.error('Failed to load call history');
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('en-US', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getStatusBadge = (status) => {
        const statusConfig = {
            completed: { label: 'Completed', color: 'bg-green-600' },
            voicemail_detected: { label: 'Voicemail', color: 'bg-orange-600' },
            fax_detected: { label: 'Fax', color: 'bg-gray-600' },
            beep_detected: { label: 'Beep', color: 'bg-purple-600' },
            music_detected: { label: 'Music', color: 'bg-blue-600' },
            failed: { label: 'Failed', color: 'bg-red-600' },
            busy: { label: 'Busy', color: 'bg-yellow-600' },
            no_answer: { label: 'No Answer', color: 'bg-gray-500' },
            initiated: { label: 'Initiated', color: 'bg-blue-500' }
        };
        const config = statusConfig[status] || { label: status, color: 'bg-gray-600' };
        return (
            <span className={`px-3 py-1 rounded text-white text-xs ${config.color}`}>
                {config.label}
            </span>
        );
    };

    const getAMDBadge = (amd) => {
        if (!amd) return null;
        const amdConfig = {
            HUMAN: { label: 'Human', color: 'bg-green-600' },
            MACHINE: { label: 'Voicemail', color: 'bg-orange-600' },
            SILENCE: { label: 'Silence', color: 'bg-gray-600' },
            FAX: { label: 'Fax', color: 'bg-gray-600' },
            BEEP: { label: 'Beep', color: 'bg-purple-600' }
        };
        const config = amdConfig[amd] || { label: amd, color: 'bg-gray-600' };
        return (
            <span className={`px-3 py-1 rounded text-white text-xs ${config.color}`}>
                {config.label}
            </span>
        );
    };

    // Filter calls
    const filteredCalls = calls.filter(call => {
        const matchesSearch = (call.recipient_number || '').includes(searchQuery);
        const matchesStatus = statusFilter === 'all' || call.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-4xl font-bold">
                    <span className="text-gradient">Call History</span>
                </h1>
                <p className="text-gray-400 mt-2">View all your calls</p>
            </div>

            {/* Search & Filter */}
            <div className="flex gap-4">
                <div className="flex-1 relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <Input
                        placeholder="Search phone number or message..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10 bg-gray-800/50 border-gray-700"
                    />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-40 bg-gray-800/50 border-gray-700">
                        <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-700">
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="completed">Completed</SelectItem>
                        <SelectItem value="voicemail_detected">Voicemail</SelectItem>
                        <SelectItem value="failed">Failed</SelectItem>
                    </SelectContent>
                </Select>
                <Button onClick={fetchCalls} variant="outline" className="border-gray-700">
                    <RefreshCw className="w-4 h-4" />
                </Button>
            </div>

            {/* Call Cards */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-white">Call Log</h2>
                    <span className="text-sm text-gray-400">{filteredCalls.length} calls</span>
                </div>

                {loading ? (
                    <div className="text-center py-12">
                        <div className="animate-spin w-12 h-12 border-4 border-violet-500 border-t-transparent rounded-full mx-auto" />
                    </div>
                ) : filteredCalls.length === 0 ? (
                    <div className="text-center py-12">
                        <Phone className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <p className="text-lg text-gray-400">No data</p>
                        <p className="text-sm text-gray-500">No calls match your filter</p>
                    </div>
                ) : (
                    filteredCalls.map((call) => (
                        <Card key={call.id} className="bg-gray-800/50 border-gray-700 backdrop-blur">
                            <CardContent className="p-6">
                                <div className="flex items-start justify-between">
                                    {/* Left: Call Info */}
                                    <div className="flex-1">
                                        <div className="flex items-center gap-3 mb-3">
                                            <Phone className="w-5 h-5 text-purple-400" />
                                            <div>
                                                <p className="text-lg font-mono text-white">{call.recipient_number}</p>
                                            </div>
                                        </div>
                                        
                                        <div className="text-sm text-gray-400 space-y-1">
                                            <p>ID: {call.session_id}</p>
                                            <p>{formatDate(call.created_at)} • Cost: ${(call.cost_credits * 1.0).toFixed(2)}</p>
                                            {call.otp_captured && (
                                                <p className="text-green-400 font-bold mt-2">
                                                    🔑 OTP Captured: {call.otp_captured}
                                                </p>
                                            )}
                                        </div>
                                    </div>

                                    {/* Right: Status & Actions */}
                                    <div className="flex flex-col items-end gap-2">
                                        {getStatusBadge(call.status)}
                                        {call.amd_result && getAMDBadge(call.amd_result)}
                                        
                                        {call.recording_file_id && (
                                            <Button
                                                size="sm"
                                                className="bg-green-600 hover:bg-green-700 mt-2"
                                                onClick={() => {
                                                    window.open(`${API}/otp/recording/download/${call.recording_file_id}`, '_blank');
                                                }}
                                            >
                                                <Download className="w-3 h-3 mr-2" />
                                                Download
                                            </Button>
                                        )}
                                    </div>
                                </div>

                                {/* Recording Player (if available) */}
                                {call.recording_file_id && (
                                    <div className="mt-4 pt-4 border-t border-gray-700">
                                        <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                                            <span>🎙️ Recording:</span>
                                            <span className="text-xs font-mono text-gray-500">{call.recording_file_id}.wav</span>
                                        </div>
                                        <audio 
                                            controls 
                                            className="w-full h-10"
                                            src={`${API}/otp/recording/play/${call.recording_file_id}?token=${localStorage.getItem('token')}`}
                                        />
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    ))
                )}
            </div>
        </div>
    );
};

export default HistoryPage;
