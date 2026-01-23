import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users,
  UserPlus,
  Mail,
  Loader2,
  Search,
  X,
  Shield,
  Video,
  Mic,
  Monitor,
  MoreVertical,
  Check,
  AlertCircle,
  Copy,
  Link as LinkIcon,
  Crown
} from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface GuestPermissions {
  can_speak: boolean;
  can_share_video: boolean;
  can_share_screen: boolean;
  can_control_stream: boolean;
  can_invite_others: boolean;
}

export interface GuestSession {
  id: string;
  live_stream_id: string;
  user_id: string;
  status: 'pending' | 'accepted' | 'active' | 'rejected' | 'left' | 'kicked';
  permissions: GuestPermissions;
  invite_token?: string;
  invite_message?: string;
  webrtc_connection_id?: string;
  connection_quality?: 'good' | 'fair' | 'poor';
  created_at: string;
  joined_at?: string;
  left_at?: string;
  last_active_at?: string;
  rejection_reason?: string;
  leave_reason?: string;
  user?: {
    id: string;
    username?: string;
    email?: string;
    full_name?: string;
  };
}

export interface GuestManagerProps {
  streamId: string;
  isHost: boolean;
  currentUserId?: string;
  onInviteGuest?: (email: string, message?: string) => void;
  onRemoveGuest?: (guestId: string) => void;
  onUpdatePermissions?: (guestId: string, permissions: GuestPermissions) => void;
  className?: string;
}

