/**
 * CTADisplay Component
 *
 * Компонент для управления CTA (Call-to-Action) элементами - интерактивные
 * призызы к действию для зрителей (подписаться, перейти по ссылке и т.д.).
 *
 * @example
 * ```tsx
 * <CTADisplay token="abc123" channelId={1} />
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
    Plus,
    Trash2,
    ExternalLink,
    MousePointerClick,
    BarChart3,
    X
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';
import { CTA, CTAAction, CTAType } from '../../types/interactions';

interface CTADisplayProps {
    token: string;
    channelId: number;
}

interface ActiveCTA extends CTA {
    remainingTime: number;
}

const CTADisplay: React.FC<CTADisplayProps> = ({ token, channelId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Data state
    const [activeCTAs, setActiveCTAs] = useState<ActiveCTA[]>([]);
    const [recentCTAs, setRecentCTAs] = useState<CTA[]>([]);
    const [loading, setLoading] = useState(false);
    const [showPreview, setShowPreview] = useState(false);

    // Config state
    const [autoDisplay, setAutoDisplay] = useState(true);
    const [defaultDuration, setDefaultDuration] = useState(10);
    const [showSettings, setShowSettings] = useState(false);

    // Create CTA form
    const [newCTA, setNewCTA] = useState({
        cta_type: 'banner' as CTAType,
        action_type: 'link' as CTAAction,
        title: '',
        description: '',
        button_text: '',
        link_url: '',
        icon: '',
        position: { x: 50, y: 50 },
        size: { width: 400, height: 200 },
        display_duration_seconds: 10,
        dismissible: true,
        priority: 1
    });

    const fetchRecentCTAs = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get(`/api/ctas?channel_id=${channelId}&limit=20`);
            const data = Array.isArray(response.data) ? response.data : [];
            setRecentCTAs(data);
        } catch (err) {
            console.error('Failed to fetch CTAs', err);
            toast.error(t('ctas.loadError', 'Не удалось загрузить CTAs'));
            setRecentCTAs([]);
        } finally {
            setLoading(false);
        }
    }, [channelId, toast, t]);

    useEffect(() => {
        fetchRecentCTAs();
    }, [token, channelId, fetchRecentCTAs]);

    // Auto-remove CTAs after duration
    useEffect(() => {
        const interval = setInterval(() => {
            setActiveCTAs(prev => {
                const now = Date.now();
                return prev
                    .map(cta => ({
                        ...cta,
                        remainingTime: Math.max(0, cta.remainingTime - 100)
                    }))
                    .filter(cta => cta.remainingTime > 0 || !cta.dismissible);
            });
        }, 100);

        return () => clearInterval(interval);
    }, []);

    const getActionIcon = (actionType: CTAAction) => {
        switch (actionType) {
            case 'link': return <ExternalLink className="w-5 h-5" />;
            case 'subscribe': return <Megaphone className="w-5 h-5" />;
            case 'follow': return <Eye className="w-5 h-5" />;
            case 'donate': return <MousePointerClick className="w-5 h-5" />;
            default: return <ExternalLink className="w-5 h-5" />;
        }
    };

    const getActionColor = (actionType: CTAAction): 'success' | 'primary' | 'warning' | 'danger' => {
        switch (actionType) {
            case 'link': return 'primary';
            case 'subscribe': return 'success';
            case 'follow': return 'warning';
            case 'donate': return 'danger';
            default: return 'primary';
        }
    };

    const handleCreateCTA = async () => {
        if (!newCTA.title.trim()) {
            toast.warning(t('ctas.enterTitle', 'Введите заголовок'));
            return;
        }

        if (newCTA.action_type === 'link' && !newCTA.link_url.trim()) {
            toast.warning(t('ctas.enterLink', 'Введите ссылку'));
            return;
        }

        setLoading(true);
        try {
            const response = await client.post('/api/ctas', {
                channel_id: channelId,
                ...newCTA
            });

            const createdCTA: ActiveCTA = {
                ...response.data,
                remainingTime: (newCTA.display_duration_seconds || defaultDuration) * 1000
            };

            setActiveCTAs(prev => [...prev, createdCTA]);
            setShowPreview(true);
            toast.success(t('ctas.created', 'CTA создан'));

            // Reset form
            setNewCTA({
                cta_type: 'banner',
                action_type: 'link',
                title: '',
                description: '',
                button_text: '',
                link_url: '',
                icon: '',
                position: { x: 50, y: 50 },
                size: { width: 400, height: 200 },
                display_duration_seconds: 10,
                dismissible: true,
                priority: 1
            });
        } catch (err) {
            console.error('Failed to create CTA', err);
            toast.error(t('ctas.createError', 'Не удалось создать CTA'));
        } finally {
            setLoading(false);
        }
    };

    const handleDismissCTA = (ctaId: string) => {
        setActiveCTAs(prev => prev.filter(c => c.id !== ctaId));
    };

    const handleDeleteCTA = async (ctaId: string) => {
        try {
            await client.delete(`/api/ctas/${ctaId}`);
            setRecentCTAs(prev => prev.filter(c => c.id !== ctaId));
            toast.success(t('ctas.deleted', 'CTA удален'));
        } catch (err) {
            console.error('Failed to delete CTA', err);
            toast.error(t('ctas.deleteError', 'Не удалось удалить CTA'));
        }
    };

    const handleClearAll = () => {
        if (!confirm(t('ctas.confirmClear', 'Удалить все активные CTAs?'))) return;
        setActiveCTAs([]);
        toast.success(t('ctas.cleared', 'CTAs очищены'));
    };

    const renderCTAContent = (cta: CTA) => {
        const icon = getActionIcon(cta.action_type);
        const color = getActionColor(cta.action_type);

        return (
            <div className="space-y-3">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full bg-${color}-500/20`}>
                        {icon}
                    </div>
                    <div className="flex-1">
                        <h3 className="text-xl font-bold">{cta.title}</h3>
                        {cta.description && (
                            <p className="text-sm opacity-80">{cta.description}</p>
                        )}
                    </div>
                    {cta.dismissible && (
                        <Button
                            isIconOnly
                            size="sm"
                            variant="light"
                            onPress={() => handleDismissCTA(cta.id)}
                        >
                            <X className="w-4 h-4" />
                        </Button>
                    )}
                </div>
                {cta.button_text && (
                    <Button
                        color={color}
                        size="lg"
                        className="w-full"
                        endContent={<ExternalLink className="w-4 h-4" />}
                    >
                        {cta.button_text}
                    </Button>
                )}
                <div className="flex gap-4 text-xs opacity-60">
                    <span>{cta.click_count} clicks</span>
                    <span>{cta.dismiss_count} dismissed</span>
                </div>
            </div>
        );
    };

    const ctaTypes: { key: CTAType; label: string }[] = [
        { key: 'button', label: 'Button' },
        { key: 'banner', label: 'Banner' },
        { key: 'overlay', label: 'Overlay' },
        { key: 'popup', label: 'Popup' }
    ];

    const actionTypes: { key: CTAAction; label: string; icon: React.ReactNode }[] = [
        { key: 'link', label: 'Link', icon: <ExternalLink className="w-4 h-4" /> },
        { key: 'subscribe', label: 'Subscribe', icon: <Megaphone className="w-4 h-4" /> },
        { key: 'follow', label: 'Follow', icon: <Eye className="w-4 h-4" /> },
        { key: 'donate', label: 'Donate', icon: <MousePointerClick className="w-4 h-4" /> }
    ];

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('ctas.display', 'CTA Display')}
                    </h2>
                    {activeCTAs.length > 0 && (
                        <Chip
                            size="sm"
                            color="primary"
                            variant="flat"
                        >
                            {activeCTAs.length} {t('ctas.activeCount', 'активных')}
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
                        {t('ctas.settings', 'Настройки')}
                    </Button>
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchRecentCTAs}
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
                                isSelected={autoDisplay}
                                onValueChange={setAutoDisplay}
                            >
                                {t('ctas.autoDisplay', 'Автоматическое отображение')}
                            </Switch>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('ctas.defaultDuration', 'Длительность по умолчанию (секунды)')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {defaultDuration}s
                                </span>
                            </div>
                            <Slider
                                value={defaultDuration}
                                onChange={(value) => setDefaultDuration(value as number)}
                                minValue={5}
                                maxValue={60}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>
                    </motion.div>
                )}

                {/* Create CTA Form */}
                <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 space-y-4 border border-[color:var(--color-outline)]">
                    <div className="flex items-center gap-2">
                        <Plus className="w-4 h-4 text-[color:var(--color-accent)]" />
                        <h4 className="font-semibold text-[color:var(--color-text)]">
                            {t('ctas.createNew', 'Создать новый CTA')}
                        </h4>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm text-[color:var(--color-text-muted)]">
                                {t('ctas.type', 'Тип')}
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {ctaTypes.map(({ key, label }) => (
                                    <Button
                                        key={key}
                                        size="sm"
                                        variant={newCTA.cta_type === key ? 'solid' : 'flat'}
                                        onPress={() => setNewCTA(prev => ({ ...prev, cta_type: key }))}
                                    >
                                        {label}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm text-[color:var(--color-text-muted)]">
                                {t('ctas.actionType', 'Действие')}
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {actionTypes.map(({ key, label, icon }) => (
                                    <Button
                                        key={key}
                                        size="sm"
                                        variant={newCTA.action_type === key ? 'solid' : 'flat'}
                                        onPress={() => setNewCTA(prev => ({ ...prev, action_type: key }))}
                                        startContent={icon}
                                    >
                                        {label}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <Input
                        label={t('ctas.title', 'Заголовок')}
                        placeholder="Subscribe to our channel!"
                        value={newCTA.title}
                        onChange={(e) => setNewCTA(prev => ({ ...prev, title: e.target.value }))}
                        classNames={{
                            input: 'text-[color:var(--color-text)]',
                            inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                            label: 'text-[color:var(--color-text-muted)]'
                        }}
                    />

                    <Textarea
                        label={t('ctas.description', 'Описание')}
                        placeholder="Optional description text..."
                        value={newCTA.description}
                        onChange={(e) => setNewCTA(prev => ({ ...prev, description: e.target.value }))}
                        minRows={2}
                        classNames={{
                            input: 'text-[color:var(--color-text)]',
                            inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]'
                        }}
                    />

                    {newCTA.action_type === 'link' && (
                        <Input
                            label={t('ctas.linkUrl', 'Ссылка')}
                            placeholder="https://example.com"
                            value={newCTA.link_url}
                            onChange={(e) => setNewCTA(prev => ({ ...prev, link_url: e.target.value }))}
                            classNames={{
                                input: 'text-[color:var(--color-text)]',
                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                label: 'text-[color:var(--color-text-muted)]'
                            }}
                        />
                    )}

                    <Input
                        label={t('ctas.buttonText', 'Текст кнопки')}
                        placeholder="Click Here"
                        value={newCTA.button_text}
                        onChange={(e) => setNewCTA(prev => ({ ...prev, button_text: e.target.value }))}
                        classNames={{
                            input: 'text-[color:var(--color-text)]',
                            inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                            label: 'text-[color:var(--color-text-muted)]'
                        }}
                    />

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('ctas.duration', 'Длительность (секунды)')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {newCTA.display_duration_seconds}s
                                </span>
                            </div>
                            <Slider
                                value={newCTA.display_duration_seconds}
                                onChange={(value) => setNewCTA(prev => ({ ...prev, display_duration_seconds: value as number }))}
                                minValue={5}
                                maxValue={60}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('ctas.priority', 'Приоритет')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {newCTA.priority}
                                </span>
                            </div>
                            <Slider
                                value={newCTA.priority}
                                onChange={(value) => setNewCTA(prev => ({ ...prev, priority: value as number }))}
                                minValue={1}
                                maxValue={10}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <Switch
                            isSelected={newCTA.dismissible}
                            onValueChange={(dismissible) => setNewCTA(prev => ({ ...prev, dismissible }))}
                        >
                            {t('ctas.dismissible', 'Можно закрыть')}
                        </Switch>
                    </div>

                    <Button
                        color="primary"
                        onPress={handleCreateCTA}
                        isDisabled={loading}
                        startContent={<Plus className="w-4 h-4" />}
                    >
                        {t('ctas.create', 'Создать CTA')}
                    </Button>
                </div>

                {/* Preview Area */}
                {(showPreview || activeCTAs.length > 0) && (
                    <div className="relative bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg overflow-hidden border border-[color:var(--color-outline)]"
                         style={{ minHeight: '250px' }}>
                        <AnimatePresence mode="wait">
                            {activeCTAs.length > 0 ? (
                                activeCTAs
                                    .sort((a, b) => b.priority - a.priority)
                                    .map((cta) => (
                                        <motion.div
                                            key={cta.id}
                                            initial={{ opacity: 0, scale: 0.9, y: 20 }}
                                            animate={{ opacity: 1, scale: 1, y: 0 }}
                                            exit={{ opacity: 0, scale: 0.9, y: -20 }}
                                            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                                            className="absolute inset-4 bg-gradient-to-r from-primary-500/20 to-secondary-500/20 backdrop-blur-sm rounded-lg p-6 border-2 border-white/20 shadow-2xl"
                                            style={{
                                                left: `${cta.position?.x || 50}%`,
                                                top: `${cta.position?.y || 50}%`,
                                                transform: 'translate(-50%, -50%)',
                                                width: cta.size?.width || 400,
                                                height: 'auto'
                                            }}
                                        >
                                            {renderCTAContent(cta)}
                                            {cta.display_duration_seconds && (
                                                <div className="absolute bottom-2 right-2 text-xs opacity-60">
                                                    {Math.ceil(cta.remainingTime / 1000)}s
                                                </div>
                                            )}
                                        </motion.div>
                                    ))
                            ) : (
                                <div className="absolute inset-0 flex items-center justify-center text-[color:var(--color-text-muted)]">
                                    <div className="text-center">
                                        <Megaphone className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                        <p>{t('ctas.noActiveCTAs', 'Нет активных CTAs')}</p>
                                        <p className="text-sm mt-1">{t('ctas.useCreateButton', 'Создайте CTA используя форму выше')}</p>
                                    </div>
                                </div>
                            )}
                        </AnimatePresence>
                    </div>
                )}

                {/* Active CTAs List */}
                {activeCTAs.length > 0 && (
                    <div className="flex justify-between items-center">
                        <div className="flex gap-2 flex-wrap">
                            {activeCTAs.map(cta => (
                                <Chip
                                    key={cta.id}
                                    size="sm"
                                    variant="flat"
                                    color={getActionColor(cta.action_type)}
                                    startContent={getActionIcon(cta.action_type)}
                                    onClose={() => handleDismissCTA(cta.id)}
                                >
                                    {cta.title} ({Math.ceil(cta.remainingTime / 1000)}s)
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
                            {t('ctas.clearAll', 'Очистить все')}
                        </Button>
                    </div>
                )}

                {/* Recent CTAs History with Statistics */}
                {recentCTAs.length > 0 && (
                    <div className="space-y-3">
                        <div className="flex items-center gap-2">
                            <BarChart3 className="w-4 h-4 text-[color:var(--color-accent)]" />
                            <h4 className="text-sm font-semibold text-[color:var(--color-text-muted)]">
                                {t('ctas.recentHistory', 'Недавние CTAs')}
                            </h4>
                        </div>
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {recentCTAs.map((cta) => (
                                <div
                                    key={cta.id}
                                    className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 border border-[color:var(--color-outline)]"
                                >
                                    <div className="flex items-center justify-between mb-2">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-full bg-${getActionColor(cta.action_type)}-500/20`}>
                                                {getActionIcon(cta.action_type)}
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-2">
                                                    <span className="font-medium text-[color:var(--color-text)]">
                                                        {cta.title}
                                                    </span>
                                                    <Chip size="sm" variant="flat" color={getActionColor(cta.action_type)}>
                                                        {cta.action_type}
                                                    </Chip>
                                                    <Chip size="sm" variant="flat">
                                                        {cta.cta_type}
                                                    </Chip>
                                                </div>
                                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                                    {new Date(cta.created_at).toLocaleString()}
                                                </div>
                                            </div>
                                        </div>
                                        <Button
                                            isIconOnly
                                            size="sm"
                                            variant="light"
                                            color="danger"
                                            onPress={() => handleDeleteCTA(cta.id)}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                    <div className="flex gap-4 text-sm">
                                        <div className="flex items-center gap-1 text-[color:var(--color-text)]">
                                            <MousePointerClick className="w-3 h-3" />
                                            <span>{cta.click_count} {t('ctas.clicks', 'кликов')}</span>
                                        </div>
                                        <div className="flex items-center gap-1 text-[color:var(--color-text-muted)]">
                                            <X className="w-3 h-3" />
                                            <span>{cta.dismiss_count} {t('ctas.dismissed', 'закрыто')}</span>
                                        </div>
                                        {cta.click_count + cta.dismiss_count > 0 && (
                                            <div className="text-[color:var(--color-accent)]">
                                                {((cta.click_count / (cta.click_count + cta.dismiss_count)) * 100).toFixed(1)}% {t('ctas.ctr', 'CTR')}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {!loading && activeCTAs.length === 0 && recentCTAs.length === 0 && (
                    <p className="text-[color:var(--color-text-muted)] text-center py-6">
                        {t('ctas.noCTAs', 'Нет CTAs. Создайте первый!')}
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

export default CTADisplay;
