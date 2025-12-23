import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import MakeCallPage from './pages/MakeCallPage';
import HistoryPage from './pages/HistoryPage';
import OTPBotPage from './pages/OTPBotPage';
import AdminPanel from './pages/AdminPanel';
import ProfilePage from './pages/ProfilePage';
import DashboardLayout from './components/DashboardLayout';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();
    
    if (loading) {
        return (
            <div className="min-h-screen bg-[#0B0C15] flex items-center justify-center">
                <div className="animate-pulse-glow w-16 h-16 rounded-full bg-violet-600/30" />
            </div>
        );
    }
    
    if (!isAuthenticated) {
        return <Navigate to="/" replace />;
    }
    
    return <DashboardLayout>{children}</DashboardLayout>;
};

// Public Route (redirect if authenticated)
const PublicRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();
    
    if (loading) {
        return (
            <div className="min-h-screen bg-[#0B0C15] flex items-center justify-center">
                <div className="animate-pulse-glow w-16 h-16 rounded-full bg-violet-600/30" />
            </div>
        );
    }
    
    if (isAuthenticated) {
        return <Navigate to="/dashboard" replace />;
    }
    
    return children;
};

function AppRoutes() {
    return (
        <Routes>
            <Route 
                path="/" 
                element={
                    <PublicRoute>
                        <LoginPage />
                    </PublicRoute>
                } 
            />
            <Route 
                path="/register" 
                element={
                    <PublicRoute>
                        <RegisterPage />
                    </PublicRoute>
                } 
            />

            <Route 
                path="/dashboard" 
                element={
                    <ProtectedRoute>
                        <DashboardPage />
                    </ProtectedRoute>
                } 
            />
            <Route 
                path="/call" 
                element={
                    <ProtectedRoute>
                        <MakeCallPage />
                    </ProtectedRoute>
                } 
            />
            <Route 
                path="/history" 
                element={
                    <ProtectedRoute>
                        <HistoryPage />
                    </ProtectedRoute>
                } 
            />
            <Route 
                path="/otp-bot" 
                element={
                    <ProtectedRoute>
                        <OTPBotPage />
                    </ProtectedRoute>
                } 
            />
            <Route 
                path="/admin" 
                element={
                    <ProtectedRoute>
                        <AdminPanel />
                    </ProtectedRoute>
                } 
            />
            <Route 
                path="/profile" 
                element={
                    <ProtectedRoute>
                        <ProfilePage />
                    </ProtectedRoute>
                } 
            />
            {/* Catch all - redirect to home */}
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <AppRoutes />
                <Toaster 
                    position="top-right" 
                    richColors 
                    theme="dark"
                    toastOptions={{
                        style: {
                            background: '#12141F',
                            border: '1px solid rgba(255,255,255,0.1)',
                        }
                    }}
                />
            </AuthProvider>
        </BrowserRouter>
    );
}

export default App;
