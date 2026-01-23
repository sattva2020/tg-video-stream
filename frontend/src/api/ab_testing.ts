/**
 * A/B Testing API Client
 * Feature: 016-a-b-testing-framework-for-content
 *
 * Клиент для работы с эндпоинтами A/B тестирования.
 */

import { client } from './client';
import type {
  ABTestCreate,
  ABTestUpdate,
  ABTestResponse,
  ABTestCollectionResponse,
  ABTestMetricCreate,
  ABTestMetricResponse,
  ABTestStartResponse,
  ABTestStopResponse,
  ABTestAnalysisResponse,
} from '../types/ab_testing';

/**
 * Создать A/B тест.
 *
 * @param testData - Данные для создания теста
 * @returns Созданный A/B тест
 */
export async function createABTest(testData: ABTestCreate): Promise<ABTestResponse> {
  const response = await client.post<ABTestResponse>('/api/ab-tests', testData);
  return response.data;
}

/**
 * Получить список A/B тестов.
 *
 * @param channelId - Фильтр по ID канала
 * @param status - Фильтр по статусу
 * @param limit - Максимальное количество результатов (1-100)
 * @param offset - Смещение для пагинации
 * @returns Список A/B тестов
 */
export async function listABTests(
  channelId?: string,
  status?: string,
  limit: number = 50,
  offset: number = 0
): Promise<ABTestCollectionResponse> {
  const response = await client.get<ABTestCollectionResponse>('/api/ab-tests', {
    params: { channel_id: channelId, status, limit, offset },
  });
  return response.data;
}

/**
 * Получить A/B тест по ID.
 *
 * @param testId - ID теста
 * @returns A/B тест с вариантами
 */
export async function getABTest(testId: string): Promise<ABTestResponse> {
  const response = await client.get<ABTestResponse>(`/api/ab-tests/${testId}`);
  return response.data;
}

/**
 * Обновить A/B тест.
 *
 * @param testId - ID теста
 * @param testData - Данные для обновления
 * @returns Обновленный A/B тест
 */
export async function updateABTest(
  testId: string,
  testData: ABTestUpdate
): Promise<ABTestResponse> {
  const response = await client.patch<ABTestResponse>(`/api/ab-tests/${testId}`, testData);
  return response.data;
}

/**
 * Удалить A/B тест.
 *
 * @param testId - ID теста
 * @returns Результат удаления
 */
export async function deleteABTest(testId: string): Promise<{ success: boolean; message: string }> {
  const response = await client.delete<{ success: boolean; message: string }>(
    `/api/ab-tests/${testId}`
  );
  return response.data;
}

/**
 * Запустить A/B тест.
 *
 * @param testId - ID теста
 * @returns Результат запуска
 */
export async function startABTest(testId: string): Promise<ABTestStartResponse> {
  const response = await client.post<ABTestStartResponse>(`/api/ab-tests/${testId}/start`);
  return response.data;
}

/**
 * Остановить A/B тест.
 *
 * @param testId - ID теста
 * @param selectWinner - Автоматически выбрать победителя
 * @param winnerVariantId - ID варианта-победителя (ручной выбор)
 * @returns Результат остановки
 */
export async function stopABTest(
  testId: string,
  selectWinner: boolean = true,
  winnerVariantId?: string
): Promise<ABTestStopResponse> {
  const response = await client.post<ABTestStopResponse>(`/api/ab-tests/${testId}/stop`, null, {
    params: { select_winner: selectWinner, winner_variant_id: winnerVariantId },
  });
  return response.data;
}

/**
 * Получить статистический анализ A/B теста.
 *
 * @param testId - ID теста
 * @param confidenceLevel - Уровень доверия (0.5-0.99)
 * @returns Результаты анализа
 */
export async function analyzeABTest(
  testId: string,
  confidenceLevel: number = 0.95
): Promise<ABTestAnalysisResponse> {
  const response = await client.get<ABTestAnalysisResponse>(
    `/api/ab-tests/${testId}/analysis`,
    {
      params: { confidence_level: confidenceLevel },
    }
  );
  return response.data;
}

/**
 * Записать метрику для варианта A/B теста.
 *
 * @param metricData - Данные метрики
 * @returns Записанная метрика
 */
export async function recordABTestMetric(
  metricData: ABTestMetricCreate
): Promise<ABTestMetricResponse> {
  const response = await client.post<ABTestMetricResponse>(
    '/api/ab-tests/metrics',
    metricData
  );
  return response.data;
}
