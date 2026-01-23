import React, { useState } from 'react';
import { MessageSquare, Users, Zap, BarChart3 } from 'lucide-react';
import { AppLayout } from '../components/layout';
import { PollManager, QAManager, ReactionOverlay, ChatOverlay, ShoutoutBanner, CTADisplay, InteractionAnalytics } from '../components';
import { useTranslation } from 'react-i18next';
import { useChannels } from '../hooks/useChannelsQuery';
import { Channel } from '../api/channels';

type InteractionTab = 'polls' | 'qa' | 'reactions' | 'chat' | 'shoutouts' | 'ctas' | 'analytics';

const InteractionsPage: React.FC = () => {
  const { t } = useTranslation();
  const { data: channels = [], isLoading: channelsLoading } = useChannels();
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [activeTab, setActiveTab] = useState<InteractionTab>('polls');

  // Filter channels - only show running channels or all channels
  const availableChannels = channels.filter(ch => ch.status === 'running' || ch.status === 'starting');

  // Auto-select first available channel
  React.useEffect(() => {
    if (!selectedChannel && availableChannels.length > 0) {
      setSelectedChannel(availableChannels[0]);
    }
  }, [availableChannels, selectedChannel]);

  const tabs: { id: InteractionTab; label: string; icon: React.ElementType }[] = [
    { id: 'polls', label: t('interactions.polls', 'Polls'), icon: BarChart3 },
    { id: 'qa', label: t('interactions.qa', 'Q&A'), icon: MessageSquare },
    { id: 'reactions', label: t('interactions.reactions', 'Reactions'), icon: Users },
    { id: 'chat', label: t('interactions.chatOverlay', 'Chat'), icon: MessageSquare },
    { id: 'shoutouts', label: t('interactions.shoutouts', 'Shoutouts'), icon: Users },
    { id: 'ctas', label: t('interactions.ctas', 'CTAs'), icon: Zap },
    { id: 'analytics', label: t('interactions.analytics', 'Analytics'), icon: BarChart3 },
  ];

  if (channelsLoading) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2 text-[color:var(--color-text)]">
              <MessageSquare className="w-6 h-6 sm:w-8 sm:h-8" />
              {t('interactions.title', 'Interactions Manager')}
            </h1>
          </div>
          <div className="animate-pulse bg-[color:var(--color-surface-muted)] rounded-xl h-64"></div>
        </div>
      </AppLayout>
    );
  }

  if (availableChannels.length === 0) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2 text-[color:var(--color-text)]">
              <MessageSquare className="w-6 h-6 sm:w-8 sm:h-8" />
              {t('interactions.title', 'Interactions Manager')}
            </h1>
          </div>

          <div className="text-center py-8 sm:py-12 bg-[color:var(--color-surface-muted)] rounded-xl border border-dashed border-[color:var(--color-border)]">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-[color:var(--color-text-muted)]" />
            <p className="text-[color:var(--color-text-muted)] text-base sm:text-lg">
              {t('interactions.noRunningChannels', 'No running channels found.')}
            </p>
            <p className="text-[color:var(--color-text-muted)] text-sm mt-2">
              {t('interactions.startChannelFirst', 'Start a channel to manage its interactions.')}
            </p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2 text-[color:var(--color-text)]">
            <MessageSquare className="w-6 h-6 sm:w-8 sm:h-8" />
            {t('interactions.title', 'Interactions Manager')}
          </h1>

          {/* Channel Selector */}
          {availableChannels.length > 1 && (
            <div className="w-full sm:w-auto">
              <select
                className="w-full sm:w-auto border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg px-4 py-2.5 text-sm"
                value={selectedChannel?.id || ''}
                onChange={(e) => {
                  const channel = channels.find(ch => ch.id === e.target.value);
                  if (channel) setSelectedChannel(channel);
                }}
              >
                {availableChannels.map((channel) => (
                  <option key={channel.id} value={channel.id}>
                    {channel.name} (ID: {channel.chat_id})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Selected Channel Info */}
        {selectedChannel && (
          <div className="mb-6 p-4 bg-[color:var(--color-surface-muted)] rounded-lg border border-[color:var(--color-border)]">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-[color:var(--color-text)]">{selectedChannel.name}</h2>
                <p className="text-sm text-[color:var(--color-text-muted)]">
                  {t('interactions.channelId', 'Channel ID')}: {selectedChannel.chat_id}
                  {selectedChannel.chat_username && ` (@${selectedChannel.chat_username})`}
                </p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  selectedChannel.status === 'running'
                    ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                }`}
              >
                {selectedChannel.status.toUpperCase()}
              </span>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 border-b border-[color:var(--color-border)]">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-4 py-2 rounded-t-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white border-b-2 border-blue-600'
                      : 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text)] hover:bg-[color:var(--color-border)]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="min-h-[500px]">
          {selectedChannel && (
            <>
              {activeTab === 'polls' && (
                <PollManager
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
              {activeTab === 'qa' && (
                <QAManager
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
              {activeTab === 'reactions' && (
                <ReactionOverlay
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
              {activeTab === 'chat' && (
                <ChatOverlay
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
              {activeTab === 'shoutouts' && (
                <ShoutoutBanner
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
              {activeTab === 'ctas' && (
                <CTADisplay
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
              {activeTab === 'analytics' && (
                <InteractionAnalytics
                  token={localStorage.getItem('token') || ''}
                  channelId={selectedChannel.chat_id}
                />
              )}
            </>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default InteractionsPage;
