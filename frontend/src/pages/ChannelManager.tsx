import React, { useState, useEffect } from 'react';
import { CreateChannelData, Channel } from '../api/channels';
import { TelegramDialog } from '../api/telegram';
import { Plus, Play, Square, RefreshCw, Tv, UserPlus, X, List, Trash2, Edit2 } from 'lucide-react';
import { TelegramLogin } from '../components/auth/TelegramLogin';
import { DialogPicker } from '../components/channels/DialogPicker';
import { SkeletonChannelCard } from '../components/ui/Skeleton';
import { ResponsiveHeader } from '../components/layout';
import { useTranslation } from 'react-i18next';
import { 
  useChannels, 
  useTelegramAccounts, 
  useCreateChannel, 
  useStartChannel, 
  useStopChannel,
  useDeleteChannel,
  useUpdateChannel,
  useUploadPlaceholder
} from '../hooks/useChannelsQuery';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../lib/queryClient';

const ChannelManager: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  
  // React Query hooks
  const { data: channels = [], isLoading: channelsLoading } = useChannels();
  const { data: accounts = [], isLoading: accountsLoading } = useTelegramAccounts();
  const createChannel = useCreateChannel();
  const startChannel = useStartChannel();
  const stopChannel = useStopChannel();
  const deleteChannel = useDeleteChannel();
  const updateChannel = useUpdateChannel();
  const uploadPlaceholder = useUploadPlaceholder();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Auto-refresh when channels are in transitional states (starting/stopping)
  useEffect(() => {
    const hasTransitionalStatus = channels.some(
      ch => ch.status === 'starting' || ch.status === 'stopping'
    );
    
    if (hasTransitionalStatus) {
      const interval = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
      }, 2000); // Poll every 2 seconds
      
      return () => clearInterval(interval);
    }
  }, [channels, queryClient]);
  
  const loading = channelsLoading || accountsLoading;
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [showDialogPicker, setShowDialogPicker] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [formData, setFormData] = useState<CreateChannelData>({
    account_id: '',
    chat_id: 0,
    name: '',
    video_quality: 'best',
    stream_type: 'video',
  });

  const handleDialogSelect = (dialog: TelegramDialog) => {
    setFormData({
      ...formData,
      chat_id: dialog.id,
      name: dialog.title,
    });
    setShowDialogPicker(false);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleCreateOrUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    let channelId = editingChannel?.id;
    
    if (editingChannel) {
      await updateChannel.mutateAsync({ id: editingChannel.id, data: formData });
    } else {
      const newChannel = await createChannel.mutateAsync(formData);
      channelId = newChannel.id;
    }
    
    if (selectedFile && channelId) {
      await uploadPlaceholder.mutateAsync({ channelId, file: selectedFile });
    }
    
    setIsModalOpen(false);
    setEditingChannel(null);
    setSelectedFile(null);
    setFormData({ account_id: '', chat_id: 0, name: '', video_quality: 'best', stream_type: 'video' });
  };

  const handleEdit = (channel: Channel) => {
    setEditingChannel(channel);
    setSelectedFile(null);
    setFormData({
      account_id: channel.account_id,
      chat_id: channel.chat_id,
      name: channel.name,
      video_quality: channel.video_quality,
      ffmpeg_args: channel.ffmpeg_args,
      stream_type: channel.stream_type as 'video' | 'audio' || 'video',
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (window.confirm(t('channels.deleteConfirm', 'Are you sure you want to delete this channel?'))) {
      await deleteChannel.mutateAsync(id);
    }
  };

  const handleStart = (id: string) => {
    startChannel.mutate(id);
  };

  const handleStop = (id: string) => {
    stopChannel.mutate(id);
  };
  
  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.channels.all });
  };

  const openCreateModal = () => {
    setEditingChannel(null);
    setFormData({ account_id: '', chat_id: 0, name: '', video_quality: 'best', stream_type: 'video' });
    setIsModalOpen(true);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[color:var(--color-surface)]">
        <ResponsiveHeader />
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
            <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2 text-[color:var(--color-text)]">
              <Tv className="w-6 h-6 sm:w-8 sm:h-8" />
              {t('channels.title', 'Channel Manager')}
            </h1>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            <SkeletonChannelCard />
            <SkeletonChannelCard />
            <SkeletonChannelCard />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)]">
      <ResponsiveHeader />
      
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Header with actions */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2 text-[color:var(--color-text)]">
            <Tv className="w-6 h-6 sm:w-8 sm:h-8" />
            {t('channels.title', 'Channel Manager')}
          </h1>
          
          {/* Action buttons - stack on mobile */}
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 w-full sm:w-auto">
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="bg-[color:var(--color-surface-muted)] hover:bg-[color:var(--color-border)] text-[color:var(--color-text)] px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors text-sm sm:text-base"
            >
              <UserPlus className="w-4 h-4 sm:w-5 sm:h-5" />
              {t('channels.connectAccount', 'Connect Account')}
            </button>
            <button
              onClick={openCreateModal}
              className="bg-[color:var(--color-accent)] hover:opacity-90 text-white px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 transition-opacity text-sm sm:text-base"
            >
              <Plus className="w-4 h-4 sm:w-5 sm:h-5" />
              {t('channels.addChannel', 'Add Channel')}
            </button>
          </div>
        </div>

        {channels.length === 0 ? (
          <div className="text-center py-8 sm:py-12 bg-[color:var(--color-surface-muted)] rounded-xl border border-dashed border-[color:var(--color-border)]">
            <Tv className="w-12 h-12 mx-auto mb-4 text-[color:var(--color-text-muted)]" />
            <p className="text-[color:var(--color-text-muted)] text-base sm:text-lg">
              {t('channels.noChannels', 'No channels configured yet.')}
            </p>
            {accounts.length === 0 ? (
               <button
                onClick={() => setIsAuthModalOpen(true)}
                className="mt-4 text-[color:var(--color-accent)] hover:underline text-sm sm:text-base"
              >
                {t('channels.connectFirst', 'Connect a Telegram account first')}
              </button>
            ) : (
              <button
                onClick={openCreateModal}
                className="mt-4 text-[color:var(--color-accent)] hover:underline text-sm sm:text-base"
              >
                {t('channels.createFirst', 'Create your first channel')}
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {channels.map((channel) => (
              <div 
                key={channel.id} 
                className="bg-[color:var(--color-panel)] rounded-xl shadow-sm border border-[color:var(--color-border)] overflow-hidden"
              >
                <div className="p-4 sm:p-5">
                  <div className="flex justify-between items-start mb-3 sm:mb-4">
                    <div className="min-w-0 flex-1 mr-3">
                      <h3 className="text-lg sm:text-xl font-semibold text-[color:var(--color-text)] truncate">
                        {channel.name}
                      </h3>
                      <p className="text-xs sm:text-sm text-[color:var(--color-text-muted)]">
                        ID: {channel.chat_id}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span
                        className={`px-2 sm:px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap ${
                          channel.status === 'running'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                            : channel.status === 'error'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                            : channel.status === 'starting' || channel.status === 'stopping'
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                            : 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)]'
                        }`}
                      >
                        {channel.status.toUpperCase()}
                      </span>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleEdit(channel)}
                          className="p-1.5 text-[color:var(--color-text-muted)] hover:text-[color:var(--color-accent)] hover:bg-[color:var(--color-surface-muted)] rounded transition-colors"
                          title={t('common.edit', 'Edit')}
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(channel.id)}
                          className="p-1.5 text-[color:var(--color-text-muted)] hover:text-red-500 hover:bg-[color:var(--color-surface-muted)] rounded transition-colors"
                          title={t('common.delete', 'Delete')}
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                  
                  <div className="space-y-1.5 sm:space-y-2 text-xs sm:text-sm text-[color:var(--color-text-muted)] mb-4 sm:mb-6">
                    <div className="flex justify-between">
                      <span>{t('channels.quality', 'Quality')}:</span>
                      <span className="font-medium text-[color:var(--color-text)]">{channel.video_quality}</span>
                    </div>
                    {channel.ffmpeg_args && (
                      <div className="flex justify-between items-start">
                        <span>{t('channels.args', 'Args')}:</span>
                        <span className="font-mono text-xs bg-[color:var(--color-surface-muted)] px-1.5 py-0.5 rounded max-w-[60%] truncate">
                          {channel.ffmpeg_args}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2 sm:gap-3">
                    {channel.status === 'stopped' || channel.status === 'error' || channel.status === 'unknown' ? (
                      <button
                        onClick={() => handleStart(channel.id)}
                        disabled={startChannel.isPending || stopChannel.isPending}
                        className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-1.5 sm:gap-2 transition-colors text-sm"
                      >
                        <Play className="w-4 h-4" /> 
                        <span className="hidden xs:inline">{t('channels.start', 'Старт')}</span>
                      </button>
                    ) : channel.status === 'stopping' ? (
                      <button
                        disabled
                        className="flex-1 bg-yellow-600 disabled:opacity-70 text-white py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-1.5 sm:gap-2 text-sm"
                      >
                        <RefreshCw className="w-4 h-4 animate-spin" /> 
                        <span className="hidden xs:inline">{t('channels.stopping', 'Остановка...')}</span>
                      </button>
                    ) : channel.status === 'starting' ? (
                      <button
                        disabled
                        className="flex-1 bg-yellow-600 disabled:opacity-70 text-white py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-1.5 sm:gap-2 text-sm"
                      >
                        <RefreshCw className="w-4 h-4 animate-spin" /> 
                        <span className="hidden xs:inline">{t('channels.starting', 'Запуск...')}</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleStop(channel.id)}
                        disabled={stopChannel.isPending}
                        className="flex-1 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white py-2 sm:py-2.5 rounded-lg flex items-center justify-center gap-1.5 sm:gap-2 transition-colors text-sm"
                      >
                        <Square className="w-4 h-4" /> 
                        <span className="hidden xs:inline">{t('channels.stop', 'Стоп')}</span>
                      </button>
                    )}
                    <button
                      onClick={handleRefresh}
                      className="p-2 sm:p-2.5 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg transition-colors"
                      title={t('common.refresh', 'Refresh Status')}
                    >
                      <RefreshCw className={`w-4 h-4 sm:w-5 sm:h-5 ${channelsLoading ? 'animate-spin' : ''}`} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add Channel Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
            <div className="bg-[color:var(--color-panel)] rounded-t-xl sm:rounded-xl p-5 sm:p-6 w-full sm:max-w-md max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl sm:text-2xl font-bold text-[color:var(--color-text)]">
                  {showDialogPicker 
                    ? t('channels.selectFromList', 'Выберите канал или группу')
                    : t('channels.addNew', 'Add New Channel')
                  }
                </h2>
                <button
                  onClick={() => {
                    if (showDialogPicker) {
                      setShowDialogPicker(false);
                    } else {
                      setIsModalOpen(false);
                    }
                  }}
                  className="p-2 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              {/* DialogPicker или форма */}
              {showDialogPicker && formData.account_id ? (
                <DialogPicker
                  accountId={formData.account_id}
                  onSelect={handleDialogSelect}
                  onCancel={() => setShowDialogPicker(false)}
                />
              ) : (
              <form onSubmit={handleCreateOrUpdate}>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                      {t('channels.telegramAccount', 'Telegram Account')}
                    </label>
                    <select
                      required
                      title={t('channels.selectAccount', 'Select Telegram Account')}
                      className="w-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg p-2.5 text-sm"
                      value={formData.account_id}
                      onChange={(e) => setFormData({ ...formData, account_id: e.target.value })}
                      disabled={!!editingChannel}
                    >
                      <option value="">{t('channels.selectAccount', 'Select Account')}</option>
                      {accounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.first_name || acc.phone} ({acc.phone})
                        </option>
                      ))}
                    </select>
                    {accounts.length === 0 && (
                      <p className="text-xs text-red-500 mt-1">
                        {t('channels.noAccounts', 'No accounts connected. Please connect an account first.')}
                      </p>
                    )}
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                      {t('channels.channelName', 'Channel Name')}
                    </label>
                    <input
                      type="text"
                      required
                      className="w-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg p-2.5 text-sm"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      placeholder={t('channels.channelNamePlaceholder', 'My Awesome Channel')}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                      {t('channels.chatId', 'Chat ID')}
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        required
                        className="flex-1 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg p-2.5 text-sm"
                        value={formData.chat_id || ''}
                        onChange={(e) => setFormData({ ...formData, chat_id: Number(e.target.value) })}
                        placeholder="-1001234567890"
                        disabled={!!editingChannel}
                      />
                      {formData.account_id && !editingChannel && (
                        <button
                          type="button"
                          onClick={() => setShowDialogPicker(true)}
                          className="px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg hover:bg-[color:var(--color-surface-muted)] transition-colors"
                          title={t('channels.selectFromList', 'Выбрать из списка')}
                        >
                          <List className="w-5 h-5" />
                        </button>
                      )}
                    </div>
                    <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                      {formData.account_id 
                        ? t('channels.chatIdHintWithPicker', 'Введите ID или выберите из списка ваших каналов')
                        : t('channels.chatIdHint', 'Enter the numeric ID of the channel/chat.')
                      }
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                      {t('channels.videoQuality', 'Video Quality')}
                    </label>
                    <select
                      title={t('channels.selectQuality', 'Select Video Quality')}
                      className="w-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg p-2.5 text-sm"
                      value={formData.video_quality}
                      onChange={(e) => setFormData({ ...formData, video_quality: e.target.value })}
                    >
                      <option value="best">{t('channels.qualityBest', 'Best')}</option>
                      <option value="worst">{t('channels.qualityWorst', 'Worst')}</option>
                      <option value="720p">720p</option>
                      <option value="480p">480p</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                      {t('channels.streamType', 'Stream Type')}
                    </label>
                    <select
                      title={t('channels.selectStreamType', 'Select Stream Type')}
                      className="w-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg p-2.5 text-sm"
                      value={formData.stream_type || 'video'}
                      onChange={(e) => setFormData({ ...formData, stream_type: e.target.value as 'video' | 'audio' })}
                    >
                      <option value="video">{t('channels.typeVideo', 'Video Chat')}</option>
                      <option value="audio">{t('channels.typeAudio', 'Voice Chat')}</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                      {t('channels.placeholder', 'Placeholder Image (for Audio Mode)')}
                    </label>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileChange}
                      className="w-full border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg p-2.5 text-sm"
                    />
                    {editingChannel?.placeholder_image && (
                      <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                        {t('channels.currentPlaceholder', 'Current: ')} {editingChannel.placeholder_image.split('/').pop()}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex flex-col-reverse sm:flex-row justify-end gap-2 sm:gap-3 mt-6">
                  <button
                    type="button"
                    onClick={() => {
                      setIsModalOpen(false);
                      setEditingChannel(null);
                    }}
                    className="w-full sm:w-auto px-4 py-2.5 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg transition-colors"
                  >
                    {t('common.cancel', 'Cancel')}
                  </button>
                  <button
                    type="submit"
                    className="w-full sm:w-auto px-4 py-2.5 bg-[color:var(--color-accent)] text-white rounded-lg hover:opacity-90 transition-opacity"
                  >
                    {editingChannel ? t('common.save', 'Save Changes') : t('channels.create', 'Create Channel')}
                  </button>
                </div>
              </form>
              )}
            </div>
          </div>
        )}

        {/* Auth Modal */}
        {isAuthModalOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
            <div className="bg-[color:var(--color-panel)] rounded-t-xl sm:rounded-xl p-5 sm:p-6 w-full sm:max-w-md max-h-[90vh] overflow-y-auto relative">
              <button 
                onClick={() => setIsAuthModalOpen(false)}
                className="absolute top-4 right-4 p-2 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
              <TelegramLogin 
                apiPrefix="/api/auth/telegram"
                onSuccess={() => {
                  setIsAuthModalOpen(false);
                  queryClient.invalidateQueries({ queryKey: queryKeys.telegram.all });
                }} 
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChannelManager;
