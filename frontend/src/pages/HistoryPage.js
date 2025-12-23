import React, { useState, useEffect } from 'react';
import { voiceApi } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '../components/ui/table';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '../components/ui/select';
import { 
    History, 
    Search, 
    ChevronLeft, 
    ChevronRight,
    PhoneOutgoing,
    CheckCircle2,
    XCircle,
    Clock,
    Filter
} from 'lucide-react';

const HistoryPage = () => {
    const [calls, setCalls] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [page, setPage] = useState(0);
    const [pageSize] = useState(10);

    useEffect(() => {
        fetchCalls();
    }, [page]);

    const fetchCalls = async () => {
        setLoading(true);
        try {
            const data = await voiceApi.getHistory(100, 0);
            setCalls(data);
        } catch (error) {
            console.error('Error fetching calls:', error);
        } finally {
            setLoading(false);
        }
    };

    const getStatusBadge = (status) => {
        const statusConfig = {
            completed: { 
                color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', 
                icon: CheckCircle2,
                label: 'Selesai'
            },
            failed: { 
                color: 'bg-red-500/20 text-red-400 border-red-500/30', 
                icon: XCircle,
                label: 'Gagal'
            },
            pending: { 
                color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', 
                icon: Clock,
                label: 'Pending'
            },
            initiated: { 
                color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', 
                icon: PhoneOutgoing,
                label: 'Diinisiasi'
            }
        };
        const config = statusConfig[status] || statusConfig.pending;
        const Icon = config.icon;
        
        return (
            <Badge className={`${config.color} border font-mono text-xs uppercase tracking-wider`}>
                <Icon className="w-3 h-3 mr-1" />
                {config.label}
            </Badge>
        );
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleString('id-ID', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Filter calls
    const filteredCalls = calls.filter(call => {
        const matchesSearch = 
            call.phone_number.includes(searchQuery) ||
            call.caller_id.includes(searchQuery) ||
            call.message_text.toLowerCase().includes(searchQuery.toLowerCase());
        
        const matchesStatus = statusFilter === 'all' || call.status === statusFilter;
        
        return matchesSearch && matchesStatus;
    });

    // Pagination
    const totalPages = Math.ceil(filteredCalls.length / pageSize);
    const paginatedCalls = filteredCalls.slice(page * pageSize, (page + 1) * pageSize);

    return (
        <div className="space-y-6" data-testid="history-page">
            {/* Header */}
            <div>
                <h1 className="text-2xl md:text-3xl font-black tracking-tight flex items-center gap-3">
                    <History className="w-8 h-8 text-cyan-400" />
                    <span>Call <span className="text-gradient">History</span></span>
                </h1>
                <p className="text-gray-400 mt-1">View all your calls</p>
            </div>

            {/* Filters */}
            <Card className="bg-[#12141F] border-white/5">
                <CardContent className="p-4">
                    <div className="flex flex-col md:flex-row gap-4">
                        <div className="flex-1 relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
                            <Input
                                data-testid="search-input"
                                placeholder="Search phone number or message..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-10 bg-[#0F111A] border-white/10"
                            />
                        </div>
                        <div className="flex gap-3">
                            <Select value={statusFilter} onValueChange={setStatusFilter}>
                                <SelectTrigger data-testid="status-filter" className="w-[150px] bg-[#0F111A] border-white/10">
                                    <Filter className="w-4 h-4 mr-2" />
                                    <SelectValue placeholder="Status" />
                                </SelectTrigger>
                                <SelectContent className="bg-[#12141F] border-white/10">
                                    <SelectItem value="all">All</SelectItem>
                                    <SelectItem value="completed">Selesai</SelectItem>
                                    <SelectItem value="initiated">Diinisiasi</SelectItem>
                                    <SelectItem value="failed">Gagal</SelectItem>
                                    <SelectItem value="pending">Pending</SelectItem>
                                </SelectContent>
                            </Select>
                            <Button 
                                variant="outline" 
                                onClick={fetchCalls}
                                className="bg-[#0F111A] border-white/10"
                            >
                                Refresh
                            </Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Table */}
            <Card className="bg-[#12141F] border-white/5">
                <CardHeader className="pb-0">
                    <CardTitle className="text-lg flex items-center justify-between">
                        <span>Log Panggilan</span>
                        <span className="text-sm font-normal text-gray-500">
                            {filteredCalls.length} calls
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                    {loading ? (
                        <div className="flex items-center justify-center py-16">
                            <div className="animate-pulse-glow w-12 h-12 rounded-full bg-violet-600/30" />
                        </div>
                    ) : filteredCalls.length === 0 ? (
                        <div className="text-center py-16 text-gray-500">
                            <History className="w-16 h-16 mx-auto mb-4 opacity-30" />
                            <p className="text-lg">No data</p>
                            <p className="text-sm">No calls match your filter</p>
                        </div>
                    ) : (
                        <>
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow className="border-white/5 hover:bg-transparent">
                                            <TableHead className="text-xs uppercase tracking-wider text-gray-500">Nomor Tujuan</TableHead>
                                            <TableHead className="text-xs uppercase tracking-wider text-gray-500">Caller ID</TableHead>
                                            <TableHead className="text-xs uppercase tracking-wider text-gray-500">Pesan</TableHead>
                                            <TableHead className="text-xs uppercase tracking-wider text-gray-500">Status</TableHead>
                                            <TableHead className="text-xs uppercase tracking-wider text-gray-500">Durasi</TableHead>
                                            <TableHead className="text-xs uppercase tracking-wider text-gray-500">Tanggal</TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {paginatedCalls.map((call) => (
                                            <TableRow 
                                                key={call.id} 
                                                className="border-white/5 table-row-hover cursor-pointer"
                                                data-testid={`history-row-${call.id}`}
                                            >
                                                <TableCell className="font-mono text-sm text-white">
                                                    {call.phone_number}
                                                </TableCell>
                                                <TableCell className="font-mono text-sm text-amber-400">
                                                    {call.caller_id}
                                                </TableCell>
                                                <TableCell className="max-w-[200px] truncate text-sm text-gray-400">
                                                    {call.message_text}
                                                </TableCell>
                                                <TableCell>
                                                    {getStatusBadge(call.status)}
                                                </TableCell>
                                                <TableCell className="font-mono text-sm text-gray-400">
                                                    {call.duration_seconds ? `${call.duration_seconds}s` : '-'}
                                                </TableCell>
                                                <TableCell className="font-mono text-xs text-gray-500">
                                                    {formatDate(call.created_at)}
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>

                            {/* Pagination */}
                            <div className="flex items-center justify-between p-4 border-t border-white/5">
                                <p className="text-sm text-gray-500">
                                    Halaman {page + 1} dari {totalPages || 1}
                                </p>
                                <div className="flex gap-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setPage(p => Math.max(0, p - 1))}
                                        disabled={page === 0}
                                        className="bg-[#0F111A] border-white/10"
                                        data-testid="prev-page-btn"
                                    >
                                        <ChevronLeft className="w-4 h-4 mr-1" />
                                        Prev
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => setPage(p => p + 1)}
                                        disabled={page >= totalPages - 1}
                                        className="bg-[#0F111A] border-white/10"
                                        data-testid="next-page-btn"
                                    >
                                        Next
                                        <ChevronRight className="w-4 h-4 ml-1" />
                                    </Button>
                                </div>
                            </div>
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default HistoryPage;
