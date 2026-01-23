/**
 * Playlist Screen
 *
 * Mobile-optimized playlist management screen.
 * Follows patterns from frontend/src/pages/Playlist.tsx
 *
 * Features:
 * - List of playlists with item counts and durations
 * - Channel selector for playing playlists
 * - Expandable playlist details to show tracks
 * - Play and delete operations
 * - Pull-to-refresh support
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useFocusEffect } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';

// API
import { playlistsApi, Playlist, PlaylistEntry } from '../api/playlists';
import { channelsApi, StreamingChannel } from '../api/channels';

// Types
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../navigation/types';

type PlaylistScreenProps = NativeStackScreenProps<RootStackParamList, 'Playlist'>;

// Format duration to human-readable string
function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m`;
}

// Format track duration to MM:SS
function formatTrackDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

// Playlist Card Component
interface PlaylistCardProps {
  playlist: Playlist;
  isExpanded: boolean;
  onPress: () => void;
  onPlay: () => void;
  onDelete: () => void;
}

const PlaylistCard: React.FC<PlaylistCardProps> = ({
  playlist,
  isExpanded,
  onPress,
  onPlay,
  onDelete,
}) => {
  const { t } = useTranslation();

  // Get source icon
  const getSourceIcon = (sourceType?: string) => {
    switch (sourceType) {
      case 'youtube':
        return 'logo-youtube';
      case 'm3u':
        return 'document-text';
      case 'gdrive_folder':
        return 'folder-open';
      case 'folder':
      case 'local':
        return 'folder';
      case 'url':
        return 'globe';
      case 'manual':
      default:
        return 'musical-notes';
    }
  };

  return (
    <TouchableOpacity
      style={[styles.playlistCard, isExpanded && styles.playlistCardExpanded]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={styles.playlistHeader}>
        <View style={styles.playlistInfo}>
          <View
            style={[
              styles.playlistIcon,
              { backgroundColor: playlist.color || '#8B5CF6' },
            ]}
          >
            <Ionicons
              name={getSourceIcon(playlist.source_type) as any}
              size={24}
              color="#FFFFFF"
            />
          </View>
          <View style={styles.playlistDetails}>
            <Text style={styles.playlistName}>{playlist.name}</Text>
            <View style={styles.playlistMeta}>
              <Text style={styles.playlistMetaText}>
                {t('playlist.items', '{count} items').replace('{count}', String(playlist.items_count))}
              </Text>
              <Text style={styles.playlistMetaText}>•</Text>
              <Text style={styles.playlistMetaText}>
                {formatDuration(playlist.total_duration)}
              </Text>
              {playlist.is_public && (
                <>
                  <Text style={styles.playlistMetaText}>•</Text>
                  <Ionicons name="globe" size={14} color="#6B7280" />
                </>
              )}
            </View>
          </View>
        </View>
        <Ionicons
          name={isExpanded ? 'chevron-up' : 'chevron-down'}
          size={20}
          color="#9CA3AF"
        />
      </View>

      {isExpanded && (
        <View style={styles.playlistExpanded}>
          {/* Description */}
          {playlist.description && (
            <Text style={styles.playlistDescription}>{playlist.description}</Text>
          )}

          {/* Tracks */}
          <View style={styles.tracksSection}>
            <Text style={styles.tracksTitle}>
              {t('playlist.tracks', 'Tracks')} ({playlist.items.length})
            </Text>
            {playlist.items.length === 0 ? (
              <Text style={styles.noTracksText}>
                {t('playlist.noTracks', 'No tracks in this playlist')}
              </Text>
            ) : (
              playlist.items.map((item: PlaylistEntry, index: number) => (
                <View key={index} style={styles.trackItem}>
                  <Text style={styles.trackNumber}>{index + 1}</Text>
                  <View style={styles.trackInfo}>
                    <Text style={styles.trackTitle} numberOfLines={1}>
                      {item.title}
                    </Text>
                    <Text style={styles.trackMeta}>
                      {item.type} • {formatTrackDuration(item.duration)}
                    </Text>
                  </View>
                </View>
              ))
            )}
          </View>

          {/* Actions */}
          <View style={styles.playlistActions}>
            <TouchableOpacity
              style={[styles.actionButton, styles.playButton]}
              onPress={onPlay}
            >
              <Ionicons name="play" size={20} color="#FFFFFF" />
              <Text style={styles.playButtonText}>
                {t('playlist.play', 'Play')}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.actionButton, styles.deleteButton]}
              onPress={onDelete}
            >
              <Ionicons name="trash-outline" size={20} color="#EF4444" />
              <Text style={styles.deleteButtonText}>
                {t('common.delete', 'Delete')}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </TouchableOpacity>
  );
};

