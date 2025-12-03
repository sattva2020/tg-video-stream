import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { telegramApi, TelegramDialog } from '../../api/telegram';
import { Users, Radio, Loader2, Search, Check, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface DialogPickerProps {
  accountId: string;
  onSelect: (dialog: TelegramDialog) => void;
  onCancel: () => void;
}

export const DialogPicker: React.FC<DialogPickerProps> = ({
  accountId,
  onSelect,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState<'all' | 'channels' | 'groups'>('all');
  
  const { data: dialogs = [], isLoading, error } = useQuery({
    queryKey: ['telegram', 'dialogs', accountId, filter],
    queryFn: () => telegramApi.getDialogs(accountId, filter),
    staleTime: 30 * 1000, // 30 секунд
    retry: 1,
  });
  
  // Фильтрация по поиску
  const filteredDialogs = dialogs.filter(dialog => 
    dialog.title.toLowerCase().includes(search.toLowerCase()) ||
    (dialog.username && dialog.username.toLowerCase().includes(search.toLowerCase()))
  );
  
  const getTypeIcon = (type: string) => {
    if (type === 'channel') {
      return <Radio className="w-4 h-4 text-blue-500" />;
    }
    return <Users className="w-4 h-4 text-green-500" />;
  };
  
  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'channel':
        return t('dialogs.typeChannel', 'Канал');
      case 'supergroup':
        return t('dialogs.typeSupergroup', 'Супергруппа');
      case 'group':
        return t('dialogs.typeGroup', 'Группа');
      default:
        return type;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Поиск */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
          <input
            type="text"
            placeholder={t('dialogs.searchPlaceholder', 'Поиск по названию...')}
            className="w-full pl-9 pr-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        
        {/* Фильтр по типу */}
        <select
          title={t('dialogs.filterType', 'Тип')}
          className="px-3 py-2 border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-[color:var(--color-text)] rounded-lg text-sm"
          value={filter}
          onChange={(e) => setFilter(e.target.value as 'all' | 'channels' | 'groups')}
        >
          <option value="all">{t('dialogs.filterAll', 'Все')}</option>
          <option value="channels">{t('dialogs.filterChannels', 'Каналы')}</option>
          <option value="groups">{t('dialogs.filterGroups', 'Группы')}</option>
        </select>
      </div>
      
      {/* Список диалогов */}
      <div className="max-h-[300px] overflow-y-auto border border-[color:var(--color-border)] rounded-lg">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-[color:var(--color-accent)]" />
            <span className="ml-2 text-[color:var(--color-text-muted)]">
              {t('dialogs.loading', 'Загрузка каналов и групп...')}
            </span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
            <AlertCircle className="w-8 h-8 text-red-500 mb-2" />
            <p className="text-red-500 text-sm">
              {t('dialogs.error', 'Не удалось загрузить список')}
            </p>
            <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
              {(error as Error).message}
            </p>
          </div>
        ) : filteredDialogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-[color:var(--color-text-muted)]">
            <Radio className="w-8 h-8 mb-2" />
            <p className="text-sm">
              {search 
                ? t('dialogs.noResults', 'Ничего не найдено')
                : t('dialogs.noDialogs', 'Нет доступных каналов или групп')
              }
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[color:var(--color-border)]">
            {filteredDialogs.map((dialog) => (
              <button
                key={dialog.id}
                onClick={() => onSelect(dialog)}
                className="w-full flex items-center gap-3 p-3 hover:bg-[color:var(--color-surface-muted)] transition-colors text-left"
              >
                {/* Иконка типа */}
                <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[color:var(--color-surface-muted)] flex items-center justify-center">
                  {getTypeIcon(dialog.type)}
                </div>
                
                {/* Информация */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-[color:var(--color-text)] truncate">
                      {dialog.title}
                    </span>
                    {dialog.is_admin && (
                      <span className="flex-shrink-0 px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-xs rounded">
                        {dialog.is_creator ? t('dialogs.owner', 'Владелец') : t('dialogs.admin', 'Админ')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
                    <span>{getTypeLabel(dialog.type)}</span>
                    {dialog.username && (
                      <>
                        <span>•</span>
                        <span>@{dialog.username}</span>
                      </>
                    )}
                    {dialog.members_count && (
                      <>
                        <span>•</span>
                        <span>{dialog.members_count.toLocaleString()} {t('dialogs.members', 'участников')}</span>
                      </>
                    )}
                  </div>
                  <div className="text-xs text-[color:var(--color-text-muted)] font-mono mt-0.5">
                    ID: {dialog.id}
                  </div>
                </div>
                
                {/* Иконка выбора */}
                <Check className="w-5 h-5 text-[color:var(--color-accent)] opacity-0 group-hover:opacity-100" />
              </button>
            ))}
          </div>
        )}
      </div>
      
      {/* Кнопки */}
      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] rounded-lg transition-colors"
        >
          {t('common.cancel', 'Отмена')}
        </button>
      </div>
    </div>
  );
};

export default DialogPicker;
