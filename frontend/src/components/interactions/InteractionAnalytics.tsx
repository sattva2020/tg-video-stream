/**
 * InteractionAnalytics Component
 *
 * Компонент для отображения аналитики интерактивных функций зрителей.
 * Показывает статистику по голосованиям, Q&A, реакциям, шаутаутам и CTA.
 *
 * @example
 * ```tsx
 * <InteractionAnalytics token="abc123" channelId={1} />
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
    Select,
    SelectItem,
    Chip,
    Spinner,
    Progress
} from '@heroui/react';
import {
    BarChart3,
    RefreshCw,
    TrendingUp,
    TrendingDown,
    Minus,
    Users,
    MessageSquare,
    Heart,
    Megaphone,
    MousePointerClick,
    Calendar
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';
import {
    InteractionAnalytics as InteractionAnalyticsData,
    EngagementMetrics
} from '../../types/interactions';

interface InteractionAnalyticsProps {
    token: string;
    channelId: number;
}

type TimePeriod = '1h' | '24h' | '7d' | '30d';

const InteractionAnalytics: React.FC<InteractionAnalyticsProps> = ({ token, channelId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Data state
    const [analytics, setAnalytics] = useState<InteractionAnalyticsData | null>(null);
    const [engagementMetrics, setEngagementMetrics] = useState<EngagementMetrics | null>(null);
    const [loading, setLoading] = useState(false);
    const [period, setPeriod] = useState<TimePeriod>('24h');

    const fetchAnalytics = useCallback(async () => {
        setLoading(true);
        try {
            // Calculate period start/end based on selected period
            const now = new Date();
            let periodStart = new Date();

            switch (period) {
                case '1h':
                    periodStart = new Date(now.getTime() - 60 * 60 * 1000);
                    break;
                case '24h':
                    periodStart = new Date(now.getTime() - 24 * 60 * 60 * 1000);
                    break;
                case '7d':
                    periodStart = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                    break;
                case '30d':
                    periodStart = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
                    break;
            }

            const params = {
                channel_id: channelId,
                period_start: periodStart.toISOString(),
                period_end: now.toISOString()
            };

            const response = await client.get('/api/analytics/interactions', { params });
            setAnalytics(response.data);
        } catch (err) {
            console.error('Failed to fetch interaction analytics', err);
            toast.error(t('analytics.loadError', 'Не удалось загрузить аналитику'));
            setAnalytics(null);
        } finally {
            setLoading(false);
        }
    }, [channelId, period, toast, t]);

    const fetchEngagementMetrics = useCallback(async () => {
        try {
            const response = await client.get(`/api/analytics/engagement?channel_id=${channelId}`);
            setEngagementMetrics(response.data);
        } catch (err) {
            console.error('Failed to fetch engagement metrics', err);
            setEngagementMetrics(null);
        }
    }, [channelId]);

    useEffect(() => {
        fetchAnalytics();
    }, [token, channelId, period, fetchAnalytics]);

    useEffect(() => {
        fetchEngagementMetrics();
        // Refresh engagement metrics every 30 seconds
        const interval = setInterval(fetchEngagementMetrics, 30000);
        return () => clearInterval(interval);
    }, [token, channelId, fetchEngagementMetrics]);

    const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
        switch (trend) {
            case 'up':
                return <TrendingUp className="w-4 h-4 text-success" />;
            case 'down':
                return <TrendingDown className="w-4 h-4 text-danger" />;
            case 'stable':
                return <Minus className="w-4 h-4 text-default" />;
        }
    };

    const formatNumber = (num: number): string => {
        if (num >= 1000000) {
            return `${(num / 1000000).toFixed(1)}M`;
        }
        if (num >= 1000) {
            return `${(num / 1000).toFixed(1)}K`;
        }
        return num.toString();
    };

    const getPeriodLabel = (period: TimePeriod): string => {
        switch (period) {
            case '1h':
                return t('analytics.period.1h', '1 час');
            case '24h':
                return t('analytics.period.24h', '24 часа');
            case '7d':
                return t('analytics.period.7d', '7 дней');
            case '30d':
                return t('analytics.period.30d', '30 дней');
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <Card>
                <CardHeader className="flex justify-between items-center gap-4">
                    <div className="flex items-center gap-3">
                        <BarChart3 className="w-6 h-6 text-[color:var(--color-accent)]" />
                        <div>
                            <h2 className="text-xl font-bold">
                                {t('analytics.title', 'Аналитика взаимодействий')}
                            </h2>
                            <p className="text-sm text-[color:var(--color-text-muted)]">
                                {t('analytics.subtitle', 'Статистика интерактивных функций зрителей')}
                            </p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Select
                            size="sm"
                            className="w-32"
                            defaultSelectedKeys={['24h']}
                            onChange={(e) => setPeriod(e.target.value as TimePeriod)}
                        >
                            <SelectItem key="1h">{getPeriodLabel('1h')}</SelectItem>
                            <SelectItem key="24h">{getPeriodLabel('24h')}</SelectItem>
                            <SelectItem key="7d">{getPeriodLabel('7d')}</SelectItem>
                            <SelectItem key="30d">{getPeriodLabel('30d')}</SelectItem>
                        </Select>
                        <Button
                            isIconOnly
                            size="sm"
                            variant="light"
                            onPress={fetchAnalytics}
                            isDisabled={loading}
                        >
                            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                    </div>
                </CardHeader>
            </Card>

            {loading && !analytics && (
                <Card>
                    <CardBody className="flex justify-center items-center py-12">
                        <Spinner size="lg" />
                    </CardBody>
                </Card>
            )}

            {analytics && (
                <>
                    {/* Overall Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {/* Total Interactions */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3 }}
                        >
                            <Card className="h-full">
                                <CardBody className="gap-2">
                                    <div className="flex items-center justify-between">
                                        <div className="p-2 rounded-lg bg-[color:var(--color-primary)]/10">
                                            <MessageSquare className="w-5 h-5 text-[color:var(--color-primary)]" />
                                        </div>
                                        {engagementMetrics && getTrendIcon(engagementMetrics.trend)}
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.totalInteractions', 'Всего взаимодействий')}
                                        </p>
                                        <p className="text-2xl font-bold">
                                            {formatNumber(analytics.total_interactions)}
                                        </p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>

                        {/* Unique Participants */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, delay: 0.1 }}
                        >
                            <Card className="h-full">
                                <CardBody className="gap-2">
                                    <div className="flex items-center justify-between">
                                        <div className="p-2 rounded-lg bg-[color:var(--color-success)]/10">
                                            <Users className="w-5 h-5 text-[color:var(--color-success)]" />
                                        </div>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.uniqueParticipants', 'Уникальных участников')}
                                        </p>
                                        <p className="text-2xl font-bold">
                                            {formatNumber(analytics.unique_participants)}
                                        </p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>

                        {/* Engagement Score */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, delay: 0.2 }}
                        >
                            <Card className="h-full">
                                <CardBody className="gap-2">
                                    <div className="flex items-center justify-between">
                                        <div className="p-2 rounded-lg bg-[color:var(--color-warning)]/10">
                                            <Heart className="w-5 h-5 text-[color:var(--color-warning)]" />
                                        </div>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.engagementScore', 'Индекс вовлечённости')}
                                        </p>
                                        <p className="text-2xl font-bold">
                                            {engagementMetrics ? engagementMetrics.engagement_score.toFixed(0) : '0'}%
                                        </p>
                                    </div>
                                    {engagementMetrics && (
                                        <Progress
                                            value={engagementMetrics.engagement_score}
                                            color="warning"
                                            className="w-full"
                                            size="sm"
                                        />
                                    )}
                                </CardBody>
                            </Card>
                        </motion.div>

                        {/* Active Users */}
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.3, delay: 0.3 }}
                        >
                            <Card className="h-full">
                                <CardBody className="gap-2">
                                    <div className="flex items-center justify-between">
                                        <div className="p-2 rounded-lg bg-[color:var(--color-accent)]/10">
                                            <TrendingUp className="w-5 h-5 text-[color:var(--color-accent)]" />
                                        </div>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.activeUsers', 'Активных сейчас')}
                                        </p>
                                        <p className="text-2xl font-bold">
                                            {engagementMetrics ? formatNumber(engagementMetrics.active_users) : '0'}
                                        </p>
                                    </div>
                                </CardBody>
                            </Card>
                        </motion.div>
                    </div>

                    {/* Breakdown by Type */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Polls */}
                        <Card>
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <BarChart3 className="w-5 h-5 text-[color:var(--color-primary)]" />
                                    <h3 className="font-semibold">
                                        {t('analytics.polls', 'Голосования')}
                                    </h3>
                                </div>
                            </CardHeader>
                            <CardBody className="gap-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.pollsCreated', 'Создано')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.polls.created}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.totalVotes', 'Голосов')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {formatNumber(analytics.breakdown.polls.total_votes)}
                                        </p>
                                    </div>
                                </div>
                                <div>
                                    <div className="flex justify-between text-sm mb-1">
                                        <span className="text-[color:var(--color-text-muted)]">
                                            {t('analytics.participationRate', 'Участие')}
                                        </span>
                                        <span className="font-semibold">
                                            {analytics.breakdown.polls.avg_participation_rate.toFixed(1)}%
                                        </span>
                                    </div>
                                    <Progress
                                        value={analytics.breakdown.polls.avg_participation_rate}
                                        color="primary"
                                        size="sm"
                                    />
                                </div>
                            </CardBody>
                        </Card>

                        {/* Questions */}
                        <Card>
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <MessageSquare className="w-5 h-5 text-[color:var(--color-success)]" />
                                    <h3 className="font-semibold">
                                        {t('analytics.questions', 'Вопросы и ответы')}
                                    </h3>
                                </div>
                            </CardHeader>
                            <CardBody className="gap-4">
                                <div className="grid grid-cols-3 gap-4">
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.questionsSubmitted', 'Отправлено')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.questions.submitted}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.questionsAnswered', 'Отвечено')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.questions.answered}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.totalUpvotes', 'Апвоутов')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {formatNumber(analytics.breakdown.questions.total_upvotes)}
                                        </p>
                                    </div>
                                </div>
                                {analytics.breakdown.questions.submitted > 0 && (
                                    <Chip size="sm" variant="flat" color="success">
                                        {((analytics.breakdown.questions.answered / analytics.breakdown.questions.submitted) * 100).toFixed(1)}%
                                        {' '}{t('analytics.answerRate', 'ответов')}
                                    </Chip>
                                )}
                            </CardBody>
                        </Card>

                        {/* Reactions */}
                        <Card>
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <Heart className="w-5 h-5 text-[color:var(--color-danger)]" />
                                    <h3 className="font-semibold">
                                        {t('analytics.reactions', 'Реакции')}
                                    </h3>
                                </div>
                            </CardHeader>
                            <CardBody className="gap-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.totalReactions', 'Всего реакций')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {formatNumber(analytics.breakdown.reactions.total_reactions)}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.uniqueEmojis', 'Уникальных эмодзи')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.reactions.unique_emojis_used}
                                        </p>
                                    </div>
                                </div>
                            </CardBody>
                        </Card>

                        {/* Shoutouts */}
                        <Card>
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <Megaphone className="w-5 h-5 text-[color:var(--color-warning)]" />
                                    <h3 className="font-semibold">
                                        {t('analytics.shoutouts', 'Шаутауты')}
                                    </h3>
                                </div>
                            </CardHeader>
                            <CardBody className="gap-4">
                                <div>
                                    <p className="text-sm text-[color:var(--color-text-muted)]">
                                        {t('analytics.shoutoutsDisplayed', 'Показано')}
                                    </p>
                                    <p className="text-xl font-bold">
                                        {analytics.breakdown.shoutouts.displayed}
                                    </p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(analytics.breakdown.shoutouts.by_type).map(([type, count]) => (
                                        count > 0 && (
                                            <Chip key={type} size="sm" variant="flat">
                                                {type}: {count}
                                            </Chip>
                                        )
                                    ))}
                                </div>
                            </CardBody>
                        </Card>

                        {/* CTAs */}
                        <Card className="lg:col-span-2">
                            <CardHeader>
                                <div className="flex items-center gap-2">
                                    <MousePointerClick className="w-5 h-5 text-[color:var(--color-accent)]" />
                                    <h3 className="font-semibold">
                                        {t('analytics.ctas', 'Призывы к действию (CTA)')}
                                    </h3>
                                </div>
                            </CardHeader>
                            <CardBody>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.ctasDisplayed', 'Показано')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.ctas.displayed}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.ctasClicked', 'Кликов')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.ctas.clicked}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.ctasDismissed', 'Закрыто')}
                                        </p>
                                        <p className="text-xl font-bold">
                                            {analytics.breakdown.ctas.dismissed}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-[color:var(--color-text-muted)]">
                                            {t('analytics.ctr', 'CTR')}
                                        </p>
                                        <p className="text-xl font-bold text-[color:var(--color-success)]">
                                            {analytics.breakdown.ctas.click_rate.toFixed(1)}%
                                        </p>
                                    </div>
                                </div>
                                {analytics.breakdown.ctas.displayed > 0 && (
                                    <div className="mt-4">
                                        <div className="flex justify-between text-sm mb-1">
                                            <span className="text-[color:var(--color-text-muted)]">
                                                {t('analytics.clickRate', 'Кликабельность')}
                                            </span>
                                            <span className="font-semibold">
                                                {analytics.breakdown.ctas.click_rate.toFixed(1)}%
                                            </span>
                                        </div>
                                        <Progress
                                            value={analytics.breakdown.ctas.click_rate}
                                            color="success"
                                            size="sm"
                                        />
                                    </div>
                                )}
                            </CardBody>
                        </Card>
                    </div>

                    {/* Period Info */}
                    <Card>
                        <CardBody className="flex items-center justify-between">
                            <div className="flex items-center gap-2 text-sm text-[color:var(--color-text-muted)]">
                                <Calendar className="w-4 h-4" />
                                <span>
                                    {t('analytics.periodInfo', 'Период')}: {getPeriodLabel(period)}
                                </span>
                            </div>
                        </CardBody>
                    </Card>
                </>
            )}
        </div>
    );
};

export default InteractionAnalytics;