// Main Screen Component
const PlaylistScreen: React.FC<PlaylistScreenProps> = ({ navigation }) => {
  const { t } = useTranslation();

  // State
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [channels, setChannels] = useState<StreamingChannel[]>([]);
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedPlaylistId, setExpandedPlaylistId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Fetch playlists
  const fetchPlaylists = useCallback(async () => {
    try {
      const data = await playlistsApi.getMyPlaylists();
      setPlaylists(data);
    } catch (error) {
      console.error('Failed to fetch playlists:', error);
      Alert.alert(
        t('errors.error', 'Error'),
        t('errors.networkError', 'Failed to load playlists')
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  // Fetch channels
  const fetchChannels = useCallback(async () => {
    try {
      const data = await channelsApi.list();
      setChannels(data);
      // Auto-select first channel if none selected
      if (data.length > 0 && !selectedChannelId) {
        setSelectedChannelId(data[0].id);
      }
    } catch (error) {
      console.error('Failed to fetch channels:', error);
    }
  }, [selectedChannelId]);

  // Initial load and refresh on focus
  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fetchPlaylists();
      fetchChannels();
    }, [fetchPlaylists, fetchChannels])
  );

  // Handle refresh
  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    fetchPlaylists();
    fetchChannels();
  }, [fetchPlaylists, fetchChannels]);

  // Handle playlist expand/collapse
  const handleTogglePlaylist = useCallback((playlistId: string) => {
    setExpandedPlaylistId(prev => (prev === playlistId ? null : playlistId));
  }, []);

  // Handle play playlist
  const handlePlayPlaylist = useCallback(
    async (playlistId: string, playlistName: string) => {
      if (!selectedChannelId) {
        Alert.alert(
          t('errors.error', 'Error'),
          t('playlist.selectPlaylist', 'Please select a channel first')
        );
        return;
      }

      setActionLoading(playlistId);
      try {
        await playlistsApi.playPlaylist(playlistId, selectedChannelId);
        Alert.alert(
          t('common.success', 'Success'),
          t('audio.queue.upNext', 'Playing: {{name}}').replace('{{name}}', playlistName)
        );
        setExpandedPlaylistId(null);
      } catch (error) {
        console.error('Failed to play playlist:', error);
        Alert.alert(
          t('errors.error', 'Error'),
          t('errors.somethingWentWrong', 'Failed to play playlist')
        );
      } finally {
        setActionLoading(null);
      }
    },
    [selectedChannelId, t]
  );

  // Handle delete playlist
  const handleDeletePlaylist = useCallback(
    async (playlistId: string, playlistName: string) => {
      Alert.alert(
        t('playlist.confirmDelete', 'Delete Playlist?'),
        t('playlist.confirmDeleteMessage', 'Are you sure you want to delete "{{name}}"?').replace(
          '{{name}}',
          playlistName
        ),
        [
          {
            text: t('common.cancel', 'Cancel'),
            style: 'cancel',
          },
          {
            text: t('common.delete', 'Delete'),
            style: 'destructive',
            onPress: async () => {
              setActionLoading(playlistId);
              try {
                await playlistsApi.deletePlaylist(playlistId);
                Alert.alert(
                  t('common.success', 'Success'),
                  t('playlist.playlistDeleted', 'Playlist deleted')
                );
                // Refresh the list
                await fetchPlaylists();
              } catch (error) {
                console.error('Failed to delete playlist:', error);
                Alert.alert(
                  t('errors.error', 'Error'),
                  t('errors.somethingWentWrong', 'Failed to delete playlist')
                );
              } finally {
                setActionLoading(null);
              }
            },
          },
        ]
      );
    },
    [fetchPlaylists, t]
  );

  // Render channel selector
  const renderChannelSelector = () => {
    if (channels.length === 0) return null;

    return (
      <View style={styles.channelSelector}>
        <Text style={styles.channelSelectorLabel}>
          {t('audio.channel.select', 'Channel')}:
        </Text>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.channelList}
          contentContainerStyle={styles.channelListContent}
        >
          {channels.map((channel) => (
            <TouchableOpacity
              key={channel.id}
              style={[
                styles.channelChip,
                selectedChannelId === channel.id && styles.channelChipSelected,
              ]}
              onPress={() => setSelectedChannelId(channel.id)}
            >
              <Text
                style={[
                  styles.channelChipText,
                  selectedChannelId === channel.id && styles.channelChipTextSelected,
                ]}
              >
                {channel.name}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>
    );
  };

  // Render loading state
  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#8B5CF6" />
        <Text style={styles.loadingText}>{t('common.loading', 'Loading...')}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>{t('nav.myPlaylists', 'My Playlists')}</Text>
      </View>

      {/* Channel Selector */}
      {renderChannelSelector()}

      {/* Playlist List */}
      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentContainer}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
      >
        {playlists.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="musical-notes-outline" size={64} color="#9CA3AF" />
            <Text style={styles.emptyTitle}>
              {t('playlist.noPlaylists', 'No playlists yet')}
            </Text>
            <Text style={styles.emptyMessage}>
              {t('playlist.createFirstPlaylist', 'Create your first playlist to get started')}
            </Text>
          </View>
        ) : (
          playlists.map((playlist) => (
            <PlaylistCard
              key={playlist.id}
              playlist={playlist}
              isExpanded={expandedPlaylistId === playlist.id}
              onPress={() => handleTogglePlaylist(playlist.id)}
              onPlay={() =>
                handlePlayPlaylist(playlist.id, playlist.name)
              }
              onDelete={() =>
                handleDeletePlaylist(playlist.id, playlist.name)
              }
            />
          ))
        )}
      </ScrollView>

      {/* Action loading indicator */}
      {actionLoading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator size="large" color="#FFFFFF" />
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6B7280',
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: '#111827',
  },
  channelSelector: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  channelSelectorLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
    marginBottom: 8,
  },
  channelList: {
    flexDirection: 'row',
  },
  channelListContent: {
    paddingRight: 20,
  },
  channelChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#F3F4F6',
    marginRight: 8,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  channelChipSelected: {
    backgroundColor: '#8B5CF6',
    borderColor: '#8B5CF6',
  },
  channelChipText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  channelChipTextSelected: {
    color: '#FFFFFF',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
  },
  playlistCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    marginBottom: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  playlistCardExpanded: {
    borderColor: '#8B5CF6',
  },
  playlistHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  playlistInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  playlistIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  playlistDetails: {
    flex: 1,
  },
  playlistName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  playlistMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  playlistMetaText: {
    fontSize: 13,
    color: '#6B7280',
  },
  playlistExpanded: {
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    padding: 16,
  },
  playlistDescription: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 16,
    fontStyle: 'italic',
  },
  tracksSection: {
    marginBottom: 16,
  },
  tracksTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  noTracksText: {
    fontSize: 14,
    color: '#9CA3AF',
    fontStyle: 'italic',
  },
  trackItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  trackNumber: {
    fontSize: 14,
    fontWeight: '600',
    color: '#9CA3AF',
    width: 32,
  },
  trackInfo: {
    flex: 1,
  },
  trackTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#111827',
    marginBottom: 2,
  },
  trackMeta: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  playlistActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 8,
  },
  playButton: {
    backgroundColor: '#8B5CF6',
  },
  playButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  deleteButton: {
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  deleteButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#EF4444',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 64,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#374151',
    marginTop: 16,
  },
  emptyMessage: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 8,
    textAlign: 'center',
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default PlaylistScreen;
