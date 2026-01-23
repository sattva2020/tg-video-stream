/**
 * A/B Testing Page
 * Feature: 016-a-b-testing-framework-for-content
 *
 * Страница A/B тестирования в админ-панели.
 * Отображает:
 * - Список A/B тестов
 * - Детали и результаты выбранного теста
 * - Мастер создания нового теста
 */

import React, { useState, useCallback, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  FlaskConical,
  Plus,
  RefreshCw,
  ArrowLeft,
} from 'lucide-react';
import { AppLayout } from '../../components/layout';
import { ABTestList } from '../../components/ab_testing/ABTestList';
import { ABTestResults } from '../../components/ab_testing/ABTestResults';
import { ABTestWizard } from '../../components/ab_testing/ABTestWizard';
import * as abTestingApi from '../../api/ab_testing';
import type {
  ABTestStatus,
  ABTestAnalysisResponse,
} from '../../types/ab_testing';

const statusOptions: { value: ABTestStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'draft', label: 'Черновики' },
  { value: 'running', label: 'Запущенные' },
  { value: 'paused', label: 'Приостановленные' },
  { value: 'completed', label: 'Завершённые' },
  { value: 'stopped', label: 'Остановленные' },
];

const ABTestingPage: React.FC = () => {
  const [selectedTestStatus, setSelectedTestStatus] = useState<ABTestStatus | 'all'>('all');
  const [selectedTestId, setSelectedTestId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<ABTestAnalysisResponse | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [listKey, setListKey] = useState(0);

  // Fetch analysis when test is selected
  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!selectedTestId) {
        setAnalysis(null);
        return;
      }

      setLoadingAnalysis(true);
      setAnalysisError(null);

      try {
        const data = await abTestingApi.analyzeABTest(selectedTestId);
        setAnalysis(data);
      } catch (err) {
        console.error('Failed to fetch analysis:', err);
        setAnalysisError('Не удалось загрузить результаты анализа');
      } finally {
        setLoadingAnalysis(false);
      }
    };

    fetchAnalysis();
  }, [selectedTestId]);

  // Auto-refresh analysis every 30 seconds when viewing a running test
  useEffect(() => {
    if (!selectedTestId || analysis?.status !== 'running') {
      return;
    }

    const interval = setInterval(() => {
      abTestingApi
        .analyzeABTest(selectedTestId)
        .then(setAnalysis)
        .catch((err) => console.error('Failed to refresh analysis:', err));
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedTestId, analysis?.status]);

  const handleTestClick = useCallback((testId: string) => {
    setSelectedTestId(testId);
  }, []);

  const handleBackToList = useCallback(() => {
    setSelectedTestId(null);
    setAnalysis(null);
  }, []);

  const handleCreateTest = useCallback((testId: string) => {
    setListKey((prev) => prev + 1);
    setSelectedTestId(testId);
  }, []);

  const handleStartTest = useCallback(() => {
    setListKey((prev) => prev + 1);
  }, []);

  const handleStopTest = useCallback(() => {
    setListKey((prev) => prev + 1);
  }, []);

  const handleDeleteTest = useCallback(() => {
    if (selectedTestId) {
      setSelectedTestId(null);
      setAnalysis(null);
    }
    setListKey((prev) => prev + 1);
  }, [selectedTestId]);

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
        >
          <div className="flex items-center gap-3">
            {selectedTestId && (
              <button
                onClick={handleBackToList}
                className="p-2 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)] transition-colors duration-300"
                title="Назад к списку"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <div>
              <h1 className="text-2xl font-bold text-[color:var(--color-text)]">
                {selectedTestId ? 'Результаты A/B теста' : 'A/B Тестирование'}
              </h1>
              <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                {selectedTestId
                  ? 'Детальный анализ и статистика'
                  : 'Создавайте и управляйте A/B тестами'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {!selectedTestId && (
              <>
                {/* Status Filter */}
                <div className="flex items-center gap-2 rounded-2xl p-1 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-sm shadow-black/5">
                  <FlaskConical className="w-4 h-4 text-[color:var(--color-text-muted)] ml-2" />
                  {statusOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() =>
                        setSelectedTestStatus(
                          option.value === 'all' ? 'all' : (option.value as ABTestStatus)
                        )
                      }
                      className={`
                        px-3 py-1.5 text-sm font-medium rounded-xl transition-colors duration-300
                        ${
                          selectedTestStatus === option.value
                            ? 'bg-[color:var(--color-accent)] text-white'
                            : 'text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)]'
                        }
                      `}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>

                {/* Create Test Button */}
                <button
                  onClick={() => setIsWizardOpen(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-2xl bg-[color:var(--color-accent)] text-white font-medium hover:bg-[color:var(--color-accent-hover)] transition-colors duration-300 shadow-lg shadow-black/10"
                >
                  <Plus className="w-4 h-4" />
                  <span className="hidden sm:inline">Создать тест</span>
                </button>
              </>
            )}

            {/* Refresh Button */}
            <button
              onClick={() => setListKey((prev) => prev + 1)}
              className="p-2 rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:bg-[color:var(--color-surface)] transition-colors duration-300"
              title="Обновить"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </motion.div>

        {/* Content */}
        {selectedTestId ? (
          /* Test Results View */
          <motion.div
            key={`results-${selectedTestId}`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            {/* Error State */}
            {analysisError && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-2xl p-4 bg-red-500/10 border border-red-500/20 text-red-300 mb-6"
              >
                {analysisError}
              </motion.div>
            )}

            {/* Results */}
            {analysis ? (
              <ABTestResults analysis={analysis} loading={loadingAnalysis} />
            ) : loadingAnalysis ? (
              <div className="rounded-2xl p-12 bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] animate-pulse">
                <div className="h-64 bg-[color:var(--color-surface-muted)] rounded-xl" />
              </div>
            ) : null}
          </motion.div>
        ) : (
          /* Test List View */
          <motion.div
            key={`list-${listKey}`}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3 }}
          >
            <ABTestList
              status={selectedTestStatus === 'all' ? undefined : selectedTestStatus}
              limit={50}
              refreshInterval={30000}
              onTestClick={handleTestClick}
              onStartTest={handleStartTest}
              onStopTest={handleStopTest}
              onDeleteTest={handleDeleteTest}
            />
          </motion.div>
        )}

        {/* Create Test Wizard */}
        <ABTestWizard
          open={isWizardOpen}
          onOpenChange={setIsWizardOpen}
          channelId="default"
          onSuccess={handleCreateTest}
        />
      </div>
    </AppLayout>
  );
};

export default ABTestingPage;
