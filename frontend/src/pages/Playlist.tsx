import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Select, SelectItem } from '@heroui/react'
import { ResponsiveHeader } from '../components/layout'
import { PlaylistManager } from '../components/schedule/PlaylistManager'
import { useChannels } from '../hooks/useChannelsQuery'

const PlaylistPage: React.FC = () => {
  const { t } = useTranslation()
  const { data: channels = [], isLoading: channelsLoading } = useChannels()
  const [selectedChannelId, setSelectedChannelId] = useState<string>('')

  // Auto-select first channel
  useEffect(() => {
    if (channels.length > 0 && !selectedChannelId) {
      setSelectedChannelId(channels[0].id)
    }
  }, [channels, selectedChannelId])
  
  return (
    <div className="min-h-screen bg-[color:var(--color-surface)]">
      <ResponsiveHeader />
      
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h1 className="text-xl sm:text-2xl font-bold text-[color:var(--color-text)]">
            {t('playlist.title', 'Плейлисты')}
          </h1>
          
          {/* Channel selector */}
          {channels.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-default-600 whitespace-nowrap">
                {t('playlist.channel', 'Канал')}:
              </span>
              <Select
                size="sm"
                aria-label={t('playlist.selectChannel', 'Выберите канал')}
                selectedKeys={selectedChannelId ? [selectedChannelId] : []}
                onChange={(e) => setSelectedChannelId(e.target.value)}
                className="w-48"
                isLoading={channelsLoading}
                popoverProps={{
                  classNames: {
                    content: "bg-white dark:bg-gray-900 border border-default-200 dark:border-gray-700",
                  },
                }}
              >
                {channels.map((channel) => (
                  <SelectItem key={channel.id}>
                    {channel.name}
                  </SelectItem>
                ))}
              </Select>
            </div>
          )}
        </div>
        
        {/* Playlist Manager (unified component) */}
        <PlaylistManager channelId={selectedChannelId} />
      </div>
    </div>
  )
}

export default PlaylistPage
