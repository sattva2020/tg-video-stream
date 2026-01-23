/**
 * Interaction Types
 *
 * TypeScript типы для интерактивных функций зрителей:
 * - Poll (голосования)
 * - Question (Q&A сессии)
 * - Reaction (emoji реакции)
 * - Shoutout (упоминания зрителей)
 * - CTA (призывы к действию)
 *
 * @example
 * ```ts
 * import { Poll, Question, Reaction } from '@/types/interactions';
 *
 * const poll: Poll = {
 *   id: 'poll_123',
 *   channel_id: 1,
 *   question: 'What do you want to see next?',
 *   options: [
 *     { id: 'opt_1', text: 'Gaming', votes: 42 },
 *     { id: 'opt_2', text: 'Music', votes: 38 }
 *   ],
 *   status: 'active',
 *   created_at: '2024-01-15T10:30:00Z'
 * };
 * ```
 */

// === Base Types ===

export type InteractionStatus = 'pending' | 'active' | 'paused' | 'ended' | 'cancelled';

export interface BaseInteraction {
  id: string;
  channel_id: number;
  status: InteractionStatus;
  created_at: string;
  updated_at?: string;
  ended_at?: string;
  created_by?: number;
}

// === Poll Types ===

export interface PollOption {
  id: string;
  text: string;
  votes: number;
  percentage?: number;
  order: number;
}

export interface Poll extends BaseInteraction {
  type: 'poll';
  question: string;
  options: PollOption[];
  allow_multiple_choice: boolean;
  max_choices?: number;
  total_votes: number;
  duration_seconds?: number;
  ends_at?: string;
  is_anonymous: boolean;
}

export interface PollVote {
  id: string;
  poll_id: string;
  channel_id: number;
  option_id: string;
  user_id?: number;
  username?: string;
  is_anonymous: boolean;
  voted_at: string;
}

// === Question Types (Q&A) ===

export interface Question extends BaseInteraction {
  type: 'question';
  text: string;
  author_name: string;
  author_id?: number;
  upvotes: number;
  is_answered: boolean;
  answered_at?: string;
  is_pinned: boolean;
  category?: string;
}

export interface QuestionSubmit {
  channel_id: number;
  text: string;
  author_name: string;
  author_id?: number;
  category?: string;
}

export interface QuestionUpdate {
  question_id: string;
  action: 'upvote' | 'downvote' | 'pin' | 'unpin' | 'answer' | 'delete';
  user_id?: number;
}

// === Reaction Types ===

export interface Reaction extends BaseInteraction {
  type: 'reaction';
  emoji: string;
  count: number;
  duration_seconds: number;
  position?: {
    x: number; // 0-100 (percent)
    y: number; // 0-100 (percent)
  };
  animation?: 'fade' | 'pop' | 'bounce' | 'slide';
  size?: 'small' | 'medium' | 'large';
}

export interface ReactionBatch {
  channel_id: number;
  reactions: Array<{
    emoji: string;
    count: number;
    timestamp: string;
  }>;
}

// === Shoutout Types ===

export type ShoutoutEventType = 'follow' | 'subscription' | 'donation' | 'raid' | 'cheer';

export interface Shoutout extends BaseInteraction {
  type: 'shoutout';
  event_type: ShoutoutEventType;
  user_name: string;
  user_id?: number;
  message?: string;
  amount?: number; // For donations/subscriptions
  currency?: string;
  duration_seconds: number;
  display_template?: 'minimal' | 'standard' | 'detailed';
  custom_message?: string;
}

export interface ShoutoutConfig {
  channel_id: number;
  enabled: boolean;
  auto_display: boolean;
  duration_seconds: number;
  min_tier_for_subscription?: number;
  min_amount_for_donation?: number;
  display_template: 'minimal' | 'standard' | 'detailed';
}

// === CTA (Call-to-Action) Types ===

export type CTAType = 'button' | 'banner' | 'overlay' | 'popup';

export type CTAAction = 'link' | 'subscribe' | 'follow' | 'donate' | 'custom';

