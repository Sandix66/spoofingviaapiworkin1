import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { CreditCard, Calendar, Check } from 'lucide-react';
import { toast } from 'sonner';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const TopupPage = () => {
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return token ? { Authorization: `Bearer ${token}` } : {};
    };

    const creditPackages = [
        { id: 'credit_100k', credits: 62, price: 100000, pricePerCredit: 1613 },
        { id: 'credit_200k', credits: 125, price: 200000, pricePerCredit: 1600 },
        { id: 'credit_300k', credits: 187, price: 300000, pricePerCredit: 1604 },
        { id: 'credit_400k', credits: 250, price: 400000, pricePerCredit: 1600 },
        { id: 'credit_500k', credits: 312, price: 500000, pricePerCredit: 1603, popular: true },
        { id: 'credit_600k', credits: 375, price: 600000, pricePerCredit: 1600 },
        { id: 'credit_700k', credits: 437, price: 700000, pricePerCredit: 1602 },
        { id: 'credit_800k', credits: 500, price: 800000, pricePerCredit: 1600 },
        { id: 'credit_900k', credits: 562, price: 900000, pricePerCredit: 1601 },
        { id: 'credit_1jt', credits: 625, price: 1000000, pricePerCredit: 1600 }
    ];

    const planPackages = [
        { id: 'plan_1day', days: 1, minutes: 400, price: 350000 },
        { id: 'plan_3days', days: 3, minutes: 1100, price: 950000 },
        { id: 'plan_7days', days: 7, minutes: 2300, price: 1950000 }
    ];

    const handleRequestTopup = async (packageType, packageId, amountIdr) => {
        setLoading(true);
        try {
            await axios.post(`${API}/user/topup/request`, null, {
                params: {
                    package_type: packageType,
                    package_id: packageId,
                    amount_idr: amountIdr
                },
                headers: getAuthHeaders()
            });
            toast.success('Top-up request submitted! Waiting for admin approval.');
        } catch (error) {
            toast.error(error.response?.data?.detail || 'Failed to submit request');
        } finally {
            setLoading(false);
        }
    };

    const formatIDR = (amount) => {
        return new Intl.NumberFormat('id-ID', {
            style: 'currency',
            currency: 'IDR',
            minimumFractionDigits: 0
        }).format(amount);
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-4xl font-bold text-white">Top-up</h1>
                    <p className="text-gray-400 mt-2">Purchase credits or daily plans</p>
                </div>
                <Button onClick={() => navigate('/profile')} variant="outline">My Plan</Button>
            </div>

            <Tabs defaultValue="credits" className="w-full">
                <TabsList className="grid w-full grid-cols-2 bg-gray-800">
                    <TabsTrigger value="credits">
                        <CreditCard className="w-4 h-4 mr-2" />
                        Credits
                    </TabsTrigger>
                    <TabsTrigger value="plans">
                        <Calendar className="w-4 h-4 mr-2" />
                        Daily Plans
                    </TabsTrigger>
                </TabsList>

                {/* Credits Tab */}
                <TabsContent value="credits" className="mt-6">
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                        {creditPackages.map((pkg) => (
                            <Card 
                                key={pkg.id}
                                className={`relative bg-gray-800/50 border-gray-700 hover:border-cyan-500/50 cursor-pointer transition ${
                                    pkg.popular ? 'border-purple-500/50' : ''
                                }`}
                                onClick={() => handleRequestTopup('credit', pkg.id, pkg.price)}
                            >
                                {pkg.popular && (
                                    <div className="absolute -top-3 right-3 bg-purple-600 text-white text-xs px-3 py-1 rounded-full">
                                        Popular
                                    </div>
                                )}
                                <CardContent className="p-6 text-center">
                                    <p className="text-5xl font-bold text-white mb-2">{pkg.credits}</p>
                                    <p className="text-sm text-gray-400 mb-4">CREDITS</p>
                                    <p className="text-2xl font-bold text-green-400 mb-1">
                                        {formatIDR(pkg.price)}
                                    </p>
                                    <p className="text-xs text-gray-500">{formatIDR(pkg.pricePerCredit)} per credit</p>
                                    <div className="mt-4 space-y-1 text-xs text-gray-400">
                                        <div className="flex items-center gap-1">
                                            <Check className="w-3 h-3 text-green-400" />
                                            Premium Voice Quality
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <Check className="w-3 h-3 text-green-400" />
                                            Advanced Features
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                </TabsContent>

                {/* Daily Plans Tab */}
                <TabsContent value="plans" className="mt-6">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
                        {planPackages.map((pkg) => (
                            <Card 
                                key={pkg.id}
                                className="bg-gray-800/50 border-gray-700 hover:border-cyan-500/50 cursor-pointer transition"
                                onClick={() => handleRequestTopup('plan', pkg.id, pkg.price)}
                            >
                                <CardHeader>
                                    <CardTitle className="text-center text-white text-2xl">
                                        {pkg.days} {pkg.days === 1 ? 'Day' : 'Days'}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="text-center space-y-4">
                                    <div>
                                        <p className="text-4xl font-bold text-cyan-400">{pkg.minutes}</p>
                                        <p className="text-sm text-gray-400">Minutes</p>
                                    </div>
                                    <div>
                                        <p className="text-3xl font-bold text-green-400">
                                            {formatIDR(pkg.price)}
                                        </p>
                                    </div>
                                    <div className="space-y-2 text-sm text-gray-300">
                                        <div className="flex items-center justify-center gap-2">
                                            <Check className="w-4 h-4 text-green-400" />
                                            {pkg.minutes} min FUP
                                        </div>
                                        <div className="flex items-center justify-center gap-2">
                                            <Check className="w-4 h-4 text-green-400" />
                                            Premium voices
                                        </div>
                                        <div className="flex items-center justify-center gap-2">
                                            <Check className="w-4 h-4 text-green-400" />
                                            All features
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        ))}
                    </div>
                    <div className="mt-8 p-4 bg-yellow-900/20 border border-yellow-500/30 rounded-lg max-w-4xl mx-auto">
                        <p className="text-sm text-yellow-200">
                            ℹ️ Daily plans use Fair Usage Policy (FUP). After reaching FUP limit, calls will deduct from your credits.
                        </p>
                    </div>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default TopupPage;
