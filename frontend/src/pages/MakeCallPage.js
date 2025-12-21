import React, { useState } from 'react';
import { voiceApi } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Slider } from '../components/ui/slider';
import { Badge } from '../components/ui/badge';
import { 
    Phone, 
    PhoneOutgoing, 
    Volume2, 
    Globe,
    Zap,
    CheckCircle2,
    AlertTriangle
} from 'lucide-react';
import { toast } from 'sonner';

const LANGUAGES = [
    { code: 'en', name: 'English' },
    { code: 'id', name: 'Indonesian' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'it', name: 'Italian' },
    { code: 'pt', name: 'Portuguese' },
    { code: 'nl', name: 'Dutch' },
    { code: 'pl', name: 'Polish' },
    { code: 'ru', name: 'Russian' },
    { code: 'ja', name: 'Japanese' },
    { code: 'ko', name: 'Korean' },
    { code: 'zh', name: 'Chinese' },
    { code: 'ar', name: 'Arabic' },
    { code: 'hi', name: 'Hindi' }
];

const MakeCallPage = () => {
    const [formData, setFormData] = useState({
        phone_number: '',
        caller_id: '',
        message_text: '',
        language: 'en',
        speech_rate: 1.0,
        repeat_count: 2
    });
    const [isLoading, setIsLoading] = useState(false);
    const [lastCallResult, setLastCallResult] = useState(null);

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Validation
        if (!formData.phone_number || !formData.caller_id || !formData.message_text) {
            toast.error('Harap isi semua field yang diperlukan');
            return;
        }

        setIsLoading(true);
        setLastCallResult(null);

        try {
            const result = await voiceApi.sendCall(formData);
            setLastCallResult(result);
            
            if (result.status === 'initiated') {
                toast.success('Panggilan berhasil diinisiasi!');
            } else if (result.status === 'failed') {
                toast.error(`Panggilan gagal: ${result.error_message || 'Unknown error'}`);
            } else {
                toast.info(`Status panggilan: ${result.status}`);
            }
        } catch (error) {
            console.error('Error sending call:', error);
            toast.error(error.response?.data?.detail || 'Gagal mengirim panggilan');
        } finally {
            setIsLoading(false);
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6" data-testid="make-call-page">
            {/* Header */}
            <div>
                <h1 className="text-2xl md:text-3xl font-black tracking-tight flex items-center gap-3">
                    <Phone className="w-8 h-8 text-violet-400" />
                    <span>Buat <span className="text-gradient">Panggilan</span></span>
                </h1>
                <p className="text-gray-400 mt-1">Kirim panggilan suara dengan pesan text-to-speech</p>
            </div>

            <div className="grid lg:grid-cols-5 gap-6">
                {/* Main Form */}
                <Card className="lg:col-span-3 bg-[#12141F] border-white/5">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <PhoneOutgoing className="w-5 h-5 text-violet-400" />
                            Detail Panggilan
                        </CardTitle>
                        <CardDescription>Masukkan informasi panggilan</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-6">
                            {/* Phone Number */}
                            <div className="space-y-2">
                                <Label htmlFor="phone_number" className="text-sm font-medium flex items-center gap-2">
                                    <span>Nomor Tujuan</span>
                                    <Badge variant="outline" className="text-xs">Required</Badge>
                                </Label>
                                <Input
                                    id="phone_number"
                                    data-testid="phone-number-input"
                                    type="tel"
                                    placeholder="+628123456789"
                                    value={formData.phone_number}
                                    onChange={(e) => handleInputChange('phone_number', e.target.value)}
                                    className="bg-[#0F111A] border-white/10 focus:border-violet-500 font-mono text-lg"
                                    required
                                />
                                <p className="text-xs text-gray-500">Format: +[kode negara][nomor], contoh: +628123456789</p>
                            </div>

                            {/* Caller ID - SPOOFED NUMBER */}
                            <div className="space-y-2">
                                <Label htmlFor="caller_id" className="text-sm font-medium flex items-center gap-2">
                                    <span>Caller ID</span>
                                    <Badge className="bg-amber-500/20 text-amber-400 border-amber-500/30 text-xs">Spoofed</Badge>
                                </Label>
                                <Input
                                    id="caller_id"
                                    data-testid="caller-id-input"
                                    type="tel"
                                    placeholder="+6221123456"
                                    value={formData.caller_id}
                                    onChange={(e) => handleInputChange('caller_id', e.target.value)}
                                    className="bg-[#0F111A] border-amber-500/30 focus:border-amber-500 font-mono text-lg"
                                    required
                                />
                                <p className="text-xs text-amber-400/80">Nomor yang akan ditampilkan kepada penerima</p>
                            </div>

                            {/* Message */}
                            <div className="space-y-2">
                                <Label htmlFor="message_text" className="text-sm font-medium flex items-center gap-2">
                                    <Volume2 className="w-4 h-4" />
                                    Pesan Suara (TTS)
                                </Label>
                                <Textarea
                                    id="message_text"
                                    data-testid="message-text-input"
                                    placeholder="Masukkan pesan yang akan diucapkan..."
                                    value={formData.message_text}
                                    onChange={(e) => handleInputChange('message_text', e.target.value)}
                                    className="bg-[#0F111A] border-white/10 focus:border-violet-500 min-h-[120px]"
                                    required
                                />
                                <div className="flex justify-between text-xs text-gray-500">
                                    <span>Pesan akan dikonversi menjadi suara</span>
                                    <span>{formData.message_text.length}/1000</span>
                                </div>
                            </div>

                            {/* Language & Speech Rate */}
                            <div className="grid md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label className="text-sm font-medium flex items-center gap-2">
                                        <Globe className="w-4 h-4" />
                                        Bahasa
                                    </Label>
                                    <Select
                                        value={formData.language}
                                        onValueChange={(value) => handleInputChange('language', value)}
                                    >
                                        <SelectTrigger 
                                            data-testid="language-select"
                                            className="bg-[#0F111A] border-white/10"
                                        >
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent className="bg-[#12141F] border-white/10">
                                            {LANGUAGES.map((lang) => (
                                                <SelectItem key={lang.code} value={lang.code}>
                                                    {lang.name}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-2">
                                    <Label className="text-sm font-medium flex items-center gap-2">
                                        <Zap className="w-4 h-4" />
                                        Kecepatan: {formData.speech_rate}x
                                    </Label>
                                    <Slider
                                        data-testid="speech-rate-slider"
                                        value={[formData.speech_rate]}
                                        onValueChange={(value) => handleInputChange('speech_rate', value[0])}
                                        min={0.5}
                                        max={2}
                                        step={0.1}
                                        className="mt-3"
                                    />
                                    <div className="flex justify-between text-xs text-gray-500">
                                        <span>Lambat</span>
                                        <span>Normal</span>
                                        <span>Cepat</span>
                                    </div>
                                </div>
                            </div>

                            {/* Repeat Count */}
                            <div className="space-y-2">
                                <Label className="text-sm font-medium flex items-center gap-2">
                                    🔁 Pengulangan Pesan: {formData.repeat_count}x
                                </Label>
                                <Slider
                                    data-testid="repeat-count-slider"
                                    value={[formData.repeat_count]}
                                    onValueChange={(value) => handleInputChange('repeat_count', value[0])}
                                    min={1}
                                    max={5}
                                    step={1}
                                    className="mt-3"
                                />
                                <div className="flex justify-between text-xs text-gray-500">
                                    <span>1x</span>
                                    <span>3x</span>
                                    <span>5x</span>
                                </div>
                                <p className="text-xs text-cyan-400/80">Pesan akan diulang untuk durasi panggilan lebih lama</p>
                            </div>

                            {/* Submit Button */}
                            <Button
                                type="submit"
                                data-testid="send-call-btn"
                                className="w-full bg-violet-600 hover:bg-violet-700 glow-primary text-lg py-6"
                                disabled={isLoading}
                            >
                                {isLoading ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                                        Mengirim Panggilan...
                                    </>
                                ) : (
                                    <>
                                        <PhoneOutgoing className="w-5 h-5 mr-2" />
                                        Kirim Panggilan
                                    </>
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Result & Info Panel */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Last Call Result */}
                    {lastCallResult && (
                        <Card className={`border ${
                            lastCallResult.status === 'initiated' 
                                ? 'bg-emerald-500/10 border-emerald-500/30' 
                                : lastCallResult.status === 'failed'
                                ? 'bg-red-500/10 border-red-500/30'
                                : 'bg-amber-500/10 border-amber-500/30'
                        }`}>
                            <CardContent className="p-6">
                                <div className="flex items-start gap-3">
                                    {lastCallResult.status === 'initiated' ? (
                                        <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                                    ) : (
                                        <AlertTriangle className="w-6 h-6 text-amber-400 flex-shrink-0" />
                                    )}
                                    <div>
                                        <p className="font-semibold text-white">
                                            {lastCallResult.status === 'initiated' ? 'Panggilan Diinisiasi!' : 
                                             lastCallResult.status === 'failed' ? 'Panggilan Gagal' : 'Status Panggilan'}
                                        </p>
                                        <p className="text-sm text-gray-400 mt-1">
                                            ID: <span className="font-mono text-xs">{lastCallResult.id}</span>
                                        </p>
                                        {lastCallResult.infobip_message_id && (
                                            <p className="text-sm text-gray-400">
                                                Infobip ID: <span className="font-mono text-xs">{lastCallResult.infobip_message_id}</span>
                                            </p>
                                        )}
                                        {lastCallResult.error_message && (
                                            <p className="text-sm text-red-400 mt-2">
                                                Error: {lastCallResult.error_message}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Info Card */}
                    <Card className="bg-[#12141F] border-white/5">
                        <CardHeader>
                            <CardTitle className="text-base">Informasi</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4 text-sm text-gray-400">
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded bg-violet-600/20 flex items-center justify-center flex-shrink-0">
                                    <span className="text-violet-400">1</span>
                                </div>
                                <p>Masukkan nomor tujuan dengan format internasional (+62xxx)</p>
                            </div>
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded bg-violet-600/20 flex items-center justify-center flex-shrink-0">
                                    <span className="text-violet-400">2</span>
                                </div>
                                <p>Caller ID adalah nomor yang akan ditampilkan ke penerima</p>
                            </div>
                            <div className="flex gap-3">
                                <div className="w-8 h-8 rounded bg-violet-600/20 flex items-center justify-center flex-shrink-0">
                                    <span className="text-violet-400">3</span>
                                </div>
                                <p>Pesan akan dikonversi menjadi suara menggunakan TTS engine</p>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Warning Card */}
                    <Card className="bg-amber-500/10 border-amber-500/30">
                        <CardContent className="p-4">
                            <div className="flex gap-3">
                                <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                                <div className="text-sm">
                                    <p className="font-semibold text-amber-400">Catatan Penting</p>
                                    <p className="text-amber-200/80 mt-1">
                                        Fitur ini hanya untuk keperluan edukasi dan project kampus. 
                                        Penggunaan untuk tujuan ilegal dilarang.
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
};

export default MakeCallPage;
