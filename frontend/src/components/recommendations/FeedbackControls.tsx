/**
 * FeedbackControls Component
 * Feature: 014-ai-powered-content-recommendations
 *
 * Компонент с кнопками лайка/дизлайка для обратной связи по рекомендациям.
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { submitFeedback } from '../../api/recommendations';
import type { FeedbackType } from '../../types/recommendations';

interface FeedbackControlsProps {
  /** ID элемента плейлиста */
  playlistItemId: string;
  /** Callback при успешной отправке обратной связи */
  onFeedbackSubmitted?: (feedbackType: FeedbackType) => void;
  /** Заблокированы ли кнопки */
  disabled?: boolean;
  /** Размер кнопок */
  size?: 'sm' | 'md' | 'lg';
}

const sizeConfig = {
  sm: {
    button: 'p-1.5 rounded-lg',
    icon: 'w-3.5 h-3.5',
  },
  md: {
    button: 'p-2 rounded-xl',
    icon: 'w-4 h-4',
  },
  lg: {
    button: 'p-2.5 rounded-xl',
    icon: 'w-5 h-5',
  },
};

export const FeedbackControls: React.FC<FeedbackControlsProps> = ({
  playlistItemId,
  onFeedbackSubmitted,
  disabled = false,
  size = 'md',
}) => {
  const [selectedFeedback, setSelectedFeedback] = useState<FeedbackType | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sizeClasses = sizeConfig[size];

  const handleFeedback = async (feedbackType: FeedbackType) => {
    if (isSubmitting || disabled) return;

    setIsSubmitting(true);
    setError(null);

    try {
      await submitFeedback({
        playlist_item_id: playlistItemId,
        feedback_type: feedbackType,
      });

      setSelectedFeedback(feedbackType);

      if (onFeedbackSubmitted) {
        onFeedbackSubmitted(feedbackType);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка отправки обратной связи';
      setError(message);
      console.error('Feedback submission error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isLikeSelected = selectedFeedback === 'like';
  const isDislikeSelected = selectedFeedback === 'dislike';

  return (
    <div className="flex items-center gap-2">
      {/* Like Button */}
      <motion.button
        whileHover={!disabled && !isSubmitting ? { scale: 1.05 } : {}}
        whileTap={!disabled && !isSubmitting ? { scale: 0.95 } : {}}
        className={`
          ${sizeClasses.button}
          transition-all duration-200
          ${isLikeSelected
            ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
            : 'bg-[color:var(--color-panel)] text-[color:var(--color-text-muted)] border border-[color:var(--color-border)] hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400'
          }
          ${disabled || isSubmitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        onClick={() => handleFeedback('like')}
        disabled={disabled || isSubmitting}
        title="Нравится"
        aria-label="Нравится"
        aria-pressed={isLikeSelected}
      >
        <ThumbsUp className={sizeClasses.icon} />
      </motion.button>

      {/* Dislike Button */}
      <motion.button
        whileHover={!disabled && !isSubmitting ? { scale: 1.05 } : {}}
        whileTap={!disabled && !isSubmitting ? { scale: 0.95 } : {}}
        className={`
          ${sizeClasses.button}
          transition-all duration-200
          ${isDislikeSelected
            ? 'bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/30'
            : 'bg-[color:var(--color-panel)] text-[color:var(--color-text-muted)] border border-[color:var(--color-border)] hover:bg-rose-500/10 hover:text-rose-600 dark:hover:text-rose-400'
          }
          ${disabled || isSubmitting ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
        onClick={() => handleFeedback('dislike')}
        disabled={disabled || isSubmitting}
        title="Не нравится"
        aria-label="Не нравится"
        aria-pressed={isDislikeSelected}
      >
        <ThumbsDown className={sizeClasses.icon} />
      </motion.button>

      {/* Error Message */}
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-xs text-rose-500 dark:text-rose-400"
        >
          {error}
        </motion.p>
      )}
    </div>
  );
};

export default FeedbackControls;
