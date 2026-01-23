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
    Textarea,
    Spinner,
    Select,
    SelectItem
} from '@heroui/react';
import {
    Plus,
    MessageCircle,
    ThumbsUp,
    Check,
    Trash2,
    Pin,
    PinOff,
    RefreshCw,
    ChevronUp,
    ChevronDown,
    Filter
} from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';
import { Question, SubmitQuestionRequest } from '../../types/interactions';

interface QAManagerProps {
    token: string;
    channelId: number;
}

type QuestionFilter = 'all' | 'unanswered' | 'answered' | 'pinned';

const QAManager: React.FC<QAManagerProps> = ({ token, channelId }) => {
    const { t } = useTranslation();
    const toast = useToast();

    // Question data
    const [questions, setQuestions] = useState<Question[]>([]);
    const [loading, setLoading] = useState(false);
    const [filter, setFilter] = useState<QuestionFilter>('all');

    // New question form state
    const [showSubmitForm, setShowSubmitForm] = useState(false);
    const [questionText, setQuestionText] = useState('');
    const [authorName, setAuthorName] = useState('');
    const [category, setCategory] = useState<string>('');
    const [submitting, setSubmitting] = useState(false);

    const categories = [
        { key: 'general', label: 'General' },
        { key: 'technical', label: 'Technical' },
        { key: 'content', label: 'Content' },
        { key: 'other', label: 'Other' }
    ];

    const fetchQuestions = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get(`/api/qa/questions?channel_id=${channelId}`);
            const data = Array.isArray(response.data) ? response.data : [];
            setQuestions(data);
        } catch (err) {
            console.error('Failed to fetch questions', err);
            toast.error(t('qa.loadError', 'Не удалось загрузить вопросы'));
            setQuestions([]);
        } finally {
            setLoading(false);
        }
    }, [channelId, toast, t]);

    useEffect(() => {
        fetchQuestions();
    }, [token, channelId, fetchQuestions]);

    const handleSubmitQuestion = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validation
        if (!questionText.trim()) {
            toast.error(t('qa.questionRequired', 'Введите вопрос'));
            return;
        }

        if (!authorName.trim()) {
            toast.error(t('qa.authorRequired', 'Введите ваше имя'));
            return;
        }

        setSubmitting(true);
        try {
            const payload: SubmitQuestionRequest = {
                channel_id: channelId,
                text: questionText.trim(),
                author_name: authorName.trim(),
                category: category || undefined
            };

            await client.post('/api/qa/questions', payload);
            toast.success(t('qa.submitted', 'Вопрос отправлен'));

            // Reset form
            setQuestionText('');
            setAuthorName('');
            setCategory('');
            setShowSubmitForm(false);

            fetchQuestions();
        } catch (err) {
            console.error('Failed to submit question', err);
            toast.error(t('qa.submitError', 'Не удалось отправить вопрос'));
        } finally {
            setSubmitting(false);
        }
    };

    const handleUpvote = async (questionId: string) => {
        try {
            await client.post(`/api/qa/questions/${questionId}/upvote`);
            fetchQuestions();
        } catch (err) {
            console.error('Failed to upvote question', err);
            toast.error(t('qa.upvoteError', 'Не удалось проголосовать'));
        }
    };

    const handleDownvote = async (questionId: string) => {
        try {
            await client.post(`/api/qa/questions/${questionId}/downvote`);
            fetchQuestions();
        } catch (err) {
            console.error('Failed to downvote question', err);
            toast.error(t('qa.downvoteError', 'Не убрать голос'));
        }
    };

    const handleTogglePin = async (questionId: string, currentlyPinned: boolean) => {
        try {
            const action = currentlyPinned ? 'unpin' : 'pin';
            await client.post(`/api/qa/questions/${questionId}/${action}`);
            toast.success(currentlyPinned
                ? t('qa.unpinned', 'Вопрос откреплен')
                : t('qa.pinned', 'Вопрос закреплен')
            );
            fetchQuestions();
        } catch (err) {
            console.error('Failed to toggle pin', err);
            toast.error(t('qa.pinError', 'Не удалось изменить закрепление'));
        }
    };

    const handleMarkAnswered = async (questionId: string) => {
        try {
            await client.post(`/api/qa/questions/${questionId}/answer`);
            toast.success(t('qa.markedAnswered', 'Вопрос отмечен как отвеченный'));
            fetchQuestions();
        } catch (err) {
            console.error('Failed to mark as answered', err);
            toast.error(t('qa.markError', 'Не удалось отметить вопрос'));
        }
    };

    const handleDeleteQuestion = async (questionId: string) => {
        if (!confirm(t('qa.confirmDelete', 'Удалить этот вопрос?'))) return;

        try {
            await client.delete(`/api/qa/questions/${questionId}`);
            toast.success(t('qa.deleted', 'Вопрос удален'));
            fetchQuestions();
        } catch (err) {
            console.error('Failed to delete question', err);
            toast.error(t('qa.deleteError', 'Не удалось удалить вопрос'));
        }
    };

    // Filter questions
    const filteredQuestions = questions.filter(q => {
        switch (filter) {
            case 'unanswered':
                return !q.is_answered;
            case 'answered':
                return q.is_answered;
            case 'pinned':
                return q.is_pinned;
            default:
                return true;
        }
    });

    // Sort: pinned first, then by upvotes
    const sortedQuestions = [...filteredQuestions].sort((a, b) => {
        if (a.is_pinned && !b.is_pinned) return -1;
        if (!a.is_pinned && b.is_pinned) return 1;
        return b.upvotes - a.upvotes;
    });

    const getCategoryLabel = (cat: string | undefined) => {
        if (!cat) return null;
        const found = categories.find(c => c.key === cat);
        return found?.label || cat;
    };

    const getCategoryColor = (cat: string | undefined) => {
        switch (cat) {
            case 'technical': return 'warning';
            case 'content': return 'success';
            case 'general': return 'primary';
            default: return 'default';
        }
    };

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('qa.management', 'Управление вопросами')}
                    </h2>
                    <Chip
                        size="sm"
                        color="primary"
                        variant="flat"
                        startContent={<MessageCircle className="w-3 h-3" />}
                    >
                        {questions.length}
                    </Chip>
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        size="sm"
                        color="primary"
                        startContent={<Plus className="w-4 h-4" />}
                        onPress={() => setShowSubmitForm(!showSubmitForm)}
                    >
                        {t('qa.submit', 'Задать вопрос')}
                    </Button>
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchQuestions}
                        isLoading={loading}
                    >
                        <RefreshCw className="w-4 h-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardBody className="space-y-6">
                {/* Submit Question Form */}
                <AnimatePresence>
                    {showSubmitForm && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="bg-[color:var(--color-surface-muted)] rounded-lg p-4 space-y-4 border border-[color:var(--color-outline)]"
                        >
                            <form onSubmit={handleSubmitQuestion} className="space-y-4">
                                <Textarea
                                    label={t('qa.questionLabel', 'Ваш вопрос')}
                                    placeholder={t('qa.questionPlaceholder', 'Введите ваш вопрос...')}
                                    value={questionText}
                                    onChange={(e) => setQuestionText(e.target.value)}
                                    minRows={2}
                                    maxRows={4}
                                    classNames={{
                                        input: 'text-[color:var(--color-text)]',
                                        inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                        label: 'text-[color:var(--color-text-muted)]'
                                    }}
                                    required
                                />

                                <div className="flex gap-4">
                                    <Input
                                        label={t('qa.authorLabel', 'Ваше имя')}
                                        placeholder={t('qa.authorPlaceholder', 'Анонимный зритель')}
                                        value={authorName}
                                        onChange={(e) => setAuthorName(e.target.value)}
                                        classNames={{
                                            input: 'text-[color:var(--color-text)]',
                                            inputWrapper: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)]',
                                            label: 'text-[color:var(--color-text-muted)]'
                                        }}
                                        className="flex-1"
                                        required
                                    />

                                    <Select
                                        label={t('qa.categoryLabel', 'Категория')}
                                        placeholder={t('qa.categoryPlaceholder', 'Выберите категорию')}
                                        selectedKeys={category ? [category] : []}
                                        onSelectionChange={(keys) => {
                                            const selected = Array.from(keys)[0] as string;
                                            setCategory(selected);
                                        }}
                                        classNames={{
                                            label: 'text-[color:var(--color-text-muted)]',
                                            trigger: 'bg-[color:var(--color-panel)] border-[color:var(--color-outline)] text-[color:var(--color-text)]',
                                            value: 'text-[color:var(--color-text)]'
                                        }}
                                        className="flex-1"
                                    >
                                        {categories.map(cat => (
                                            <SelectItem key={cat.key}>
                                                {cat.label}
                                            </SelectItem>
                                        ))}
                                    </Select>
                                </div>

                                <div className="flex gap-2">
                                    <Button
                                        type="submit"
                                        color="primary"
                                        isLoading={submitting}
                                        startContent={!submitting && <MessageCircle className="w-4 h-4" />}
                                    >
                                        {t('qa.submit', 'Отправить вопрос')}
                                    </Button>
                                    <Button
                                        type="button"
                                        variant="flat"
                                        onPress={() => setShowSubmitForm(false)}
                                    >
                                        {t('common.cancel', 'Отмена')}
                                    </Button>
                                </div>
                            </form>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Filter */}
                <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-[color:var(--color-text-muted)]" />
                    <div className="flex gap-2">
                        {(['all', 'unanswered', 'answered', 'pinned'] as QuestionFilter[]).map(f => (
                            <Chip
                                key={f}
                                size="sm"
                                color={filter === f ? 'primary' : 'default'}
                                variant={filter === f ? 'solid' : 'flat'}
                                className="cursor-pointer"
                                onPress={() => setFilter(f)}
                            >
                                {t(`qa.filter.${f}`, f)}
                            </Chip>
                        ))}
                    </div>
                </div>

                {/* Questions List */}
                {loading && (
                    <div className="flex justify-center py-6">
                        <Spinner size="lg" />
                    </div>
                )}

                {!loading && sortedQuestions.length === 0 && (
                    <p className="text-[color:var(--color-text-muted)] text-center py-6">
                        {filter === 'all'
                            ? t('qa.noQuestions', 'Нет вопросов. Задайте первый!')
                            : t('qa.noFilteredQuestions', 'Нет вопросов в этой категории')
                        }
                    </p>
                )}

                {!loading && sortedQuestions.length > 0 && (
                    <div className="space-y-3">
                        <AnimatePresence mode="popLayout">
                            {sortedQuestions.map((question, index) => (
                                <motion.div
                                    key={question.id}
                                    layout
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, scale: 0.9 }}
                                    transition={{ delay: index * 0.05 }}
                                    className={`bg-[color:var(--color-surface-muted)] rounded-lg p-4 border transition-colors ${
                                        question.is_pinned
                                            ? 'border-[color:var(--color-accent)] shadow-lg'
                                            : 'border-[color:var(--color-outline)]'
                                    } ${question.is_answered ? 'opacity-70' : ''}`}
                                >
                                    <div className="flex gap-4">
                                        {/* Upvote Section */}
                                        <div className="flex flex-col items-center gap-1">
                                            <Button
                                                isIconOnly
                                                size="sm"
                                                variant="light"
                                                onPress={() => handleUpvote(question.id)}
                                                isDisabled={question.is_answered}
                                            >
                                                <ChevronUp className="w-5 h-5" />
                                            </Button>
                                            <span className="text-lg font-bold text-[color:var(--color-text)]">
                                                {question.upvotes}
                                            </span>
                                            <Button
                                                isIconOnly
                                                size="sm"
                                                variant="light"
                                                onPress={() => handleDownvote(question.id)}
                                                isDisabled={question.is_answered}
                                            >
                                                <ChevronDown className="w-5 h-5" />
                                            </Button>
                                        </div>

                                        {/* Question Content */}
                                        <div className="flex-1">
                                            <div className="flex items-start justify-between gap-2 mb-2">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    {question.is_pinned && (
                                                        <Pin className="w-4 h-4 text-[color:var(--color-accent)]" />
                                                    )}
                                                    {question.is_answered && (
                                                        <Chip
                                                            size="sm"
                                                            color="success"
                                                            variant="flat"
                                                            startContent={<Check className="w-3 h-3" />}
                                                        >
                                                            {t('qa.answered', 'Отвечен')}
                                                        </Chip>
                                                    )}
                                                    {question.category && (
                                                        <Chip
                                                            size="sm"
                                                            color={getCategoryColor(question.category)}
                                                            variant="flat"
                                                        >
                                                            {getCategoryLabel(question.category)}
                                                        </Chip>
                                                    )}
                                                </div>
                                                <div className="flex gap-1">
                                                    <Button
                                                        isIconOnly
                                                        size="sm"
                                                        variant="light"
                                                        onPress={() => handleTogglePin(question.id, question.is_pinned)}
                                                    >
                                                        {question.is_pinned
                                                            ? <PinOff className="w-4 h-4" />
                                                            : <Pin className="w-4 h-4" />
                                                        }
                                                    </Button>
                                                    {!question.is_answered && (
                                                        <Button
                                                            isIconOnly
                                                            size="sm"
                                                            variant="light"
                                                            color="success"
                                                            onPress={() => handleMarkAnswered(question.id)}
                                                        >
                                                            <Check className="w-4 h-4" />
                                                        </Button>
                                                    )}
                                                    <Button
                                                        isIconOnly
                                                        size="sm"
                                                        variant="light"
                                                        color="danger"
                                                        onPress={() => handleDeleteQuestion(question.id)}
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </Button>
                                                </div>
                                            </div>

                                            <p className="text-[color:var(--color-text)] font-medium mb-2">
                                                {question.text}
                                            </p>

                                            <div className="flex items-center gap-2 text-sm text-[color:var(--color-text-muted)]">
                                                <span>{question.author_name}</span>
                                                <span>•</span>
                                                <span>{new Date(question.created_at).toLocaleString()}</span>
                                            </div>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </CardBody>
        </Card>
    );
};

export default QAManager;
