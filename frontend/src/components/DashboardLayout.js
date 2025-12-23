import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/button';
import { 
    LayoutDashboard, 
    Phone, 
    History, 
    LogOut,
    Menu,
    X,
    User,
    Bot,
    Shield,
    CreditCard
} from 'lucide-react';
import { useState } from 'react';

const DashboardLayout = ({ children }) => {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const handleLogout = () => {
        logout();
        navigate('/');
    };

    const navItems = [
        { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { to: '/call', icon: Phone, label: 'Buat Panggilan' },
        { to: '/otp-bot', icon: Bot, label: 'OTP Bot' },
        { to: '/history', icon: History, label: 'Riwayat' },
        ...(user?.role === 'admin' ? [{ to: '/admin', icon: Shield, label: 'Admin Panel' }] : []),
        { to: '/profile', icon: User, label: 'Profile' },
    ];

    const NavItem = ({ to, icon: Icon, label }) => (
        <NavLink
            to={to}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                    isActive
                        ? 'bg-violet-600/20 text-violet-400 border border-violet-500/30'
                        : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`
            }
        >
            <Icon className="w-5 h-5" />
            <span className="font-medium">{label}</span>
        </NavLink>
    );

    return (
        <div className="min-h-screen bg-[#0B0C15]">
            {/* Mobile Header */}
            <header className="lg:hidden fixed top-0 left-0 right-0 z-50 glass border-b border-white/5">
                <div className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center">
                            <Phone className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-bold text-lg">VoiceSpoof</span>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        data-testid="mobile-menu-btn"
                    >
                        {sidebarOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                    </Button>
                </div>
            </header>

            {/* Sidebar */}
            <aside className={`
                fixed inset-y-0 left-0 z-40 w-64 glass border-r border-white/5 transform transition-transform duration-200 ease-in-out
                lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
            `}>
                <div className="flex flex-col h-full">
                    {/* Logo */}
                    <div className="p-6 border-b border-white/5">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center glow-primary">
                                <Phone className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h1 className="font-black text-xl">
                                    <span className="text-gradient">Voice</span>
                                    <span className="text-white">Spoof</span>
                                </h1>
                                <p className="text-xs text-gray-500">Campus Project</p>
                            </div>
                        </div>
                    </div>

                    {/* Navigation */}
                    <nav className="flex-1 p-4 space-y-2">
                        {navItems.map((item) => (
                            <NavItem key={item.to} {...item} />
                        ))}
                    </nav>

                    {/* User & Credits & Logout */}
                    <div className="p-4 border-t border-white/5 space-y-3">
                        {/* Credits Display */}
                        <div className="px-4 py-3 rounded-lg bg-gradient-to-r from-yellow-600/20 to-orange-600/20 border border-yellow-500/30">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <CreditCard className="w-4 h-4 text-yellow-400" />
                                    <span className="text-xs text-yellow-100">Credits</span>
                                </div>
                                <span className="text-lg font-bold text-yellow-400">{user?.credits?.toFixed(0) || 0}</span>
                            </div>
                            <p className="text-xs text-yellow-200/60 mt-1">1 credit = 1 minute</p>
                        </div>

                        {/* User Info */}
                        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-[#0F111A]">
                            <div className="w-8 h-8 rounded-full bg-violet-600/30 flex items-center justify-center">
                                <User className="w-4 h-4 text-violet-400" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-white truncate">{user?.name}</p>
                                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                                {user?.role === 'admin' && (
                                    <span className="text-xs px-2 py-0.5 bg-purple-600 rounded text-white mt-1 inline-block">Admin</span>
                                )}
                            </div>
                        </div>
                        <Button
                            variant="ghost"
                            onClick={handleLogout}
                            className="w-full justify-start text-gray-400 hover:text-red-400 hover:bg-red-500/10"
                            data-testid="logout-btn"
                        >
                            <LogOut className="w-4 h-4 mr-2" />
                            Keluar
                        </Button>
                    </div>
                </div>
            </aside>

            {/* Overlay */}
            {sidebarOpen && (
                <div 
                    className="fixed inset-0 z-30 bg-black/50 lg:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Main Content */}
            <main className="lg:pl-64 pt-16 lg:pt-0">
                <div className="p-6 lg:p-10 min-h-screen">
                    {children}
                </div>
            </main>
        </div>
    );
};

export default DashboardLayout;
