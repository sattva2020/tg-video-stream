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
    Progress,
    Textarea,
    Switch,
    Spinner
} from '@heroui/react';
import {
    Plus,
    Trash2,
    BarChart3,
    RefreshCw,
    Check,
    X,
    Users
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';
import { Poll, PollOption, CreatePollRequest } from '../../types/interactions';

interface PollManagerProps {
    token: string;
    channelId: number;
}

interface NewPollOption {
    id: string;
    text: string;
}

const PollManager: React.FC<PollManagerProps> = ({ token, channelId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Poll data
    const [polls, setPolls] = useState<Poll[]>([]);
    const [loading, setLoading] = useState(false);
    const [activePoll, setActivePoll] = useState<Poll | null>(null);

    // New poll form state
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [question, setQuestion] = useState('');
    const [options, setOptions] = useState<NewPollOption[]>([
        { id: 'opt_1', text: '' },
        { id: 'opt_2', text: '' }
    ]);
    const [allowMultiple, setAllowMultiple] = useState(false);
    const [maxChoices, setMaxChoices] = useState(1);
    const [durationSeconds, setDurationSeconds] = useState<number | undefined>(undefined);
    const [isAnonymous, setIsAnonymous] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    const fetchPolls = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get(`/api/polls?channel_id=${channelId}`);
            const data = Array.isArray(response.data) ? response.data : [];
            setPolls(data);

            // Set active poll (first non-ended poll)
            const active = data.find((p: Poll) => p.status === 'active');
            setActivePoll(active || null);
        } catch (err) {
            console.error('Failed to fetch polls', err);
            toast.error(t('polls.loadError', 'Не удалось загрузить голосования'));
            setPolls([]);
        } finally {
            setLoading(false);
        }
    }, [channelId, toast, t]);

    useEffect(() => {
        fetchPolls();
    }, [token, channelId, fetchPolls]);

    const handleAddOption = () => {
        if (options.length >= 10) {
            toast.warning(t('polls.maxOptions', 'Максимум 10 вариантов'));
            return;
        }
        setOptions([
            ...options,
            { id: `opt_${Date.now()}`, text: '' }
        ]);
    };

    const handleRemoveOption = (id: string) => {
        if (options.length <= 2) {
            toast.warning(t('polls.minOptions', 'Минимум 2 варианта'));
            return;
        }
        setOptions(options.filter(opt => opt.id !== id));
    };

    const handleOptionTextChange = (id: string, text: string) => {
        setOptions(options.map(opt =>
            opt.id === id ? { ...opt, text } : opt
        ));
    };

    const handleCreatePoll = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validation
        if (!question.trim()) {
            toast.error(t('polls.questionRequired', 'Введите вопрос'));
            return;
        }

        const validOptions = options.filter(opt => opt.text.trim());
        if (validOptions.length < 2) {
            toast.error(t('polls.minTwoOptions', 'Минимум 2 варианта ответа'));
            return;
        }

        setSubmitting(true);
        try {
            const payload: CreatePollRequest = {
                channel_id: channelId,
                question: question.trim(),
                options: validOptions.map(opt => opt.text.trim()),
                allow_multiple_choice: allowMultiple,
                max_choices: allowMultiple ? maxChoices : undefined,
                duration_seconds: durationSeconds,
                is_anonymous: isAnonymous
            };

            await client.post('/api/polls', payload);
            toast.success(t('polls.created', 'Голосование создано'));

            // Reset form
            setQuestion('');
            setOptions([{ id: 'opt_1', text: '' }, { id: 'opt_2', text: '' }]);
            setAllowMultiple(false);
            setMaxChoices(1);
            setDurationSeconds(undefined);
            setIsAnonymous(true);
            setShowCreateForm(false);

            fetchPolls();
        } catch (err) {
            console.error('Failed to create poll', err);
            toast.error(t('polls.createError', 'Не удалось создать голосование'));
        } finally {
            setSubmitting(false);
        }
    };

    const handleVote = async (optionId: string) => {
        if (!activePoll) return;

        try {
            await client.post(`/api/polls/${activePoll.id}/vote`, {
                option_id: optionId
            });
            toast.success(t('polls.voteRecorded', 'Голос записан'));
            fetchPolls();
        } catch (err) {
            console.error('Failed to vote', err);
            toast.error(t('polls.voteError', 'Не удалось записать голос'));
        }
    };

    const handleClosePoll = async (pollId: string) => {
        if (!confirm(t('polls.confirmClose', 'Завершить это голосование?'))) return;

        try {
            await client.post(`/api/polls/${pollId}/close`);
            toast.success(t('polls.closed', 'Голосование завершено'));
            fetchPolls();
        } catch (err) {
            console.error('Failed to close poll', err);
            toast.error(t('polls.closeError', 'Не удалось завершить голосование'));
        }
    };

    const handleDeletePoll = async (pollId: string) => {
        if (!confirm(t('polls.confirmDelete', 'Удалить это голосование?'))) return;

        try {
            await client.delete(`/api/polls/${pollId}`);
            toast.success(t('polls.deleted', 'Голосование удалено'));
            fetchPolls();
        } catch (err) {
            console.error('Failed to delete poll', err);
            toast.error(t('polls.deleteError', 'Не удалось удалить голосование'));
        }
    };

    const getPercentage = (votes: number, total: number) => {
        if (total === 0) return 0;
        return Math.round((votes / total) * 100);
    };

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('polls.management', 'Управление голосованиями')}
                    </h2>
                    {activePoll && (
                        <Chip
                            size="sm"
                            color="success"
                            variant="flat"
                            startContent={<Users className="w-3 h-3" />}
                        >
                            {t('polls.active', 'Активное')}
                        </Chip>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        color="primary"
                        startContent={<Plus className="w-4 h-4" />}
                        onPress={() => setShowCreateForm(!showCreateForm)}
                    >
                        {t('polls.create', 'Создать')}
                    </Button>
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchPolls}
                        isLoading={loading}
                    >
                        <RefreshCw className="w-4 h-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardBody className="space-y-6">
                {/* Create Poll Form */}
                {showCreateForm && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 space-y-4 border border-[color:var(--color-outline)]"
                    >
                        <form onSubmit={handleCreatePoll} className="space-y-4">
                            <Input
                                label={t('polls.questionLabel', 'Вопрос')}
                                placeholder={t('polls.questionPlaceholder', 'Введите вопрос...')}
                                value={question}
                                onChange={(e) => setQuestion(e.target.value)}
                                classNames={{
                                    input: 'text-[color:var(--color-text)]',
                                    inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                    label: 'text-[color:var(--color-text-muted)]'
                                }}
                                required
                            />

                            <div className="space-y-2">
                                <label className="text-sm text-[color:var(--color-text-muted)]">
                                    {t('polls.optionsLabel', 'Варианты ответа')}
                                </label>
                                {options.map((option, index) => (
                                    <div key={option.id} className="flex gap-2">
                                        <Input
                                            placeholder={`${t('polls.option', 'Вариант')} ${index + 1}`}
                                            value={option.text}
                                            onChange={(e) => handleOptionTextChange(option.id, e.target.value)}
                                            classNames={{
                                                input: 'text-[color:var(--color-text)]',
                                                inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]'
                                            }}
                                            className="flex-1"
                                            required
                                        />
                                        {options.length > 2 && (
                                            <Button
                                                isIconOnly
                                                size="sm"
                                                variant="light"
                                                color="danger"
                                                onPress={() => handleRemoveOption(option.id)}
                                            >
                                                <X className="w-4 h-4" />
                                            </Button>
                                        )}
                                    </div>
                                ))}
                                {options.length < 10 && (
                                    <Button
                                        size="sm"
                                        variant="flat"
                                        onPress={handleAddOption}
                                        startContent={<Plus className="w-4 h-4" />}
                                    >
                                        {t('polls.addOption', 'Добавить вариант')}
                                    </Button>
                                )}
                            </div>

                            <div className="flex gap-4">
                                <Switch
                                    isSelected={allowMultiple}
                                    onValueChange={setAllowMultiple}
                                >
                                    {t('polls.allowMultiple', 'Несколько вариантов')}
                                </Switch>
                                <Switch
                                    isSelected={isAnonymous}
                                    onValueChange={setIsAnonymous}
                                >
                                    {t('polls.anonymous', 'Анонимное')}
                                </Switch>
                            </div>

                            {allowMultiple && (
                                <Input
                                    type="number"
                                    label={t('polls.maxChoices', 'Макс. выборов')}
                                    value={maxChoices.toString()}
                                    onChange={(e) => setMaxChoices(Math.max(1, parseInt(e.target.value) || 1))}
                                    min="1"
                                    max={options.length}
                                    classNames={{
                                        input: 'text-[color:var(--color-text)]',
                                        inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                        label: 'text-[color:var(--color-text-muted)]'
                                    }}
                                />
                            )}

                            <Input
                                type="number"
                                label={t('polls.durationLabel', 'Длительность (секунды)')}
                                placeholder={t('polls.durationPlaceholder', 'Не ограничено')}
                                value={durationSeconds?.toString() || ''}
                                onChange={(e) => setDurationSeconds(e.target.value ? parseInt(e.target.value) : undefined)}
                                min="1"
                                classNames={{
                                    input: 'text-[color:var(--color-text)]',
                                    inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                    label: 'text-[color:var(--color-text-muted)]'
                                }}
                            />

                            <div className="flex gap-2">
                                <Button
                                    type="submit"
                                    color="primary"
                                    isLoading={submitting}
                                    startContent={!submitting && <Check className="w-4 h-4" />}
                                >
                                    {t('polls.create', 'Создать')}
                                </Button>
                                <Button
                                    type="button"
                                    variant="flat"
                                    onPress={() => setShowCreateForm(false)}
                                >
                                    {t('common.cancel', 'Отмена')}
                                </Button>
                            </div>
                        </form>
                    </motion.div>
                )}

                {/* Active Poll */}
                {activePoll && (
                    <div className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 border border-[color:var(--color-accent)]">
                        <div className="flex justify-between items-start mb-4">
                            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
                                {activePoll.question}
                            </h3>
                            <div className="flex gap-2">
                                {activePoll.status === 'active' && (
                                    <Button
                                        size="sm"
                                        color="warning"
                                        variant="flat"
                                        onPress={() => handleClosePoll(activePoll.id)}
                                    >
                                        {t('polls.end', 'Завершить')}
                                    </Button>
                                )}
                            </div>
                        </div>

                        <div className="space-y-3">
                            {activePoll.options.map((option) => {
                                const percentage = getPercentage(option.votes, activePoll.total_votes);

                                return (
                                    <motion.div
                                        key={option.id}
                                        className="relative"
                                        whileHover={{ scale: 1.01 }}
                                    >
                                        {activePoll.status === 'active' ? (
                                            <Button
                                                fullWidth
                                                variant="flat"
                                                className="justify-start h-auto py-3"
                                                onPress={() => handleVote(option.id)}
                                            >
                                                <div className="w-full text-left">
                                                    <div className="flex justify-between mb-1">
                                                        <span className="text-[color:var(--color-text)]">{option.text}</span>
                                                        <span className="text-[color:var(--color-text-muted)] text-sm">
                                                            {percentage}%
                                                        </span>
                                                    </div>
                                                    <Progress
                                                        value={percentage}
                                                        color="primary"
                                                        size="sm"
                                                        className="w-full"
                                                    />
                                                    <div className="text-xs text-[color:var(--color-text-muted)] mt-1">
                                                        {option.votes} {t('polls.votes', 'голосов')}
                                                    </div>
                                                </div>
                                            </Button>
                                        ) : (
                                            <div className="bg-[color:var(--color-panel)] rounded-lg p-3 border border-[color:var(--color-outline)]">
                                                <div className="flex justify-between mb-1">
                                                    <span className="text-[color:var(--color-text)]">{option.text}</span>
                                                    <span className="text-[color:var(--color-text-muted)] text-sm">
                                                        {percentage}%
                                                    </span>
                                                </div>
                                                <Progress
                                                    value={percentage}
                                                    color={percentage > 50 ? 'success' : 'default'}
                                                    size="sm"
                                                    className="w-full"
                                                />
                                                <div className="text-xs text-[color:var(--color-text-muted)] mt-1">
                                                    {option.votes} {t('polls.votes', 'голосов')}
                                                </div>
                                            </div>
                                        )}
                                    </motion.div>
                                );
                            })}
                        </div>

                        <div className="mt-4 text-sm text-[color:var(--color-text-muted)] flex justify-between">
                            <span>
                                {t('polls.totalVotes', 'Всего голосов')}: {activePoll.total_votes}
                            </span>
                            {activePoll.ends_at && (
                                <span>
                                    {t('polls.endsAt', 'Завершится')}: {new Date(activePoll.ends_at).toLocaleString()}
                                </span>
                            )}
                        </div>
                    </div>
                )}

                {/* Polls List */}
                {!loading && polls.length === 0 && !activePoll && (
                    <p className="text-[color:var(--color-text-muted)] text-center py-6">
                        {t('polls.noPolls', 'Нет голосований. Создайте первое!')}
                    </p>
                )}

                {loading && (
                    <div className="flex justify-center py-6">
                        <Spinner size="lg" />
                    </div>
                )}

                {/* Past Polls */}
                {!activePoll && polls.length > 0 && (
                    <div className="space-y-3">
                        <h4 className="text-sm font-semibold text-[color:var(--color-text-muted)]">
                            {t('polls.pastPolls', 'Прошлые голосования')}
                        </h4>
                        {polls.map((poll) => (
                            <div
                                key={poll.id}
                                className="bg-[color:var(--color-surface-muted)] rounded-lg p-3 border border-[color:var(--color-outline)]"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <h5 className="font-medium text-[color:var(--color-text)]">
                                        {poll.question}
                                    </h5>
                                    <div className="flex gap-1">
                                        <Button
                                            isIconOnly
                                            size="sm"
                                            variant="light"
                                            color="danger"
                                            onPress={() => handleDeletePoll(poll.id)}
                                        >
                                            <Trash2 className="w-4 h-4" />
                                        </Button>
                                    </div>
                                </div>
                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                    <Chip size="sm" variant="flat">
                                        {poll.status}
                                    </Chip>
                                    <span className="ml-2">
                                        {poll.total_votes} {t('polls.votes', 'голосов')}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardBody>
        </Card>
    );
};

export default PollManager;
