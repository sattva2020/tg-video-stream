import React from 'react'
import { useTranslation } from 'react-i18next'
import PlaylistQueue from '../components/PlaylistQueue'
import AddTrackForm from '../components/AddTrackForm'
import { ResponsiveHeader } from '../components/layout'

const PlaylistPage: React.FC = () => {
  const { t } = useTranslation()
  
  return (
    <div className="min-h-screen bg-[color:var(--color-surface)]">
      <ResponsiveHeader />
      
      <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <h1 className="text-xl sm:text-2xl font-bold mb-4 sm:mb-6 text-[color:var(--color-text)]">
          {t('playlist.title', 'Плейлист')}
        </h1>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
          <div>
            <AddTrackForm onAdded={() => { /* PlaylistQueue will pick up via WebSocket/polling */ }} />
          </div>
          <div>
            <PlaylistQueue />
          </div>
        </div>
      </div>
    </div>
  )
}

export default PlaylistPage
