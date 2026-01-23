/**
 * ShoutoutBanner Component
 *
 * Компонент для управления shoutout баннерами - отображение упоминаний зрителей
 * (новые подписчики, донаты, рейды и т.д.) на stream overlay.
 *
 * @example
 * ```tsx
 * <ShoutoutBanner token="abc123" channelId={1} />
 * ```
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Card,
    CardBody,
    CardHeader,
    Button,
    Input,
    Chip,
    Switch,
    Select,
    SelectItem,
    Slider,
    Spinner,
    Textarea
} from '@heroui/react';
import {
    Megaphone,
    RefreshCw,
    Settings,
    Eye,
    EyeOff,
    Zap,
    Trash2,
    Heart,
    Star,
    Users,
    Gift,
    Sparkles
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';
import { Shoutout, ShoutoutEventType, ShoutoutConfig } from '../../types/interactions';

interface ShoutoutBannerProps {
    token: string;
    channelId: number;
}

interface ActiveShoutout extends Shoutout {
    remainingTime: number;
}

const ShoutoutBanner: React.FC<ShoutoutBannerProps> = ({ token, channelId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Data state
    const [activeShoutouts, setActiveShoutouts] = useState<ActiveShoutout[]>([]);
    const [recentShoutouts, setRecentShoutouts] = useState<Shoutout[]>([]);
    const [loading, setLoading] = useState(false);
    const [showPreview, setShowPreview] = useState(false);

    // Config state
    const [config, setConfig] = useState<ShoutoutConfig>({
        channel_id: channelId,
        enabled: true,
        auto_display: true,
        duration_seconds: 5,
        min_tier_for_subscription: 1,
        min_amount_for_donation: 0,
        display_template: 'standard'
    });
    const [showSettings, setShowSettings] = useState(false);

    // Test shoutout form
    const [testEventType, setTestEventType] = useState<ShoutoutEventType>('follow');
    const [testUserName, setTestUserName] = useState('TestUser');
    const [testAmount, setTestAmount] = useState('');
    const [testMessage, setTestMessage] = useState('');
    const [testCustomMessage, setTestCustomMessage] = useState('');

    const fetchRecentShoutouts = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get(`/api/shoutouts?channel_id=${channelId}&limit=20`);
            const data = Array.isArray(response.data) ? response.data : [];
            setRecentShoutouts(data);
        } catch (err) {
            console.error('Failed to fetch shoutouts', err);
            toast.error(t('shoutouts.loadError', 'Не удалось загрузить shoutouts'));
            setRecentShoutouts([]);
        } finally {
            setLoading(false);
        }
    }, [channelId, toast, t]);

    useEffect(() => {
        fetchRecentShoutouts();
    }, [token, channelId, fetchRecentShoutouts]);

    // Auto-remove shoutouts after duration
    useEffect(() => {
        if (!config.enabled) return;

        const interval = setInterval(() => {
            setActiveShoutouts(prev => {
                const now = Date.now();
                return prev
                    .map(shoutout => ({
                        ...shoutout,
                        remainingTime: Math.max(0, shoutout.remainingTime - 100)
                    }))
                    .filter(shoutout => shoutout.remainingTime > 0);
            });
        }, 100);

        return () => clearInterval(interval);
    }, [config.enabled]);

    const getEventIcon = (eventType: ShoutoutEventType) => {
        switch (eventType) {
            case 'follow': return <Users className="w-5 h-5" />;
            case 'subscription': return <Star className="w-5 h-5" />;
            case 'donation': return <Gift className="w-5 h-5" />;
            case 'raid': return <Sparkles className="w-5 h-5" />;
            case 'cheer': return <Heart className="w-5 h-5" />;
            default: return <Megaphone className="w-5 h-5" />;
        }
    };

    const getEventColor = (eventType: ShoutoutEventType): 'success' | 'primary' | 'warning' | 'danger' => {
        switch (eventType) {
            case 'follow': return 'success';
            case 'subscription': return 'primary';
            case 'donation': return 'warning';
            case 'raid': return 'primary';
            case 'cheer': return 'danger';
            default: return 'success';
        }
    };

    const handleTestShoutout = () => {
        if (!config.enabled) {
            toast.warning(t('shoutouts.disabled', 'Shoutouts отключены'));
            return;
        }

        if (!testUserName.trim()) {
            toast.warning(t('shoutouts.enterUserName', 'Введите имя пользователя'));
            return;
        }

        const newShoutout: ActiveShoutout = {
            id: `test_${Date.now()}`,
            channel_id: channelId,
            type: 'shoutout',
            event_type: testEventType,
            user_name: testUserName,
            message: testMessage || undefined,
            amount: testAmount ? parseFloat(testAmount) : undefined,
            currency: testEventType === 'donation' ? 'USD' : undefined,
            duration_seconds: config.duration_seconds,
            remainingTime: config.duration_seconds * 1000,
            display_template: config.display_template,
            custom_message: testCustomMessage || undefined,
            status: 'active',
            created_at: new Date().toISOString()
        };

        setActiveShoutouts(prev => [...prev, newShoutout]);
        setShowPreview(true);
        toast.success(t('shoutouts.testCreated', 'Тестовый shoutout создан'));
    };

    const handleClearAll = () => {
        if (!confirm(t('shoutouts.confirmClear', 'Удалить все активные shoutouts?'))) return;
        setActiveShoutouts([]);
        toast.success(t('shoutouts.cleared', 'Shoutouts очищены'));
    };

    const handleDeleteShoutout = (shoutoutId: string) => {
        setActiveShoutouts(prev => prev.filter(s => s.id !== shoutoutId));
    };

    const renderShoutoutContent = (shoutout: Shoutout, template: 'minimal' | 'standard' | 'detailed') => {
        const icon = getEventIcon(shoutout.event_type);
        const color = getEventColor(shoutout.event_type);

        if (template === 'minimal') {
            return (
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full bg-${color}-500/20`}>
                        {icon}
                    </div>
                    <div>
                        <p className="text-lg font-bold">{shoutout.user_name}</p>
                        <p className="text-xs opacity-80">{shoutout.event_type}</p>
                    </div>
                </div>
            );
        }

        if (template === 'standard') {
            return (
                <div className="flex items-center gap-4">
                    <div className={`p-3 rounded-full bg-${color}-500/20`}>
                        {icon}
                    </div>
                    <div className="flex-1">
                        <p className="text-2xl font-bold">{shoutout.user_name}</p>
                        <p className="text-sm opacity-80 capitalize">{shoutout.event_type}</p>
                        {shoutout.amount && (
                            <p className="text-lg font-bold text-yellow-400">
                                ${shoutout.amount}
                            </p>
                        )}
                    </div>
                </div>
            );
        }

        // detailed template
        return (
            <div className="flex items-center gap-4">
                <div className={`p-4 rounded-full bg-${color}-500/20`}>
                    {icon}
                </div>
                <div className="flex-1 space-y-1">
                    <p className="text-3xl font-bold">{shoutout.user_name}</p>
                    <p className="text-base opacity-80 capitalize">{shoutout.event_type}</p>
                    {shoutout.amount && (
                        <p className="text-2xl font-bold text-yellow-400">
                            ${shoutout.amount} {shoutout.currency}
                        </p>
                    )}
                    {shoutout.message && (
                        <p className="text-sm italic opacity-90">&quot;{shoutout.message}&quot;</p>
                    )}
                    {shoutout.custom_message && (
                        <p className="text-sm font-semibold">{shoutout.custom_message}</p>
                    )}
                </div>
            </div>
        );
    };

    const getBackgroundGradient = (eventType: ShoutoutEventType) => {
        switch (eventType) {
            case 'follow': return 'from-green-500/30 to-emerald-500/30';
            case 'subscription': return 'from-purple-500/30 to-pink-500/30';
            case 'donation': return 'from-yellow-500/30 to-orange-500/30';
            case 'raid': return 'from-blue-500/30 to-indigo-500/30';
            case 'cheer': return 'from-red-500/30 to-pink-500/30';
            default: return 'from-gray-500/30 to-gray-600/30';
        }
    };

    const eventTypes: { key: ShoutoutEventType; label: string; icon: React.ReactNode }[] = [
        { key: 'follow', label: 'Follow', icon: <Users className="w-4 h-4" /> },
        { key: 'subscription', label: 'Subscription', icon: <Star className="w-4 h-4" /> },
        { key: 'donation', label: 'Donation', icon: <Gift className="w-4 h-4" /> },
        { key: 'raid', label: 'Raid', icon: <Sparkles className="w-4 h-4" /> },
        { key: 'cheer', label: 'Cheer', icon: <Heart className="w-4 h-4" /> }
    ];

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('shoutouts.banner', 'Shoutout Banner')}
                    </h2>
                    <Chip
                        size="sm"
                        color={config.enabled ? 'success' : 'default'}
                        variant="flat"
                        startContent={config.enabled ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    >
                        {config.enabled ? t('shoutouts.active', 'Активен') : t('shoutouts.inactive', 'Неактивен')}
                    </Chip>
                    {activeShoutouts.length > 0 && (
                        <Chip
                            size="sm"
                            color="primary"
                            variant="flat"
                        >
                            {activeShoutouts.length} {t('shoutouts.activeCount', 'активных')}
                        </Chip>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        variant="flat"
                        startContent={<Settings className="w-4 h-4" />}
                        onPress={() => setShowSettings(!showSettings)}
                    >
                        {t('shoutouts.settings', 'Настройки')}
                    </Button>
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchRecentShoutouts}
                        isLoading={loading}
                    >
                        <RefreshCw className="w-4 h-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardBody className="space-y-6">
                {/* Settings Panel */}
                {showSettings && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 space-y-4 border border-[color:var(--color-outline)]"
                    >
                        <div className="flex items-center gap-4">
                            <Switch
                                isSelected={config.enabled}
                                onValueChange={(enabled) => setConfig(prev => ({ ...prev, enabled }))}
                            >
                                {t('shoutouts.enableBanner', 'Показывать баннер')}
                            </Switch>
                        </div>

                        <div className="flex items-center gap-4">
                            <Switch
                                isSelected={config.auto_display}
                                onValueChange={(auto_display) => setConfig(prev => ({ ...prev, auto_display }))}
                            >
                                {t('shoutouts.autoDisplay', 'Автоматическое отображение')}
                            </Switch>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <Select
                                label={t('shoutouts.template', 'Шаблон отображения')}
                                selectedKeys={[config.display_template]}
                                onSelectionChange={(keys) => {
                                    const template = Array.from(keys)[0] as 'minimal' | 'standard' | 'detailed';
                                    setConfig(prev => ({ ...prev, display_template: template }));
                                }}
                                classNames={{
                                    label: 'text-[color:var(--color-text-muted)]',
                                    trigger: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)] text-[color:var(--color-text)]',
                                    value: 'text-[color:var(--color-text)]'
                                }}
                            >
                                <SelectItem key="minimal">Minimal</SelectItem>
                                <SelectItem key="standard">Standard</SelectItem>
                                <SelectItem key="detailed">Detailed</SelectItem>
                            </Select>

                            <div className="space-y-2">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('shoutouts.minDonation', 'Мин. сумма доната')}
                                </label>
                                <Input
                                    type="number"
                                    value={config.min_amount_for_donation.toString()}
                                    onChange={(e) => setConfig(prev => ({ ...prev, min_amount_for_donation: parseFloat(e.target.value) || 0 }))}
                                    min="0"
                                    step="0.01"
                                    classNames={{
                                        input: 'text-[color:var(--color-text)]',
                                        inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                        label: 'text-[color:var(--color-text-muted)]'
                                    }}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('shoutouts.duration', 'Длительность (секунды)')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {config.duration_seconds}s
                                </span>
                            </div>
                            <Slider
                                value={config.duration_seconds}
                                onChange={(value) => setConfig(prev => ({ ...prev, duration_seconds: value as number }))}
                                minValue={3}
                                maxValue={30}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('shoutouts.minTier', 'Мин. уровень подписки')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    Tier {config.min_tier_for_subscription}
                                </span>
                            </div>
                            <Slider
                                value={config.min_tier_for_subscription}
                                onChange={(value) => setConfig(prev => ({ ...prev, min_tier_for_subscription: value as number }))}
                                minValue={1}
                                maxValue={3}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>
                    </motion.div>
                )}

                {/* Test Shoutout */}
                <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 space-y-4 border border-[color:var(--color-outline)]">
                    <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-[color:var(--color-accent)]" />
                        <h4 className="font-semibold text-[color:var(--color-text)]">
                            {t('shoutouts.testShoutout', 'Тестовый Shoutout')}
                        </h4>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm text-[color:var(--color-text-muted)]">
                                {t('shoutouts.eventType', 'Тип события')}
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {eventTypes.map(({ key, label, icon }) => (
                                    <Button
                                        key={key}
                                        size="sm"
                                        variant={testEventType === key ? 'solid' : 'flat'}
                                        onPress={() => setTestEventType(key)}
                                        startContent={icon}
                                    >
                                        {label}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        <Input
                            label={t('shoutouts.userName', 'Имя пользователя')}
                            placeholder="TestUser"
                            value={testUserName}
                            onChange={(e) => setTestUserName(e.target.value)}
                            classNames={{
                                input: 'text-[color:var(--color-text)]',
                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                label: 'text-[color:var(--color-text-muted)]'
                            }}
                        />
                    </div>

                    {(testEventType === 'donation' || testEventType === 'cheer') && (
                        <Input
                            type="number"
                            label={t('shoutouts.amount', 'Сумма')}
                            placeholder="10.00"
                            value={testAmount}
                            onChange={(e) => setTestAmount(e.target.value)}
                            min="0"
                            step="0.01"
                            classNames={{
                                input: 'text-[color:var(--color-text)]',
                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                label: 'text-[color:var(--color-text-muted)]'
                            }}
                        />
                    )}

                    <Input
                        label={t('shoutouts.message', 'Сообщение')}
                        placeholder="Optional message from user..."
                        value={testMessage}
                        onChange={(e) => setTestMessage(e.target.value)}
                        classNames={{
                            input: 'text-[color:var(--color-text)]',
                            inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                            label: 'text-[color:var(--color-text-muted)]'
                        }}
                    />

                    <Textarea
                        label={t('shoutouts.customMessage', 'Кастомное сообщение')}
                        placeholder="Thank you for the support!"
                        value={testCustomMessage}
                        onChange={(e) => setTestCustomMessage(e.target.value)}
                        minRows={2}
                        classNames={{
                            input: 'text-[color:var(--color-text)]',
                            inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]'
                        }}
                    />

                    <Button
                        color="primary"
                        onPress={handleTestShoutout}
                        isDisabled={!config.enabled}
                        startContent={<Megaphone className="w-4 h-4" />}
                    >
                        {t('shoutouts.show', 'Показать')}
                    </Button>
                </div>

                {/* Preview Area */}
                {(showPreview || activeShoutouts.length > 0) && (
                    <div className="relative bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg overflow-hidden border border-[color:var(--color-outline)]"
                         style={{ minHeight: '200px' }}>
                        <AnimatePresence mode="wait">
                            {activeShoutouts.length > 0 ? (
                                activeShoutouts.map((shoutout) => (
                                    <motion.div
                                        key={shoutout.id}
                                        initial={{ opacity: 0, scale: 0.8, y: 50 }}
                                        animate={{ opacity: 1, scale: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.8, y: -50 }}
                                        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                                        className={`absolute inset-4 bg-gradient-to-r ${getBackgroundGradient(shoutout.event_type)} backdrop-blur-sm rounded-lg p-6 border-2 border-white/20 shadow-2xl`}
                                        onClick={() => handleDeleteShoutout(shoutout.id)}
                                    >
                                        {renderShoutoutContent(shoutout, shoutout.display_template || config.display_template)}
                                        <div className="absolute bottom-2 right-2 text-xs opacity-60">
                                            {Math.ceil(shoutout.remainingTime / 1000)}s
                                        </div>
                                    </motion.div>
                                ))
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-[color:var(--color-text-muted)]">
                                    <div className="text-center">
                                        <Megaphone className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                        <p>{t('shoutouts.noActiveShoutouts', 'Нет активных shoutouts')}</p>
                                        <p className="text-sm mt-1">{t('shoutouts.useTestButton', 'Используйте кнопку выше для теста')}</p>
                                    </div>
                                </div>
                            )}
                        </AnimatePresence>
                    </div>
                )}

                {/* Active Shoutouts List */}
                {activeShoutouts.length > 0 && (
                    <div className="flex justify-between items-center">
                        <div className="flex gap-2 flex-wrap">
                            {activeShoutouts.map(shoutout => (
                                <Chip
                                    key={shoutout.id}
                                    size="sm"
                                    variant="flat"
                                    color={getEventColor(shoutout.event_type)}
                                    startContent={getEventIcon(shoutout.event_type)}
                                    onClose={() => handleDeleteShoutout(shoutout.id)}
                                >
                                    {shoutout.user_name} ({Math.ceil(shoutout.remainingTime / 1000)}s)
                                </Chip>
                            ))}
                        </div>
                        <Button
                            size="sm"
                            color="danger"
                            variant="flat"
                            startContent={<Trash2 className="w-4 h-4" />}
                            onPress={handleClearAll}
                        >
                            {t('shoutouts.clearAll', 'Очистить все')}
                        </Button>
                    </div>
                )}

                {/* Recent Shoutouts History */}
                {recentShoutouts.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-[color:var(--color-text-muted)]">
                            {t('shoutouts.recentHistory', 'Недавние shoutouts')}
                        </h4>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            {recentShoutouts.map((shoutout) => (
                                <div
                                    key={shoutout.id}
                                    className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 border border-[color:var(--color-outline)] flex items-center justify-between"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-full bg-${getEventColor(shoutout.event_type)}-500/20`}>
                                            {getEventIcon(shoutout.event_type)}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className="font-medium text-[color:var(--color-text)]">
                                                    {shoutout.user_name}
                                                </span>
                                                <Chip size="sm" variant="flat" color={getEventColor(shoutout.event_type)}>
                                                    {shoutout.event_type}
                                                </Chip>
                                            </div>
                                            <div className="text-xs text-[color:var(--color-text-muted)]">
                                                {new Date(shoutout.created_at).toLocaleString()}
                                            </div>
                                        </div>
                                    </div>
                                    {shoutout.amount && (
                                        <div className="text-lg font-bold text-yellow-500">
                                            ${shoutout.amount}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {!loading && activeShoutouts.length === 0 && recentShoutouts.length === 0 && (
                    <p className="text-[color:var(--color-text-muted)] text-center py-6">
                        {t('shoutouts.noShoutouts', 'Нет shoutouts. Создайте первый!')}
                    </p>
                )}

                {loading && (
                    <div className="flex justify-center py-6">
                        <Spinner size="lg" />
                    </div>
                )}
            </CardBody>
        </Card>
    );
};

export default ShoutoutBanner;