export interface CTA extends BaseInteraction {
  type: 'cta';
  cta_type: CTAType;
  action_type: CTAAction;
  title: string;
  description?: string;
  button_text?: string;
  link_url?: string;
  icon?: string;
  position?: {
    x: number; // 0-100 (percent)
    y: number; // 0-100 (percent)
  };
  size?: {
    width: number; // pixels
    height: number; // pixels
  };
  display_duration_seconds?: number;
  dismissible: boolean;
  priority: number; // Higher = shown first when multiple CTAs
  click_count: number;
  dismiss_count: number;
}

export interface CTAClick {
  id: string;
  cta_id: string;
  channel_id: number;
  user_id?: number;
  action: CTAAction;
  clicked_at: string;
  metadata?: Record<string, unknown>;
}

// === Moderation Types ===

export interface ModerationRule {
  id: string;
  channel_id: number;
  rule_type: 'poll' | 'question' | 'reaction' | 'shoutout' | 'cta' | 'all';
  filter_type: 'keyword' | 'regex' | 'emoji' | 'user';
  pattern: string;
  action: 'block' | 'flag' | 'replace';
  replacement_text?: string;
  is_active: boolean;
  created_at: string;
}

export interface ModeratedItem {
  id: string;
  interaction_type: 'poll' | 'question' | 'reaction' | 'shoutout' | 'cta';
  interaction_id: string;
  channel_id: number;
  reason: string;
  rule_id: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  reviewed_at?: string;
  reviewed_by?: number;
}

// === Analytics Types ===

export interface InteractionAnalytics {
  channel_id: number;
  period_start: string;
  period_end: string;
  total_interactions: number;
  unique_participants: number;
  breakdown: {
    polls: {
      created: number;
      total_votes: number;
      avg_participation_rate: number;
    };
    questions: {
      submitted: number;
      answered: number;
      total_upvotes: number;
    };
    reactions: {
      total_reactions: number;
      unique_emojis_used: number;
    };
    shoutouts: {
      displayed: number;
      by_type: Record<ShoutoutEventType, number>;
    };
    ctas: {
      displayed: number;
      clicked: number;
      dismissed: number;
      click_rate: number;
    };
  };
}

export interface EngagementMetrics {
  channel_id: number;
  timestamp: string;
  current_interactions: number;
  active_users: number;
  engagement_score: number; // 0-100
  trend: 'up' | 'down' | 'stable';
}

// === WebSocket Events for Interactions ===

export type InteractionWebSocketEvent =
  | { type: 'poll_created'; data: Poll }
  | { type: 'poll_updated'; data: Poll }
  | { type: 'poll_ended'; data: { poll_id: string; results: PollOption[] } }
  | { type: 'vote_submitted'; data: PollVote }
  | { type: 'question_submitted'; data: Question }
  | { type: 'question_upvoted'; data: { question_id: string; upvotes: number } }
  | { type: 'question_answered'; data: { question_id: string; answered_at: string } }
  | { type: 'reaction_added'; data: Reaction }
  | { type: 'reaction_batch'; data: ReactionBatch }
  | { type: 'shoutout_triggered'; data: Shoutout }
  | { type: 'cta_displayed'; data: CTA }
  | { type: 'cta_clicked'; data: CTAClick }
  | { type: 'moderation_flagged'; data: ModeratedItem }
  | { type: 'analytics_update'; data: EngagementMetrics };

// === API Request/Response Types ===

export interface CreatePollRequest {
  channel_id: number;
  question: string;
  options: string[];
  allow_multiple_choice: boolean;
  max_choices?: number;
  duration_seconds?: number;
  is_anonymous: boolean;
}

export interface SubmitQuestionRequest {
  channel_id: number;
  text: string;
  author_name: string;
  author_id?: number;
  category?: string;
}

export interface CreateCTARequest {
  channel_id: number;
  cta_type: CTAType;
  action_type: CTAAction;
  title: string;
  description?: string;
  button_text?: string;
  link_url?: string;
  icon?: string;
  position?: { x: number; y: number };
  size?: { width: number; height: number };
  display_duration_seconds?: number;
  dismissible: boolean;
  priority: number;
}

export interface InteractionListResponse<T = BaseInteraction> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}