export const GuestManager: React.FC<GuestManagerProps> = ({
  streamId,
  isHost,
  currentUserId,
  onInviteGuest,
  onRemoveGuest,
  onUpdatePermissions,
  className = '',
}) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteMessage, setInviteMessage] = useState('');
  const [selectedGuest, setSelectedGuest] = useState<GuestSession | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // Query to fetch guests - placeholder until API client is implemented in subtask 6-7
  const { data: guests = [], isLoading, error } = useQuery({
    queryKey: ['live', 'guests', streamId],
    queryFn: async () => {
      // TODO: Replace with actual API call in subtask 6-7
      // return await liveApi.guests.list(streamId);
      return [];
    },
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 15 * 1000, // Refresh every 15 seconds
    enabled: !!streamId,
  });

  // Filter guests by search
  const filteredGuests = guests.filter((guest: GuestSession) => {
    const searchLower = search.toLowerCase();
    return (
      guest.user?.username?.toLowerCase().includes(searchLower) ||
      guest.user?.email?.toLowerCase().includes(searchLower) ||
      guest.user?.full_name?.toLowerCase().includes(searchLower)
    );
  });

  // Group guests by status
  const activeGuests = filteredGuests.filter((g: GuestSession) => g.status === 'active');
  const pendingGuests = filteredGuests.filter((g: GuestSession) => g.status === 'pending' || g.status === 'accepted');
  const inactiveGuests = filteredGuests.filter((g: GuestSession) => ['rejected', 'left', 'kicked'].includes(g.status));

  const getStatusColor = (status: GuestSession['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 border-green-300 dark:border-green-700';
      case 'accepted':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 border-blue-300 dark:border-blue-700';
      case 'pending':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 border-yellow-300 dark:border-yellow-700';
      case 'rejected':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-300 dark:border-red-700';
      case 'left':
        return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400 border-gray-300 dark:border-gray-700';
      case 'kicked':
        return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-300 dark:border-red-700';
      default:
        return 'bg-gray-100 dark:bg-gray-900/30 text-gray-700 dark:text-gray-400';
    }
  };

  const getStatusLabel = (status: GuestSession['status']) => {
    switch (status) {
      case 'active':
        return t('live.guest.statusActive', 'Active');
      case 'accepted':
        return t('live.guest.statusAccepted', 'Accepted');
      case 'pending':
        return t('live.guest.statusPending', 'Pending');
      case 'rejected':
        return t('live.guest.statusRejected', 'Declined');
      case 'left':
        return t('live.guest.statusLeft', 'Left');
      case 'kicked':
        return t('live.guest.statusKicked', 'Kicked');
      default:
        return status;
    }
  };

  const getQualityColor = (quality?: string) => {
    switch (quality) {
      case 'good':
        return 'text-green-500';
      case 'fair':
        return 'text-yellow-500';
      case 'poor':
        return 'text-red-500';
      default:
        return 'text-gray-400';
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;

    try {
      // TODO: Replace with actual API call in subtask 6-7
      // await liveApi.guests.invite(streamId, inviteEmail, inviteMessage);
      onInviteGuest?.(inviteEmail, inviteMessage);
      setInviteEmail('');
      setInviteMessage('');
      setShowInviteModal(false);
      queryClient.invalidateQueries({ queryKey: ['live', 'guests', streamId] });
    } catch (err) {
      // Error will be handled by mutation error state
    }
  };

  const handleRemoveGuest = async (guestId: string) => {
    if (!confirm(t('live.guest.confirmRemove', 'Are you sure you want to remove this guest?'))) {
      return;
    }

    try {
      // TODO: Replace with actual API call in subtask 6-7
      // await liveApi.guests.remove(guestId);
      onRemoveGuest?.(guestId);
      queryClient.invalidateQueries({ queryKey: ['live', 'guests', streamId] });
    } catch (err) {
      // Error will be handled by mutation error state
    }
  };

  const handleCopyInviteLink = (token: string) => {
    const inviteLink = `${window.location.origin}/live/guest/join?token=${token}`;
    navigator.clipboard.writeText(inviteLink);
    setCopiedToken(token);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const togglePermission = async (guest: GuestSession, permission: keyof GuestPermissions) => {
    const newPermissions = {
      ...guest.permissions,
      [permission]: !guest.permissions[permission],
    };

    try {
      // TODO: Replace with actual API call in subtask 6-7
      // await liveApi.guests.updatePermissions(guest.id, newPermissions);
      onUpdatePermissions?.(guest.id, newPermissions);
      queryClient.invalidateQueries({ queryKey: ['live', 'guests', streamId] });
    } catch (err) {
      // Error will be handled by mutation error state
    }
  };

  const renderGuestItem = (guest: GuestSession) => (
    <div
      key={guest.id}
      className="p-4 bg-[color:var(--color-surface)] border border-[color:var(--color-border)] rounded-lg hover:border-[color:var(--color-accent)] transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        {/* Guest info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-[color:var(--color-text)]">
              {guest.user?.full_name || guest.user?.username || guest.user?.email || t('live.guest.unknownUser', 'Unknown User')}
            </span>
            {guest.user_id === currentUserId && (
              <span className="flex-shrink-0 px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 text-xs rounded border border-purple-300 dark:border-purple-700">
                {t('live.guest.you', 'You')}
              </span>
            )}
            {guest.status === 'active' && guest.webrtc_connection_id && (
              <div className={`flex items-center gap-1 text-xs ${getQualityColor(guest.connection_quality)}`}>
                <div className={`w-2 h-2 rounded-full ${guest.connection_quality === 'good' ? 'bg-current animate-pulse' : 'bg-current'}`} />
                <span>{guest.connection_quality || 'N/A'}</span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)] mb-2">
            <span className={`px-1.5 py-0.5 rounded border ${getStatusColor(guest.status)}`}>
              {getStatusLabel(guest.status)}
            </span>
            {guest.user?.email && (
              <>
                <span>•</span>
                <span>{guest.user.email}</span>
              </>
            )}
            {guest.joined_at && (
              <>
                <span>•</span>
                <span>{t('live.guest.joinedAt', 'Joined: {{time}}', { time: new Date(guest.joined_at).toLocaleTimeString() })}</span>
              </>
            )}
          </div>

          {/* Permissions */}
          {guest.status === 'active' && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {guest.permissions.can_speak && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[color:var(--color-surface-muted)] rounded text-xs text-[color:var(--color-text-muted)]">
                  <Mic className="w-3 h-3" />
                  {t('live.guest.canSpeak', 'Speak')}
                </span>
              )}
              {guest.permissions.can_share_video && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[color:var(--color-surface-muted)] rounded text-xs text-[color:var(--color-text-muted)]">
                  <Video className="w-3 h-3" />
                  {t('live.guest.canShareVideo', 'Video')}
                </span>
              )}
              {guest.permissions.can_share_screen && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[color:var(--color-surface-muted)] rounded text-xs text-[color:var(--color-text-muted)]">
                  <Monitor className="w-3 h-3" />
                  {t('live.guest.canShareScreen', 'Screen')}
                </span>
              )}
              {guest.permissions.can_control_stream && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[color:var(--color-surface-muted)] rounded text-xs text-[color:var(--color-text-muted)]">
                  <Shield className="w-3 h-3" />
                  {t('live.guest.canControl', 'Control')}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        {isHost && guest.user_id !== currentUserId && (
          <div className="flex items-center gap-1">
            {guest.invite_token && (
              <button
                onClick={() => handleCopyInviteLink(guest.invite_token!)}
                className="p-2 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded transition-colors"
                title={t('live.guest.copyInviteLink', 'Copy invite link')}
              >
                {copiedToken === guest.invite_token ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <LinkIcon className="w-4 h-4" />
                )}
              </button>
            )}
            <button
              onClick={() => handleRemoveGuest(guest.id)}
              className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
              title={t('live.guest.removeGuest', 'Remove guest')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-[color:var(--color-accent)]" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('live.guest.title', 'Guest Co-Hosts')}
          </h3>
          <span className="px-2 py-0.5 bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)] text-sm rounded-full">
            {activeGuests.length}/{guests.length}
          </span>
        </div>

        {isHost && (
          <button
            onClick={() => setShowInviteModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-[color:var(--color-accent)] hover:opacity-90 text-white rounded-lg transition-colors text-sm font-medium"
          >
            <UserPlus className="w-4 h-4" />
            {t('live.guest.inviteButton', 'Invite Guest')}
          </button>
        )}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
        <input
          type="text"
          placeholder={t('live.guest.searchPlaceholder', 'Search guests...')}
          className="w-full pl-9 pr-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Guests list */}
      <div className="space-y-3 max-h-[500px] overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[color:var(--color-accent)]" />
            <span className="ml-2 text-[color:var(--color-text-muted)]">
              {t('live.guest.loading', 'Loading guests...')}
            </span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-500 text-sm">
              {t('live.guest.error', 'Failed to load guests')}
            </p>
          </div>
        ) : filteredGuests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-[color:var(--color-text-muted)]">
            <Users className="w-8 h-8 mb-2" />
            <p className="text-sm font-medium">
              {search
                ? t('live.guest.noResults', 'No guests found')
                : t('live.guest.noGuests', 'No guests yet')}
            </p>
            <p className="text-xs mt-1">
              {t('live.guest.inviteHint', 'Click "Invite Guest" to add co-hosts')}
            </p>
          </div>
        ) : (
          <>
            {/* Active guests */}
            {activeGuests.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wide">
                  {t('live.guest.sectionActive', 'Active ({{count}})', { count: activeGuests.length })}
                </h4>
                {activeGuests.map((guest: GuestSession) => renderGuestItem(guest))}
              </div>
            )}

            {/* Pending guests */}
            {pendingGuests.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wide">
                  {t('live.guest.sectionPending', 'Pending ({{count}})', { count: pendingGuests.length })}
                </h4>
                {pendingGuests.map((guest: GuestSession) => renderGuestItem(guest))}
              </div>
            )}

            {/* Inactive guests */}
            {inactiveGuests.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wide">
                  {t('live.guest.sectionInactive', 'Inactive ({{count}})', { count: inactiveGuests.length })}
                </h4>
                {inactiveGuests.map((guest: GuestSession) => renderGuestItem(guest))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Invite modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-[color:var(--color-surface)] rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
                {t('live.guest.inviteTitle', 'Invite Guest Co-Host')}
              </h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="p-1 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                  {t('live.guest.emailLabel', 'Email Address')}
                  <span className="text-red-500 ml-1">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
                  <input
                    type="email"
                    placeholder="guest@example.com"
                    className="w-full pl-9 pr-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-[color:var(--color-text)] mb-1.5">
                  {t('live.guest.messageLabel', 'Invitation Message (Optional)')}
                </label>
                <textarea
                  placeholder={t('live.guest.messagePlaceholder', 'Add a personal message to your invitation...')}
                  className="w-full px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm resize-none"
                  rows={3}
                  value={inviteMessage}
                  onChange={(e) => setInviteMessage(e.target.value)}
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="px-4 py-2 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg transition-colors"
                >
                  {t('common.cancel', 'Cancel')}
                </button>
                <button
                  type="button"
                  onClick={handleInvite}
                  disabled={!inviteEmail.trim()}
                  className="px-4 py-2 bg-[color:var(--color-accent)] hover:opacity-90 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <UserPlus className="w-4 h-4" />
                  {t('live.guest.sendInvite', 'Send Invite')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default GuestManager;
