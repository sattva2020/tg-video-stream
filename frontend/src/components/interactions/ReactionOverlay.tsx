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
    Spinner
} from '@heroui/react';
import {
    Smile,
    RefreshCw,
    Settings,
    Eye,
    EyeOff,
    Zap,
    Trash2
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';
import { Reaction } from '../../types/interactions';

interface ReactionOverlayProps {
    token: string;
    channelId: number;
}

interface ActiveReaction extends Reaction {
    remainingTime: number;
}

interface ReactionSettings {
    enabled: boolean;
    default_duration: number;
    default_animation: 'fade' | 'pop' | 'bounce' | 'slide';
    default_size: 'small' | 'medium' | 'large';
    max_visible: number;
    auto_position: boolean;
}

const ReactionOverlay: React.FC<ReactionOverlayProps> = ({ token, channelId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Reaction data
    const [activeReactions, setActiveReactions] = useState<ActiveReaction[]>([]);
    const [recentReactions, setRecentReactions] = useState<Reaction[]>([]);
    const [loading, setLoading] = useState(false);
    const [showPreview, setShowPreview] = useState(false);

    // Settings
    const [settings, setSettings] = useState<ReactionSettings>({
        enabled: true,
        default_duration: 5,
        default_animation: 'pop',
        default_size: 'medium',
        max_visible: 10,
        auto_position: true
    });
    const [showSettings, setShowSettings] = useState(false);

    // Test reaction form
    const [testEmoji, setTestEmoji] = useState('🎉');
    const [testCount, setTestCount] = useState(1);

    const fetchRecentReactions = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get(`/api/reactions?channel_id=${channelId}&limit=20`);
            const data = Array.isArray(response.data) ? response.data : [];
            setRecentReactions(data);
        } catch (err) {
            console.error('Failed to fetch reactions', err);
            toast.error(t('reactions.loadError', 'Не удалось загрузить реакции'));
            setRecentReactions([]);
        } finally {
            setLoading(false);
        }
    }, [channelId, toast, t]);

    useEffect(() => {
        fetchRecentReactions();
    }, [token, channelId, fetchRecentReactions]);

    // Auto-remove reactions after duration
    useEffect(() => {
        if (!settings.enabled) return;

        const interval = setInterval(() => {
            setActiveReactions(prev => {
                const now = Date.now();
                return prev
                    .map(reaction => ({
                        ...reaction,
                        remainingTime: Math.max(0, reaction.remainingTime - 100)
                    }))
                    .filter(reaction => reaction.remainingTime > 0);
            });
        }, 100);

        return () => clearInterval(interval);
    }, [settings.enabled]);

    const handleTestReaction = () => {
        if (!settings.enabled) {
            toast.warning(t('reactions.disabled', 'Реакции отключены'));
            return;
        }

        if (activeReactions.length >= settings.max_visible) {
            toast.warning(t('reactions.maxVisible', 'Достигнут лимит отображения'));
            return;
        }

        const newReaction: ActiveReaction = {
            id: `test_${Date.now()}`,
            channel_id: channelId,
            type: 'reaction',
            emoji: testEmoji,
            count: testCount,
            duration_seconds: settings.default_duration,
            remainingTime: settings.default_duration * 1000,
            animation: settings.default_animation,
            size: settings.default_size,
            status: 'active',
            created_at: new Date().toISOString(),
            position: settings.auto_position ? {
                x: Math.random() * 60 + 20, // Keep within 20-80% to avoid edges
                y: Math.random() * 60 + 20
            } : { x: 50, y: 50 }
        };

        setActiveReactions(prev => [...prev, newReaction]);
        setShowPreview(true);
    };

    const handleClearAll = () => {
        if (!confirm(t('reactions.confirmClear', 'Удалить все активные реакции?'))) return;
        setActiveReactions([]);
        toast.success(t('reactions.cleared', 'Реакции очищены'));
    };

    const handleDeleteReaction = (reactionId: string) => {
        setActiveReactions(prev => prev.filter(r => r.id !== reactionId));
    };

    const getAnimationVariants = (animation: string) => {
        switch (animation) {
            case 'fade':
                return {
                    initial: { opacity: 0, scale: 0.8 },
                    animate: { opacity: 1, scale: 1 },
                    exit: { opacity: 0, scale: 0.8 }
                };
            case 'pop':
                return {
                    initial: { opacity: 0, scale: 0 },
                    animate: { opacity: 1, scale: 1, transition: { type: 'spring', stiffness: 300, damping: 20 } },
                    exit: { opacity: 0, scale: 0 }
                };
            case 'bounce':
                return {
                    initial: { opacity: 0, y: -50 },
                    animate: { opacity: 1, y: 0, transition: { type: 'spring', bounce: 0.5 } },
                    exit: { opacity: 0, y: 50 }
                };
            case 'slide':
                return {
                    initial: { opacity: 0, x: -100 },
                    animate: { opacity: 1, x: 0 },
                    exit: { opacity: 0, x: 100 }
                };
            default:
                return {
                    initial: { opacity: 0 },
                    animate: { opacity: 1 },
                    exit: { opacity: 0 }
                };
        }
    };

    const getSizeClasses = (size: string) => {
        switch (size) {
            case 'small': return 'text-2xl';
            case 'medium': return 'text-5xl';
            case 'large': return 'text-7xl';
            default: return 'text-5xl';
        }
    };

    const commonEmojis = ['🎉', '❤️', '👍', '😂', '😮', '🔥', '👏', '🎊', '⭐', '💯'];

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('reactions.overlay', 'Оверлей реакций')}
                    </h2>
                    <Chip
                        size="sm"
                        color={settings.enabled ? 'success' : 'default'}
                        variant="flat"
                        startContent={settings.enabled ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    >
                        {settings.enabled ? t('reactions.active', 'Активен') : t('reactions.inactive', 'Неактивен')}
                    </Chip>
                    {activeReactions.length > 0 && (
                        <Chip
                            size="sm"
                            color="primary"
                            variant="flat"
                        >
                            {activeReactions.length} {t('reactions.activeCount', 'активных')}
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
                        {t('reactions.settings', 'Настройки')}
                    </Button>
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchRecentReactions}
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
                                isSelected={settings.enabled}
                                onValueChange={(enabled) => setSettings(prev => ({ ...prev, enabled }))}
                            >
                                {t('reactions.enableOverlay', 'Показывать оверлей')}
                            </Switch>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <Select
                                label={t('reactions.animation', 'Анимация')}
                                selectedKeys={[settings.default_animation]}
                                onSelectionChange={(keys) => {
                                    const animation = Array.from(keys)[0] as typeof settings.default_animation;
                                    setSettings(prev => ({ ...prev, default_animation: animation }));
                                }}
                                classNames={{
                                    label: 'text-[color:var(--color-text-muted)]',
                                    trigger: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)] text-[color:var(--color-text)]',
                                    value: 'text-[color:var(--color-text)]'
                                }}
                            >
                                <SelectItem key="fade">Fade</SelectItem>
                                <SelectItem key="pop">Pop</SelectItem>
                                <SelectItem key="bounce">Bounce</SelectItem>
                                <SelectItem key="slide">Slide</SelectItem>
                            </Select>

                            <Select
                                label={t('reactions.size', 'Размер')}
                                selectedKeys={[settings.default_size]}
                                onSelectionChange={(keys) => {
                                    const size = Array.from(keys)[0] as typeof settings.default_size;
                                    setSettings(prev => ({ ...prev, default_size: size }));
                                }}
                                classNames={{
                                    label: 'text-[color:var(--color-text-muted)]',
                                    trigger: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)] text-[color:var(--color-text)]',
                                    value: 'text-[color:var(--color-text)]'
                                }}
                            >
                                <SelectItem key="small">Small</SelectItem>
                                <SelectItem key="medium">Medium</SelectItem>
                                <SelectItem key="large">Large</SelectItem>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('reactions.duration', 'Длительность (секунды)')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {settings.default_duration}s
                                </span>
                            </div>
                            <Slider
                                value={settings.default_duration}
                                onChange={(value) => setSettings(prev => ({ ...prev, default_duration: value as number }))}
                                minValue={1}
                                maxValue={30}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('reactions.maxVisible', 'Макс. одновременно')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {settings.max_visible}
                                </span>
                            </div>
                            <Slider
                                value={settings.max_visible}
                                onChange={(value) => setSettings(prev => ({ ...prev, max_visible: value as number }))}
                                minValue={1}
                                maxValue={20}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>

                        <Switch
                            isSelected={settings.auto_position}
                            onValueChange={(auto_position) => setSettings(prev => ({ ...prev, auto_position }))}
                        >
                            {t('reactions.autoPosition', 'Автоматическая позиция')}
                        </Switch>
                    </motion.div>
                )}

                {/* Test Reaction */}
                <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 space-y-4 border border-[color:var(--color-outline)]">
                    <div className="flex items-center gap-2">
                        <Zap className="w-4 h-4 text-[color:var(--color-accent)]" />
                        <h4 className="font-semibold text-[color:var(--color-text)]">
                            {t('reactions.testReaction', 'Тестовая реакция')}
                        </h4>
                    </div>

                    <div className="flex gap-4 items-end">
                        <div className="flex-1 space-y-2">
                            <label className="text-sm text-[color:var(--color-text-muted)]">
                                {t('reactions.commonEmojis', 'Частые эмодзи')}
                            </label>
                            <div className="flex flex-wrap gap-2">
                                {commonEmojis.map(emoji => (
                                    <Button
                                        key={emoji}
                                        size="sm"
                                        variant={testEmoji === emoji ? 'solid' : 'flat'}
                                        onPress={() => setTestEmoji(emoji)}
                                        className="text-xl"
                                    >
                                        {emoji}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        <Input
                            label={t('reactions.customEmoji', 'Свой эмодзи')}
                            placeholder="🎉"
                            value={testEmoji}
                            onChange={(e) => setTestEmoji(e.target.value)}
                            maxLength={2}
                            classNames={{
                                input: 'text-[color:var(--color-text)] text-center text-xl',
                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                label: 'text-[color:var(--color-text-muted)]'
                            }}
                            className="w-24"
                        />

                        <Input
                            type="number"
                            label={t('reactions.count', 'Количество')}
                            value={testCount.toString()}
                            onChange={(e) => setTestCount(Math.max(1, parseInt(e.target.value) || 1))}
                            min="1"
                            max="99"
                            classNames={{
                                input: 'text-[color:var(--color-text)]',
                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                label: 'text-[color:var(--color-text-muted)]'
                            }}
                            className="w-24"
                        />

                        <Button
                            color="primary"
                            onPress={handleTestReaction}
                            isDisabled={!settings.enabled}
                            startContent={<Smile className="w-4 h-4" />}
                        >
                            {t('reactions.show', 'Показать')}
                        </Button>
                    </div>
                </div>

                {/* Preview Area */}
                {(showPreview || activeReactions.length > 0) && (
                    <div className="relative bg-gradient-to-br from-purple-900/20 to-blue-900/20 rounded-lg overflow-hidden border border-[color:var(--color-outline)]"
                         style={{ minHeight: '300px' }}>
                        {/* Grid overlay for reference */}
                        <div className="absolute inset-0 opacity-10 pointer-events-none"
                             style={{
                                 backgroundImage: 'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)',
                                 backgroundSize: '50px 50px'
                             }}
                        />

                        {/* Active Reactions */}
                        <AnimatePresence>
                            {activeReactions.map((reaction) => {
                                const variants = getAnimationVariants(reaction.animation || 'pop');
                                const size = reaction.size || settings.default_size;

                                return (
                                    <motion.div
                                        key={reaction.id}
                                        className="absolute flex items-center justify-center cursor-pointer hover:scale-110 transition-transform"
                                        style={{
                                            left: `${reaction.position?.x || 50}%`,
                                            top: `${reaction.position?.y || 50}%`,
                                            transform: 'translate(-50%, -50%)'
                                        }}
                                        {...variants}
                                        onClick={() => handleDeleteReaction(reaction.id)}
                                    >
                                        <div className={`flex flex-col items-center ${getSizeClasses(size)}`}>
                                            <span className="drop-shadow-2xl">{reaction.emoji}</span>
                                            {reaction.count > 1 && (
                                                <span className="text-sm font-bold text-white bg-black/50 px-2 py-0.5 rounded-full mt-1">
                                                    ×{reaction.count}
                                                </span>
                                            )}
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>

                        {/* Empty state */}
                        {activeReactions.length === 0 && (
                            <div className="absolute inset-0 flex items-center justify-center text-[color:var(--color-text-muted)]">
                                <div className="text-center">
                                    <Smile className="w-12 h-12 mx-auto mb-2 opacity-50" />
                                    <p>{t('reactions.noActiveReactions', 'Нет активных реакций')}</p>
                                    <p className="text-sm mt-1">{t('reactions.useTestButton', 'Используйте кнопку выше для теста')}</p>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Active Reactions List */}
                {activeReactions.length > 0 && (
                    <div className="flex justify-between items-center">
                        <div className="flex gap-2 flex-wrap">
                            {activeReactions.map(reaction => (
                                <Chip
                                    key={reaction.id}
                                    size="sm"
                                    variant="flat"
                                    onClose={() => handleDeleteReaction(reaction.id)}
                                >
                                    {reaction.emoji} ({Math.ceil(reaction.remainingTime / 1000)}s)
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
                            {t('reactions.clearAll', 'Очистить все')}
                        </Button>
                    </div>
                )}

                {/* Recent Reactions History */}
                {recentReactions.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-[color:var(--color-text-muted)]">
                            {t('reactions.recentHistory', 'Недавние реакции')}
                        </h4>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            {recentReactions.map((reaction) => (
                                <div
                                    key={reaction.id}
                                    className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 border border-[color:var(--color-outline)] flex items-center justify-between"
                                >
                                    <div className="flex items-center gap-3">
                                        <span className="text-2xl">{reaction.emoji}</span>
                                        <div>
                                            <div className="text-sm text-[color:var(--color-text)]">
                                                {t('reactions.count', 'Количество')}: {reaction.count}
                                            </div>
                                            <div className="text-xs text-[color:var(--color-text-muted)]">
                                                {new Date(reaction.created_at).toLocaleString()}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {reaction.animation && (
                                            <Chip size="sm" variant="flat">
                                                {reaction.animation}
                                            </Chip>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {!loading && activeReactions.length === 0 && recentReactions.length === 0 && (
                    <p className="text-[color:var(--color-text-muted)] text-center py-6">
                        {t('reactions.noReactions', 'Нет реакций. Создайте первую!')}
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

export default ReactionOverlay;
