/**
 * TopTracksTable Component
 * Feature: 021-admin-analytics-menu
 * 
 * Таблица топ треков за период.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Music, Clock, Play } from 'lucide-react';
import type { TopTrackItem } from '../../types/analytics';

interface TopTracksTableProps {
  tracks: TopTrackItem[];
  loading?: boolean;
}

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  if (hours > 0) {
    return `${hours}ч ${minutes}м`;
  }
  return `${minutes}м`;
};

export const TopTracksTable: React.FC<TopTracksTableProps> = ({
  tracks,
  loading = false,
}) => {
  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-violet-500/10 rounded-xl">
            <Music className="w-5 h-5 text-violet-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Топ треков
          </h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
          ))}
        </div>
      </motion.div>
    );
  }

  if (!tracks.length) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-violet-500/10 rounded-xl">
            <Music className="w-5 h-5 text-violet-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            Топ треков
          </h3>
        </div>
        <div className="h-48 flex items-center justify-center text-gray-500">
          Нет данных за выбранный период
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800/50 rounded-2xl p-6 border border-gray-200 dark:border-gray-700 shadow-lg"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-violet-500/10 rounded-xl">
          <Music className="w-5 h-5 text-violet-500" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Топ треков
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="pb-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                #
              </th>
              <th className="pb-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Трек
              </th>
              <th className="pb-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div className="flex items-center justify-end gap-1">
                  <Play className="w-3 h-3" />
                  Воспроизв.
                </div>
              </th>
              <th className="pb-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                <div className="flex items-center justify-end gap-1">
                  <Clock className="w-3 h-3" />
                  Время
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700/50">
            {tracks.map((track, index) => (
              <motion.tr
                key={track.track_id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
              >
                <td className="py-3 text-sm font-medium text-gray-500 dark:text-gray-400">
                  {index + 1}
                </td>
                <td className="py-3">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-xs">
                      {track.title}
                    </span>
                    {track.artist && (
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {track.artist}
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-3 text-right">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-400">
                    {track.play_count}
                  </span>
                </td>
                <td className="py-3 text-right text-sm text-gray-500 dark:text-gray-400">
                  {formatDuration(track.total_duration_seconds)}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default TopTracksTable;
