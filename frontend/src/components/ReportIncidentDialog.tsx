/**
 * ReportIncidentDialog - диалог для создания обращения в поддержку
 * 
 * Автоматически прикрепляет собранные логи и информацию о браузере.
 * Позволяет добавить описание и скриншот.
 */

import React, { useState, useCallback, useRef } from 'react';
import type { LogEntry, BrowserInfo, CreateIncidentResponse, SimilarIncident } from '../types/incident';
import { useTranslation } from 'react-i18next';

interface ReportIncidentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  browserInfo: BrowserInfo;
  lastError: LogEntry | null;
}

export function ReportIncidentDialog({
  isOpen,
  onClose,
  logs,
  browserInfo,
  lastError,
}: ReportIncidentDialogProps) {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [screenshot, setScreenshot] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<CreateIncidentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Предзаполнение из последней ошибки
  React.useEffect(() => {
    if (isOpen && lastError && !title) {
      if (lastError.type === 'console') {
        setTitle(`Ошибка: ${lastError.message.slice(0, 100)}`);
      } else if (lastError.type === 'network') {
        setTitle(`Ошибка сети: ${lastError.method} ${lastError.url.slice(0, 50)}`);
      }
    }
  }, [isOpen, lastError, title]);

  // Сброс при закрытии
  const handleClose = useCallback(() => {
    setTitle('');
    setDescription('');
    setScreenshot(null);
    setResult(null);
    setError(null);
    setShowLogs(false);
    onClose();
  }, [onClose]);

  // Загрузка скриншота
  const handleScreenshotUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Пожалуйста, выберите изображение');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('Размер файла не должен превышать 5 МБ');
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      setScreenshot(reader.result as string);
      setError(null);
    };
    reader.readAsDataURL(file);
  }, []);

  // Отправка инцидента
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!title.trim()) {
      setError('Укажите заголовок проблемы');
      return;
    }

    if (!description.trim()) {
      setError('Опишите проблему подробнее');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/incidents', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          logs,
          browserInfo,
          pageUrl: window.location.href,
          screenshot: screenshot || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Не удалось создать обращение');
      }

      const data: CreateIncidentResponse = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setIsSubmitting(false);
    }
  }, [title, description, logs, browserInfo, screenshot]);

  if (!isOpen) return null;

  // Подсчёт ошибок в логах
  const errorCount = logs.filter(log => 
    (log.type === 'console' && log.level === 'error') ||
    (log.type === 'network' && log.statusCode && log.statusCode >= 400)
  ).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Заголовок */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {result ? '✅ Обращение создано' : '🐛 Сообщить о проблеме'}
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Закрыть"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Контент */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {result ? (
            // Результат успешного создания
            <div className="space-y-4">
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <p className="text-green-800 dark:text-green-200">
                  Ваше обращение #{result.id.slice(0, 8)} успешно создано!
                </p>
              </div>

              {/* AI-предложение */}
              {result.aiSuggestedSolution && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <h3 className="font-medium text-blue-800 dark:text-blue-200 mb-2">
                    💡 Возможное решение
                  </h3>
                  <p className="text-blue-700 dark:text-blue-300 whitespace-pre-wrap">
                    {result.aiSuggestedSolution}
                  </p>
                </div>
              )}

              {/* Похожие инциденты */}
              {result.similarIncidents && result.similarIncidents.length > 0 && (
                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                  <h3 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                    📋 Похожие обращения
                  </h3>
                  <ul className="space-y-2">
                    {result.similarIncidents.map((incident: SimilarIncident) => (
                      <li key={incident.id} className="text-yellow-700 dark:text-yellow-300">
                        <span className="font-medium">{incident.title}</span>
                        {incident.solution && (
                          <p className="text-sm mt-1 text-yellow-600 dark:text-yellow-400">
                            Решение: {incident.solution}
                          </p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Мы рассмотрим ваше обращение в ближайшее время. 
                Вы получите уведомление о статусе.
              </p>
            </div>
          ) : (
            // Форма создания
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Ошибка */}
              {error && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                  <p className="text-red-700 dark:text-red-300 text-sm">{error}</p>
                </div>
              )}

              {/* Заголовок */}
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Заголовок проблемы *
                </label>
                <input
                  type="text"
                  id="title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Кратко опишите проблему"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  maxLength={200}
                  required
                />
              </div>

              {/* Описание */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Подробное описание *
                </label>
                <textarea
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Опишите шаги для воспроизведения проблемы, что вы ожидали увидеть и что произошло на самом деле"
                  rows={5}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg 
                           bg-white dark:bg-gray-700 text-gray-900 dark:text-white
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  required
                />
              </div>

              {/* Скриншот */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Скриншот (опционально)
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                             text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700
                             transition-colors text-sm"
                  >
                    📷 Загрузить скриншот
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleScreenshotUpload}
                    className="hidden"
                  />
                  {screenshot && (
                    <div className="flex items-center gap-2">
                      <img src={screenshot} alt="Screenshot" className="h-10 w-10 object-cover rounded" />
                      <button
                        type="button"
                        onClick={() => setScreenshot(null)}
                        className="text-red-500 hover:text-red-700 text-sm"
                      >
                        Удалить
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Информация о собранных данных */}
              <div className="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    📊 Автоматически собранные данные
                  </h4>
                  <button
                    type="button"
                    onClick={() => setShowLogs(!showLogs)}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    {showLogs ? 'Скрыть' : 'Показать'}
                  </button>
                </div>
                
                <div className="flex flex-wrap gap-2 text-xs">
                  <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded">
                    🌐 {browserInfo.name} {browserInfo.version}
                  </span>
                  <span className="px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                    💻 {browserInfo.os}
                  </span>
                  <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">
                    📋 {logs.length} логов
                  </span>
                  {errorCount > 0 && (
                    <span className="px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded">
                      ⚠️ {errorCount} ошибок
                    </span>
                  )}
                </div>

                {showLogs && (
                  <div className="mt-3 max-h-40 overflow-y-auto bg-gray-900 rounded p-2 text-xs font-mono text-gray-300">
                    {logs.slice(-20).map((log, i) => (
                      <div key={i} className={`py-0.5 ${
                        log.type === 'console' && log.level === 'error' ? 'text-red-400' :
                        log.type === 'console' && log.level === 'warn' ? 'text-yellow-400' :
                        log.type === 'network' ? 'text-blue-400' :
                        log.type === 'action' ? 'text-green-400' :
                        'text-gray-400'
                      }`}>
                        [{log.type}] {
                          log.type === 'console' ? log.message.slice(0, 100) :
                          log.type === 'network' ? `${log.method} ${log.url} ${log.statusCode || log.error}` :
                          log.type === 'action' ? `${log.action} ${log.element || ''}` :
                          log.type === 'performance' ? `${log.metric}: ${log.value}ms` :
                          ''
                        }
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Кнопки */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 
                           dark:hover:bg-gray-700 rounded-lg transition-colors"
                  disabled={isSubmitting}
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg
                           transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Отправка...
                    </>
                  ) : (
                    '📤 Отправить'
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

export default ReportIncidentDialog;
