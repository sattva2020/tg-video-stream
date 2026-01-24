/**
 * ChatOverlay Component
 *
 * Компонент для управления отображением чат-сообщений на stream overlay.
 * Поддерживает Telegram-интеграцию, модерацию и настройку отображения.
 *
 * @example
 * ```tsx
 * <ChatOverlay token="abc123" channelId={1} />
 * ```
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
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
    MessageSquare,
    RefreshCw,
    Settings,
    Eye,
    EyeOff,
    Trash2,
    Shield,
    AlertTriangle,
    Ban
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';

// === Types ===

interface ChatMessage {
    id: string;
    stream_id: string;
    author_id?: string;
    telegram_user_id?: number;
    author_name: string;
    author_avatar_url?: string;
    content: string;
    message_status: 'pending' | 'visible' | 'hidden' | 'flagged';
    telegram_message_id?: number;
    original_timestamp?: string;
    is_filtered: boolean;
    filter_reason?: string;
    is_flagged: boolean;
    created_at: string;
}

interface ChatOverlayConfig {
    enabled: boolean;
    max_messages: number;
    display_duration_seconds: number;
    font_size: number;
    position: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right';
    show_avatars: boolean;
    show_timestamps: boolean;
    background_opacity: number;
    auto_hide: boolean;
    filter_profanity: boolean;
}

interface ChatOverlayProps {
    token: string;
    channelId: number;
    streamId?: string;
}

// === Component ===

const ChatOverlay: React.FC<ChatOverlayProps> = ({ token, channelId, streamId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Data state
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [stats, setStats] = useState<any>(null);

    // Settings state
    const [config, setConfig] = useState<ChatOverlayConfig>({
        enabled: true,
        max_messages: 50,
        display_duration_seconds: 30,
        font_size: 16,
        position: 'bottom-left',
        show_avatars: true,
        show_timestamps: false,
        background_opacity: 0.8,
        auto_hide: false,
        filter_profanity: true
    });
    const [showSettings, setShowSettings] = useState(false);

    // Moderation state
    const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
    const [filterReason, setFilterReason] = useState('');

    const fetchMessages = useCallback(async () => {
        setLoading(true);
        try {
            const params: any = { limit: 50 };
            if (streamId) {
                params.stream_id = streamId;
            }
            const response = await client.get('/api/chat-overlay/messages', { params });
            const data = Array.isArray(response.data) ? response.data : [];
            setMessages(data);
        } catch (err) {
            console.error('Failed to fetch chat messages', err);
            toast.error(t('chat.loadError', 'Не удалось загрузить сообщения'));
            setMessages([]);
        } finally {
            setLoading(false);
        }
    }, [streamId, toast, t]);

    const fetchStats = useCallback(async () => {
        if (!streamId) return;

        try {
            const response = await client.get(`/api/chat-overlay/stats/${streamId}`);
            setStats(response.data);
        } catch (err) {
            console.error('Failed to fetch chat stats', err);
        }
    }, [streamId]);

    useEffect(() => {
        fetchMessages();
        if (streamId) {
            fetchStats();
        }
    }, [token, channelId, streamId, fetchMessages, fetchStats]);

    const handleUpdateMessageStatus = async (messageId: string, updates: Partial<ChatMessage>) => {
        try {
            await client.put(`/api/chat-overlay/messages/${messageId}`, updates);
            toast.success(t('chat.messageUpdated', 'Сообщение обновлено'));
            fetchMessages();
            fetchStats();
        } catch (err) {
            console.error('Failed to update message', err);
            toast.error(t('chat.updateError', 'Не удалось обновить сообщение'));
        }
    };

    const handleHideMessage = async (messageId: string) => {
        await handleUpdateMessageStatus(messageId, {
            message_status: 'hidden',
            is_filtered: true
        });
    };

    const handleFilterMessage = async () => {
        if (!selectedMessageId || !filterReason.trim()) {
            toast.warning(t('chat.specifyReason', 'Укажите причину фильтрации'));
            return;
        }

        await handleUpdateMessageStatus(selectedMessageId, {
            message_status: 'hidden',
            is_filtered: true,
            filter_reason: filterReason
        });
        setSelectedMessageId(null);
        setFilterReason('');
    };

    const handleDeleteMessage = async (messageId: string) => {
        if (!confirm(t('chat.confirmDelete', 'Удалить это сообщение?'))) return;

        try {
            await client.delete(`/api/chat-overlay/messages/${messageId}`);
            toast.success(t('chat.messageDeleted', 'Сообщение удалено'));
            fetchMessages();
            fetchStats();
        } catch (err) {
            console.error('Failed to delete message', err);
            toast.error(t('chat.deleteError', 'Не удалось удалить сообщение'));
        }
    };

    const handleSaveConfig = async () => {
        if (!streamId) {
            toast.warning(t('chat.noStream', 'Не указан stream ID'));
            return;
        }

        try {
            await client.put(`/api/chat-overlay/config/${streamId}`, config);
            toast.success(t('chat.configSaved', 'Конфигурация сохранена'));
        } catch (err) {
            console.error('Failed to save config', err);
            toast.error(t('chat.configError', 'Не удалось сохранить конфигурацию'));
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'visible': return 'success';
            case 'hidden': return 'default';
            case 'flagged': return 'warning';
            case 'pending': return 'primary';
            default: return 'default';
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'visible': return <Eye className="w-3 h-3" />;
            case 'hidden': return <EyeOff className="w-3 h-3" />;
            case 'flagged': return <AlertTriangle className="w-3 h-3" />;
            default: return null;
        }
    };

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('chat.overlay', 'Оверлей чата')}
                    </h2>
                    <Chip
                        size="sm"
                        color={config.enabled ? 'success' : 'default'}
                        variant="flat"
                        startContent={config.enabled ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    >
                        {config.enabled ? t('chat.active', 'Активен') : t('chat.inactive', 'Неактивен')}
                    </Chip>
                    {stats && (
                        <Chip size="sm" color="primary" variant="flat">
                            {stats.active_messages || 0} {t('chat.messages', 'сообщений')}
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
                        {t('chat.settings', 'Настройки')}
                    </Button>
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchMessages}
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
                                {t('chat.enableOverlay', 'Показывать оверлей')}
                            </Switch>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <Select
                                label={t('chat.position', 'Позиция')}
                                selectedKeys={[config.position]}
                                onSelectionChange={(keys) => {
                                    const position = Array.from(keys)[0] as typeof config.position;
                                    setConfig(prev => ({ ...prev, position }));
                                }}
                                classNames={{
                                    label: 'text-[color:var(--color-text-muted)]',
                                    trigger: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)] text-[color:var(--color-text)]',
                                    value: 'text-[color:var(--color-text)]'
                                }}
                            >
                                <SelectItem key="bottom-left">{t('chat.bottomLeft', 'Слева внизу')}</SelectItem>
                                <SelectItem key="bottom-right">{t('chat.bottomRight', 'Справа внизу')}</SelectItem>
                                <SelectItem key="top-left">{t('chat.topLeft', 'Слева вверху')}</SelectItem>
                                <SelectItem key="top-right">{t('chat.topRight', 'Справа вверху')}</SelectItem>
                            </Select>

                            <div className="space-y-2">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('chat.maxMessages', 'Макс. сообщений')}
                                </label>
                                <Input
                                    type="number"
                                    value={config.max_messages.toString()}
                                    onChange={(e) => setConfig(prev => ({ ...prev, max_messages: parseInt(e.target.value) || 50 }))}
                                    min="1"
                                    max="200"
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
                                    {t('chat.fontSize', 'Размер шрифта')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {config.font_size}px
                                </span>
                            </div>
                            <Slider
                                value={config.font_size}
                                onChange={(value) => setConfig(prev => ({ ...prev, font_size: value as number }))}
                                minValue={10}
                                maxValue={32}
                                step={1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('chat.backgroundOpacity', 'Прозрачность фона')}
                                </label>
                                <span className="text-sm text-[color:var(--color-text)]">
                                    {Math.round(config.background_opacity * 100)}%
                                </span>
                            </div>
                            <Slider
                                value={config.background_opacity}
                                onChange={(value) => setConfig(prev => ({ ...prev, background_opacity: value as number }))}
                                minValue={0}
                                maxValue={1}
                                step={0.1}
                                className="max-w-full"
                                color="primary"
                            />
                        </div>

                        <div className="flex gap-4">
                            <Switch
                                isSelected={config.show_avatars}
                                onValueChange={(show_avatars) => setConfig(prev => ({ ...prev, show_avatars }))}
                            >
                                {t('chat.showAvatars', 'Показывать аватары')}
                            </Switch>
                            <Switch
                                isSelected={config.show_timestamps}
                                onValueChange={(show_timestamps) => setConfig(prev => ({ ...prev, show_timestamps }))}
                            >
                                {t('chat.showTimestamps', 'Показывать время')}
                            </Switch>
                            <Switch
                                isSelected={config.auto_hide}
                                onValueChange={(auto_hide) => setConfig(prev => ({ ...prev, auto_hide }))}
                            >
                                {t('chat.autoHide', 'Автоскрытие')}
                            </Switch>
                            <Switch
                                isSelected={config.filter_profanity}
                                onValueChange={(filter_profanity) => setConfig(prev => ({ ...prev, filter_profanity }))}
                            >
                                {t('chat.filterProfanity', 'Фильтр мата')}
                            </Switch>
                        </div>

                        <Button
                            color="primary"
                            onPress={handleSaveConfig}
                            className="w-full"
                        >
                            {t('chat.saveConfig', 'Сохранить конфигурацию')}
                        </Button>
                    </motion.div>
                )}

                {/* Stats Panel */}
                {stats && (
                    <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 border border-[color:var(--color-outline)]">
                        <h4 className="font-semibold text-[color:var(--color-text)] mb-3">
                            {t('chat.statistics', 'Статистика')}
                        </h4>
                        <div className="grid grid-cols-4 gap-4">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-[color:var(--color-text)]">
                                    {stats.total_messages || 0}
                                </div>
                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                    {t('chat.total', 'Всего')}
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-green-500">
                                    {stats.by_status?.visible || 0}
                                </div>
                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                    {t('chat.visible', 'Видимых')}
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-red-500">
                                    {stats.filtered_count || 0}
                                </div>
                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                    {t('chat.filtered', 'Отфильтровано')}
                                </div>
                            </div>
                            <div className="text-center">
                                <div className="text-2xl font-bold text-yellow-500">
                                    {stats.by_status?.flagged || 0}
                                </div>
                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                    {t('chat.flagged', 'На проверке')}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Filter Reason Input */}
                {selectedMessageId && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 space-y-3"
                    >
                        <div className="flex items-center gap-2">
                            <Shield className="w-4 h-4 text-yellow-500" />
                            <h4 className="font-semibold text-[color:var(--color-text)]">
                                {t('chat.filterMessage', 'Фильтровать сообщение')}
                            </h4>
                        </div>
                        <Textarea
                            placeholder={t('chat.filterReasonPlaceholder', 'Причина фильтрации...')}
                            value={filterReason}
                            onChange={(e) => setFilterReason(e.target.value)}
                            minRows={2}
                            classNames={{
                                input: 'text-[color:var(--color-text)]',
                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]'
                            }}
                        />
                        <div className="flex gap-2">
                            <Button
                                color="warning"
                                size="sm"
                                onPress={handleFilterMessage}
                                startContent={<Ban className="w-4 h-4" />}
                            >
                                {t('chat.filter', 'Фильтровать')}
                            </Button>
                            <Button
                                size="sm"
                                variant="flat"
                                onPress={() => {
                                    setSelectedMessageId(null);
                                    setFilterReason('');
                                }}
                            >
                                {t('chat.cancel', 'Отмена')}
                            </Button>
                        </div>
                    </motion.div>
                )}

                {/* Messages List */}
                <div className="space-y-3">
                    <h4 className="text-sm font-semibold text-[color:var(--color-text-muted)]">
                        {t('chat.messages', 'Сообщения')}
                    </h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                        {messages.map((message) => (
                            <motion.div
                                key={message.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`bg-[color:var(--color-surface-muted)] rounded-lg p-3 border transition-all ${
                                    message.is_filtered
                                        ? 'border-red-500/50 bg-red-500/10'
                                        : 'border-[color:var(--color-outline)]'
                                }`}
                            >
                                <div className="flex items-start gap-3">
                                    {/* Avatar */}
                                    {config.show_avatars && message.author_avatar_url && (
                                        <img
                                            src={message.author_avatar_url}
                                            alt={message.author_name}
                                            className="w-8 h-8 rounded-full"
                                        />
                                    )}
                                    {!config.show_avatars && (
                                        <div className="w-8 h-8 rounded-full bg-[color:var(--color-accent)] flex items-center justify-center text-white font-bold">
                                            {message.author_name.charAt(0).toUpperCase()}
                                        </div>
                                    )}

                                    {/* Message Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="font-medium text-[color:var(--color-text)]">
                                                {message.author_name}
                                            </span>
                                            {config.show_timestamps && (
                                                <span className="text-xs text-[color:var(--color-text-muted)]">
                                                    {new Date(message.created_at).toLocaleTimeString()}
                                                </span>
                                            )}
                                            <Chip
                                                size="sm"
                                                color={getStatusColor(message.message_status)}
                                                variant="flat"
                                                startContent={getStatusIcon(message.message_status)}
                                            >
                                                {message.message_status}
                                            </Chip>
                                            {message.is_filtered && (
                                                <Chip size="sm" color="danger" variant="flat">
                                                    {t('chat.filtered', 'Отфильтровано')}
                                                </Chip>
                                            )}
                                        </div>
                                        <p className="text-sm text-[color:var(--color-text)] break-words">
                                            {message.content}
                                        </p>
                                        {message.filter_reason && (
                                            <p className="text-xs text-red-500 mt-1">
                                                {t('chat.reason', 'Причина')}: {message.filter_reason}
                                            </p>
                                        )}
                                    </div>

                                    {/* Actions */}
                                    <div className="flex gap-1">
                                        {!message.is_filtered && (
                                            <>
                                                <Button
                                                    isIconOnly
                                                    size="sm"
                                                    variant="light"
                                                    color="warning"
                                                    onPress={() => handleHideMessage(message.id)}
                                                    aria-label={t('chat.hide', 'Скрыть')}
                                                >
                                                    <EyeOff className="w-3 h-3" />
                                                </Button>
                                                <Button
                                                    isIconOnly
                                                    size="sm"
                                                    variant="light"
                                                    color="warning"
                                                    onPress={() => setSelectedMessageId(message.id)}
                                                    aria-label={t('chat.filter', 'Фильтровать')}
                                                >
                                                    <Shield className="w-3 h-3" />
                                                </Button>
                                            </>
                                        )}
                                        <Button
                                            isIconOnly
                                            size="sm"
                                            variant="light"
                                            color="danger"
                                            onPress={() => handleDeleteMessage(message.id)}
                                            aria-label={t('chat.delete', 'Удалить')}
                                        >
                                            <Trash2 className="w-3 h-3" />
                                        </Button>
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                </div>

                {/* Empty State */}
                {!loading && messages.length === 0 && (
                    <div className="text-center py-12 text-[color:var(--color-text-muted)]">
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{t('chat.noMessages', 'Нет сообщений')}</p>
                        <p className="text-sm mt-1">
                            {t('chat.messagesWillAppear', 'Сообщения появятся здесь')}
                        </p>
                    </div>
                )}

                {/* Loading State */}
                {loading && (
                    <div className="flex justify-center py-12">
                        <Spinner size="lg" />
                    </div>
                )}
            </CardBody>
        </Card>
    );
};

export default ChatOverlay;
