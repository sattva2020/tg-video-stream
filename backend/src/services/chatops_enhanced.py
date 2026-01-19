"""
ChatOps Enhanced - Расширенный ChatOps бот с AI возможностями.

Новые функции:
1. /dashboard - Генерация Grafana дашбордов по запросу
2. /rag [query] - RAG-поиск по историческим логам с LLM контекстом  
3. /predict [metric] [hours] - Предиктивный анализ ресурсов
4. Автоматические аннотации в Grafana при аномалиях

Автор: Jarvis
Дата: 2026-01-03
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import json
import hashlib
import re

import httpx
import numpy as np
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from prometheus_api_client import PrometheusConnect

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
LOKI_URL = os.getenv('LOKI_URL', 'http://loki:3100')
GRAFANA_URL = os.getenv('GRAFANA_URL', 'http://grafana:3000')
GRAFANA_API_KEY = os.getenv('GRAFANA_API_KEY', '')
GRAFANA_EXTERNAL_URL = os.getenv('GRAFANA_EXTERNAL_URL', 'https://grafana.sattva-streamer.top')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')
ALLOWED_USERS = os.getenv('ALLOWED_USERS', '').split(',')


# ============================================================================
# 1. GRAFANA DASHBOARD GENERATOR
# ============================================================================

class GrafanaDashboardGenerator:
    """Генератор дашбордов Grafana через AI."""
    
    # Шаблоны панелей
    PANEL_TEMPLATES = {
        'cpu': {
            'title': 'CPU Usage',
            'expr': '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'unit': 'percent',
            'thresholds': [{'value': 80, 'color': 'yellow'}, {'value': 95, 'color': 'red'}]
        },
        'memory': {
            'title': 'Memory Usage',
            'expr': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
            'unit': 'percent',
            'thresholds': [{'value': 80, 'color': 'yellow'}, {'value': 95, 'color': 'red'}]
        },
        'disk': {
            'title': 'Disk Usage',
            'expr': '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
            'unit': 'percent',
            'thresholds': [{'value': 80, 'color': 'yellow'}, {'value': 95, 'color': 'red'}]
        },
        'network_rx': {
            'title': 'Network Receive',
            'expr': 'sum(rate(node_network_receive_bytes_total[5m]))',
            'unit': 'Bps',
            'thresholds': []
        },
        'network_tx': {
            'title': 'Network Transmit',
            'expr': 'sum(rate(node_network_transmit_bytes_total[5m]))',
            'unit': 'Bps',
            'thresholds': []
        },
        'http_requests': {
            'title': 'HTTP Requests Rate',
            'expr': 'sum(rate(http_requests_total[5m]))',
            'unit': 'reqps',
            'thresholds': []
        },
        'http_latency': {
            'title': 'HTTP Latency P95',
            'expr': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            'unit': 's',
            'thresholds': [{'value': 0.5, 'color': 'yellow'}, {'value': 1, 'color': 'red'}]
        },
        'http_errors': {
            'title': 'HTTP Errors Rate',
            'expr': 'sum(rate(http_requests_total{status=~"5.."}[5m]))',
            'unit': 'reqps',
            'thresholds': [{'value': 0.1, 'color': 'yellow'}, {'value': 1, 'color': 'red'}]
        },
        'db_connections': {
            'title': 'Database Connections',
            'expr': 'pg_stat_activity_count',
            'unit': 'short',
            'thresholds': [{'value': 80, 'color': 'yellow'}, {'value': 100, 'color': 'red'}]
        },
    }
    
    def __init__(self, ai_analyzer):
        self.ai = ai_analyzer
        self.grafana_url = GRAFANA_URL
        self.grafana_api_key = GRAFANA_API_KEY
        self.external_url = GRAFANA_EXTERNAL_URL
    
    async def generate_from_prompt(self, prompt: str) -> Dict[str, Any]:
        """Генерация дашборда из текстового запроса."""
        
        # Используем AI для парсинга запроса
        panels = await self._parse_prompt_with_ai(prompt)
        
        if not panels:
            # Fallback: простой парсинг ключевых слов
            panels = self._parse_prompt_simple(prompt)
        
        # Определяем временной диапазон из запроса
        time_range = self._extract_time_range(prompt)
        
        # Генерация JSON дашборда
        dashboard = self._build_dashboard(panels, prompt, time_range)
        
        return dashboard
    
    async def _parse_prompt_with_ai(self, prompt: str) -> List[str]:
        """Использование AI для понимания запроса."""
        system_prompt = """Ты помогаешь создавать Grafana дашборды.
        
Из запроса пользователя извлеки список метрик.
Доступные метрики: cpu, memory, disk, network_rx, network_tx, http_requests, http_latency, http_errors, db_connections

Ответь JSON массивом метрик, например: ["cpu", "memory", "disk"]

Если запрос общий (например "системные метрики"), включи: cpu, memory, disk
Если про сеть - network_rx, network_tx  
Если про HTTP/API - http_requests, http_latency, http_errors
"""
        try:
            response = await self.ai.analyze_raw(
                system_prompt=system_prompt,
                user_prompt=f"Запрос: {prompt}"
            )
            
            # Парсим JSON из ответа
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                metrics = json.loads(match.group())
                # Фильтруем только валидные метрики
                return [m for m in metrics if m in self.PANEL_TEMPLATES]
        except Exception as e:
            logger.warning(f"AI parsing failed: {e}")
        
        return []
    
    def _parse_prompt_simple(self, prompt: str) -> List[str]:
        """Простой парсинг запроса по ключевым словам."""
        prompt_lower = prompt.lower()
        panels = []
        
        keyword_map = {
            'cpu': ['cpu', 'процессор', 'нагрузка'],
            'memory': ['memory', 'ram', 'память', 'оперативн'],
            'disk': ['disk', 'диск', 'хранилище', 'место'],
            'network_rx': ['network', 'сеть', 'трафик', 'входящ'],
            'network_tx': ['network', 'сеть', 'трафик', 'исходящ'],
            'http_requests': ['http', 'request', 'запрос', 'api'],
            'http_latency': ['latency', 'задержк', 'время ответа'],
            'http_errors': ['error', 'ошибк', '5xx', '500'],
            'db_connections': ['database', 'db', 'postgres', 'база данных', 'соединени'],
        }
        
        for metric, keywords in keyword_map.items():
            if any(kw in prompt_lower for kw in keywords):
                panels.append(metric)
        
        # Если ничего не найдено - базовый набор
        if not panels:
            if any(w in prompt_lower for w in ['систем', 'обзор', 'overview', 'status', 'статус']):
                panels = ['cpu', 'memory', 'disk']
            else:
                panels = ['cpu', 'memory', 'disk', 'http_requests']
        
        return panels
    
    def _extract_time_range(self, prompt: str) -> str:
        """Извлечение временного диапазона из запроса."""
        prompt_lower = prompt.lower()
        
        patterns = {
            '1h': ['час', '1h', '1 час', 'hour'],
            '6h': ['6 час', '6h'],
            '12h': ['12 час', '12h', 'полдня'],
            '24h': ['24 час', '24h', 'сутки', 'день', 'day'],
            '7d': ['недел', '7d', '7 дн', 'week'],
            '30d': ['месяц', '30d', '30 дн', 'month'],
        }
        
        for range_val, keywords in patterns.items():
            if any(kw in prompt_lower for kw in keywords):
                return range_val
        
        return '6h'  # default
    
    def _build_dashboard(self, panel_names: List[str], title: str, time_range: str) -> Dict:
        """Построение JSON дашборда."""
        panels = []
        
        # Сетка 2 колонки
        col = 0
        row = 0
        
        for i, panel_name in enumerate(panel_names):
            template = self.PANEL_TEMPLATES.get(panel_name, {})
            if not template:
                continue
            
            panel = {
                "id": i + 1,
                "type": "timeseries",
                "title": template['title'],
                "gridPos": {"x": col * 12, "y": row * 8, "w": 12, "h": 8},
                "datasource": {"type": "prometheus", "uid": "prometheus"},
                "targets": [{
                    "expr": template['expr'],
                    "refId": "A",
                    "legendFormat": template['title']
                }],
                "fieldConfig": {
                    "defaults": {
                        "unit": template.get('unit', 'short'),
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [{"value": None, "color": "green"}] + [
                                {"value": t['value'], "color": t['color']} 
                                for t in template.get('thresholds', [])
                            ]
                        }
                    }
                },
                "options": {
                    "legend": {"displayMode": "list", "placement": "bottom"}
                }
            }
            panels.append(panel)
            
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        # Генерируем уникальный UID
        uid = hashlib.md5(f"{title}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        dashboard = {
            "dashboard": {
                "uid": uid,
                "title": f"AI Generated: {title[:50]}",
                "tags": ["ai-generated", "chatops"],
                "timezone": "browser",
                "panels": panels,
                "time": {"from": f"now-{time_range}", "to": "now"},
                "refresh": "30s",
                "schemaVersion": 38,
            },
            "overwrite": True,
            "message": f"Created by ChatOps AI: {title}"
        }
        
        return dashboard
    
    async def create_dashboard(self, dashboard: Dict) -> Tuple[bool, str]:
        """Создание дашборда через Grafana API."""
        if not self.grafana_api_key:
            return False, "GRAFANA_API_KEY не настроен"
        
        headers = {
            "Authorization": f"Bearer {self.grafana_api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.grafana_url}/api/dashboards/db",
                    headers=headers,
                    json=dashboard,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    uid = data.get('uid', dashboard['dashboard']['uid'])
                    url = f"{self.external_url}/d/{uid}"
                    return True, url
                else:
                    return False, f"Grafana API error: {response.status_code} - {response.text}"
                    
            except Exception as e:
                logger.error(f"Ошибка создания дашборда: {e}")
                return False, str(e)


# ============================================================================
# 2. RAG (Retrieval Augmented Generation) НА ЛОГАХ
# ============================================================================

class LogRAG:
    """RAG-система для интеллектуального поиска по логам."""
    
    def __init__(self, ai_analyzer):
        self.ai = ai_analyzer
        self.loki_url = LOKI_URL
    
    async def search_with_context(self, query: str, hours: int = 24) -> Dict[str, Any]:
        """
        RAG-поиск: 
        1. Получаем релевантные логи из Loki
        2. Группируем по времени и контексту
        3. Передаём в LLM для анализа
        """
        
        # Шаг 1: Извлекаем ключевые слова из запроса
        keywords = await self._extract_keywords(query)
        
        # Шаг 2: Поиск логов по ключевым словам
        logs = await self._search_loki(keywords, hours)
        
        if not logs:
            return {
                'status': 'no_logs',
                'message': 'Логи не найдены',
                'query': query,
                'keywords': keywords
            }
        
        # Шаг 3: Группировка и ранжирование логов
        grouped_logs = self._group_logs(logs)
        
        # Шаг 4: Формируем контекст для LLM
        context = self._build_context(grouped_logs, query)
        
        # Шаг 5: Анализ с помощью LLM
        analysis = await self._analyze_with_llm(query, context)
        
        return {
            'status': 'success',
            'query': query,
            'keywords': keywords,
            'logs_found': len(logs),
            'time_range': f'{hours}h',
            'groups': len(grouped_logs),
            'analysis': analysis,
            'sample_logs': logs[:5]
        }
    
    async def _extract_keywords(self, query: str) -> List[str]:
        """Извлечение ключевых слов из запроса."""
        # Базовые стоп-слова
        stop_words = {
            'что', 'как', 'почему', 'когда', 'где', 'кто', 'какой', 'какая', 'какое',
            'был', 'была', 'было', 'были', 'есть', 'это', 'эти', 'этот', 'эта',
            'в', 'на', 'по', 'за', 'из', 'от', 'до', 'с', 'к', 'о', 'и', 'или',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'why', 'how', 'when'
        }
        
        # Простая токенизация
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ0-9_-]+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Добавляем технические термины если есть
        tech_patterns = ['error', 'exception', 'fail', 'timeout', 'connect', 'refused']
        for pattern in tech_patterns:
            if pattern in query.lower() and pattern not in keywords:
                keywords.append(pattern)
        
        return keywords[:10]  # Лимит ключевых слов
    
    async def _search_loki(self, keywords: List[str], hours: int) -> List[Dict]:
        """Поиск в Loki по ключевым словам."""
        if not keywords:
            keywords = ['error']
        
        # Строим LogQL запрос с OR для всех ключевых слов
        pattern = '|'.join(re.escape(kw) for kw in keywords)
        logql = f'{{job=~".+"}} |~ "(?i)({pattern})"'
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        params = {
            'query': logql,
            'start': int(start_time.timestamp() * 1e9),
            'end': int(end_time.timestamp() * 1e9),
            'limit': 500,
            'direction': 'backward'
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.loki_url}/loki/api/v1/query_range",
                    params=params,
                    timeout=30
                )
                data = response.json()
                
                logs = []
                if data.get('status') == 'success':
                    for stream in data.get('data', {}).get('result', []):
                        labels = stream.get('stream', {})
                        for value in stream.get('values', []):
                            logs.append({
                                'timestamp': datetime.fromtimestamp(int(value[0]) / 1e9),
                                'message': value[1],
                                'labels': labels,
                                'job': labels.get('job', 'unknown'),
                                'level': self._detect_level(value[1])
                            })
                
                # Сортировка по времени
                logs.sort(key=lambda x: x['timestamp'], reverse=True)
                return logs
                
            except Exception as e:
                logger.error(f"Loki search error: {e}")
                return []
    
    def _detect_level(self, message: str) -> str:
        """Определение уровня лога."""
        msg_lower = message.lower()
        if any(w in msg_lower for w in ['error', 'exception', 'fatal', 'critical']):
            return 'error'
        elif any(w in msg_lower for w in ['warn', 'warning']):
            return 'warning'
        elif any(w in msg_lower for w in ['debug']):
            return 'debug'
        return 'info'
    
    def _group_logs(self, logs: List[Dict]) -> List[Dict]:
        """Группировка логов по временным окнам и источникам."""
        if not logs:
            return []
        
        groups = {}
        
        for log in logs:
            # Группируем по 5-минутным интервалам и job
            window = log['timestamp'].replace(
                minute=(log['timestamp'].minute // 5) * 5,
                second=0,
                microsecond=0
            )
            key = f"{window.isoformat()}_{log['job']}"
            
            if key not in groups:
                groups[key] = {
                    'start_time': window,
                    'job': log['job'],
                    'logs': [],
                    'error_count': 0,
                    'warning_count': 0
                }
            
            groups[key]['logs'].append(log)
            if log['level'] == 'error':
                groups[key]['error_count'] += 1
            elif log['level'] == 'warning':
                groups[key]['warning_count'] += 1
        
        # Сортируем группы по количеству ошибок
        sorted_groups = sorted(
            groups.values(), 
            key=lambda x: (x['error_count'], x['warning_count']),
            reverse=True
        )
        
        return sorted_groups[:20]  # Топ 20 групп
    
    def _build_context(self, groups: List[Dict], query: str) -> str:
        """Формирование контекста для LLM."""
        context = f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ: {query}\n\n"
        context += "НАЙДЕННЫЕ ЛОГИ (сгруппированы по времени и источнику):\n\n"
        
        for i, group in enumerate(groups[:10], 1):
            context += f"=== Группа {i} ===\n"
            context += f"Время: {group['start_time'].strftime('%Y-%m-%d %H:%M')}\n"
            context += f"Источник: {group['job']}\n"
            context += f"Ошибок: {group['error_count']}, Предупреждений: {group['warning_count']}\n"
            context += "Примеры сообщений:\n"
            
            for log in group['logs'][:5]:
                level_emoji = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️', 'debug': '🔍'}.get(log['level'], '•')
                msg = log['message'][:200]
                context += f"  {level_emoji} {msg}\n"
            
            context += "\n"
        
        return context
    
    async def _analyze_with_llm(self, query: str, context: str) -> str:
        """Анализ логов с помощью LLM."""
        system_prompt = """Ты — DevOps инженер, анализирующий логи.

На основе предоставленных логов ответь на вопрос пользователя.

Правила:
1. Отвечай конкретно на вопрос
2. Указывай временные рамки и источники проблем
3. Приводи цитаты из логов если нужно
4. Давай рекомендации по устранению
5. Используй emoji для наглядности
6. Отвечай на русском языке
"""
        
        try:
            response = await self.ai.analyze_raw(
                system_prompt=system_prompt,
                user_prompt=context
            )
            return response
        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return f"Ошибка анализа: {e}"


# ============================================================================
# 3. GRAFANA ANNOTATIONS
# ============================================================================

class GrafanaAnnotations:
    """Управление аннотациями в Grafana."""
    
    def __init__(self):
        self.grafana_url = GRAFANA_URL
        self.api_key = GRAFANA_API_KEY
    
    async def create_annotation(
        self,
        text: str,
        tags: List[str] = None,
        time_from: datetime = None,
        time_to: datetime = None,
        dashboard_uid: str = None,
        panel_id: int = None
    ) -> Tuple[bool, str]:
        """Создание аннотации в Grafana."""
        
        if not self.api_key:
            return False, "GRAFANA_API_KEY не настроен"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        now = datetime.now()
        
        annotation = {
            "text": text,
            "tags": tags or ["chatops", "ai"],
            "time": int((time_from or now).timestamp() * 1000),
        }
        
        if time_to:
            annotation["timeEnd"] = int(time_to.timestamp() * 1000)
        
        if dashboard_uid:
            annotation["dashboardUID"] = dashboard_uid
        
        if panel_id:
            annotation["panelId"] = panel_id
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.grafana_url}/api/annotations",
                    headers=headers,
                    json=annotation,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return True, f"Аннотация создана (ID: {data.get('id')})"
                else:
                    return False, f"Grafana error: {response.status_code}"
                    
            except Exception as e:
                logger.error(f"Annotation error: {e}")
                return False, str(e)
    
    async def create_anomaly_annotation(
        self,
        anomaly_data: Dict[str, Any],
        dashboard_uid: str = None
    ) -> Tuple[bool, str]:
        """Создание аннотации при обнаружении аномалии."""
        
        details = anomaly_data.get('details', [])
        score = anomaly_data.get('score', 0)
        
        text = f"🔴 Anomaly Detected (score: {score:.2f})\n"
        text += "\n".join(details) if details else "Unusual metric patterns detected"
        
        tags = ["anomaly", "ai-detected"]
        
        return await self.create_annotation(
            text=text,
            tags=tags,
            dashboard_uid=dashboard_uid
        )
    
    async def get_annotations(
        self,
        from_time: datetime = None,
        to_time: datetime = None,
        tags: List[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Получение списка аннотаций."""
        
        if not self.api_key:
            return []
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        params = {"limit": limit}
        
        if from_time:
            params["from"] = int(from_time.timestamp() * 1000)
        if to_time:
            params["to"] = int(to_time.timestamp() * 1000)
        if tags:
            params["tags"] = ",".join(tags)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.grafana_url}/api/annotations",
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    return response.json()
                    
            except Exception as e:
                logger.error(f"Get annotations error: {e}")
        
        return []


# ============================================================================
# 4. PREDICTIVE ANALYTICS (Prophet)
# ============================================================================

class PredictiveAnalytics:
    """Предиктивный анализ метрик."""
    
    SUPPORTED_METRICS = {
        'cpu': {
            'query': '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'name': 'CPU Usage',
            'unit': '%',
            'threshold': 90,
            'warning': 80
        },
        'memory': {
            'query': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
            'name': 'Memory Usage', 
            'unit': '%',
            'threshold': 95,
            'warning': 85
        },
        'disk': {
            'query': '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
            'name': 'Disk Usage',
            'unit': '%',
            'threshold': 95,
            'warning': 85
        },
    }
    
    def __init__(self):
        self.prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    
    async def predict(self, metric: str, hours_ahead: int = 24) -> Dict[str, Any]:
        """Прогноз метрики на N часов вперёд."""
        
        if metric not in self.SUPPORTED_METRICS:
            return {
                'status': 'error',
                'message': f'Метрика не поддерживается. Доступные: {", ".join(self.SUPPORTED_METRICS.keys())}'
            }
        
        config = self.SUPPORTED_METRICS[metric]
        
        # Получаем исторические данные (7 дней)
        history = await self._get_historical_data(config['query'], days=7)
        
        if len(history) < 100:
            return {
                'status': 'error',
                'message': 'Недостаточно исторических данных для прогноза (нужно минимум 7 дней)'
            }
        
        # Прогнозирование
        try:
            forecast = await self._make_forecast(history, hours_ahead)
        except Exception as e:
            # Fallback на простую линейную регрессию
            logger.warning(f"Prophet failed, using linear regression: {e}")
            forecast = self._linear_forecast(history, hours_ahead)
        
        # Анализ прогноза
        analysis = self._analyze_forecast(forecast, config)
        
        return {
            'status': 'success',
            'metric': metric,
            'metric_name': config['name'],
            'unit': config['unit'],
            'hours_ahead': hours_ahead,
            'current_value': history[-1]['value'] if history else None,
            'forecast': forecast,
            'analysis': analysis,
            'threshold': config['threshold'],
            'warning': config['warning']
        }
    
    async def _get_historical_data(self, query: str, days: int = 7) -> List[Dict]:
        """Получение исторических данных из Prometheus."""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        try:
            result = self.prom.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step='15m'  # 15-минутные интервалы
            )
            
            if result and len(result) > 0:
                return [
                    {
                        'timestamp': datetime.fromtimestamp(float(v[0])),
                        'value': float(v[1]) if v[1] != 'NaN' else 0.0
                    }
                    for v in result[0]['values']
                ]
        except Exception as e:
            logger.error(f"Historical data error: {e}")
        
        return []
    
    async def _make_forecast(self, history: List[Dict], hours_ahead: int) -> List[Dict]:
        """Прогнозирование с использованием Prophet."""
        try:
            from prophet import Prophet
            import pandas as pd
            
            # Подготовка данных для Prophet
            df = pd.DataFrame([
                {'ds': h['timestamp'], 'y': h['value']}
                for h in history
            ])
            
            # Инициализация и обучение модели
            model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05
            )
            
            # Запуск в отдельном потоке (Prophet не async)
            await asyncio.to_thread(model.fit, df)
            
            # Создаём dataframe для прогноза
            future = model.make_future_dataframe(periods=hours_ahead * 4, freq='15min')
            
            # Прогнозирование
            forecast = await asyncio.to_thread(model.predict, future)
            
            # Берём только будущие значения
            now = datetime.now()
            future_forecast = forecast[forecast['ds'] > now]
            
            return [
                {
                    'timestamp': row['ds'].to_pydatetime(),
                    'value': max(0, min(100, row['yhat'])),  # Ограничиваем 0-100
                    'lower': max(0, row['yhat_lower']),
                    'upper': min(100, row['yhat_upper'])
                }
                for _, row in future_forecast.iterrows()
            ]
            
        except ImportError:
            logger.warning("Prophet not installed, using linear regression")
            return self._linear_forecast(history, hours_ahead)
    
    def _linear_forecast(self, history: List[Dict], hours_ahead: int) -> List[Dict]:
        """Простой линейный прогноз как fallback."""
        if len(history) < 2:
            return []
        
        # Берём последние 24 часа для расчёта тренда
        recent = history[-96:]  # 96 * 15min = 24h
        
        if len(recent) < 2:
            recent = history
        
        # Линейная регрессия
        x = np.arange(len(recent))
        y = np.array([h['value'] for h in recent])
        
        # y = mx + b
        m = np.polyfit(x, y, 1)[0]
        b = np.mean(y) - m * np.mean(x)
        
        # Генерируем прогноз
        forecast = []
        last_time = history[-1]['timestamp']
        
        for i in range(hours_ahead * 4):  # 15-минутные интервалы
            future_x = len(recent) + i
            predicted_value = m * future_x + b
            
            # Ограничиваем значения
            predicted_value = max(0, min(100, predicted_value))
            
            forecast.append({
                'timestamp': last_time + timedelta(minutes=15 * (i + 1)),
                'value': predicted_value,
                'lower': max(0, predicted_value - 10),
                'upper': min(100, predicted_value + 10)
            })
        
        return forecast
    
    def _analyze_forecast(self, forecast: List[Dict], config: Dict) -> Dict[str, Any]:
        """Анализ прогноза - определение когда будет превышен порог."""
        
        threshold = config['threshold']
        warning = config['warning']
        
        # Ищем когда будет достигнут порог
        threshold_time = None
        warning_time = None
        max_value = 0
        
        for point in forecast:
            value = point['value']
            max_value = max(max_value, value)
            
            if value >= threshold and threshold_time is None:
                threshold_time = point['timestamp']
            
            if value >= warning and warning_time is None:
                warning_time = point['timestamp']
        
        # Формируем анализ
        now = datetime.now()
        
        if threshold_time:
            hours_to_threshold = (threshold_time - now).total_seconds() / 3600
            status = 'critical'
            message = f"🔴 Критический порог ({threshold}{config['unit']}) будет достигнут через {hours_to_threshold:.1f} часов"
        elif warning_time:
            hours_to_warning = (warning_time - now).total_seconds() / 3600
            status = 'warning'
            message = f"🟡 Порог предупреждения ({warning}{config['unit']}) будет достигнут через {hours_to_warning:.1f} часов"
        else:
            status = 'ok'
            message = f"🟢 Метрика останется в норме (макс. прогноз: {max_value:.1f}{config['unit']})"
        
        return {
            'status': status,
            'message': message,
            'max_predicted': max_value,
            'threshold_time': threshold_time.isoformat() if threshold_time else None,
            'warning_time': warning_time.isoformat() if warning_time else None,
            'hours_to_threshold': (threshold_time - now).total_seconds() / 3600 if threshold_time else None
        }


# ============================================================================
# ENHANCED AI ANALYZER (с поддержкой raw prompts)
# ============================================================================

class EnhancedAIAnalyzer:
    """Расширенный AI анализатор с поддержкой custom prompts."""
    
    PROVIDERS = {
        'openai': {'base_url': None, 'model': 'gpt-4o-mini'},
        'anthropic': {'base_url': None, 'model': 'claude-3-haiku-20240307'},
        'openrouter': {'base_url': 'https://openrouter.ai/api/v1', 'model': 'anthropic/claude-3-haiku'},
        'deepseek': {'base_url': 'https://api.deepseek.com/v1', 'model': 'deepseek-chat'},
        'gemini': {'base_url': None, 'model': 'gemini-1.5-flash'},
    }
    
    def __init__(self):
        self.provider = AI_PROVIDER
        self.keys = {
            'openai': OPENAI_API_KEY,
            'anthropic': ANTHROPIC_API_KEY,
            'openrouter': OPENROUTER_API_KEY,
            'deepseek': DEEPSEEK_API_KEY,
            'gemini': GEMINI_API_KEY,
        }
    
    async def analyze_raw(self, system_prompt: str, user_prompt: str) -> str:
        """Выполнение произвольного запроса к LLM."""
        
        provider = self.provider
        if not self.keys.get(provider):
            available = [p for p, k in self.keys.items() if k]
            provider = available[0] if available else None
        
        if not provider:
            raise ValueError("No AI provider configured")
        
        if provider == 'anthropic':
            return await self._call_anthropic(system_prompt, user_prompt)
        elif provider == 'gemini':
            return await self._call_gemini(system_prompt, user_prompt)
        else:
            return await self._call_openai_compatible(provider, system_prompt, user_prompt)
    
    async def _call_openai_compatible(self, provider: str, system: str, user: str) -> str:
        """Вызов OpenAI-совместимых API."""
        import openai
        
        config = self.PROVIDERS.get(provider, {})
        
        client = openai.AsyncOpenAI(
            api_key=self.keys.get(provider),
            base_url=config.get('base_url')
        )
        
        response = await client.chat.completions.create(
            model=config.get('model', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    async def _call_anthropic(self, system: str, user: str) -> str:
        """Вызов Anthropic Claude."""
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=self.keys.get('anthropic'))
        
        response = await client.messages.create(
            model=self.PROVIDERS['anthropic']['model'],
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        
        return response.content[0].text
    
    async def _call_gemini(self, system: str, user: str) -> str:
        """Вызов Google Gemini."""
        import google.generativeai as genai
        
        genai.configure(api_key=self.keys.get('gemini'))
        model = genai.GenerativeModel(self.PROVIDERS['gemini']['model'])
        
        response = await asyncio.to_thread(
            model.generate_content,
            f"{system}\n\n{user}"
        )
        
        return response.text


# ============================================================================
# ENHANCED CHATOPS BOT
# ============================================================================

class EnhancedChatOpsBot:
    """Расширенный ChatOps бот с AI возможностями."""
    
    def __init__(self):
        # Базовые сервисы (импорт с fallback для Docker)
        try:
            from .chatops_bot import MetricsService, LogsService, AlertsService
        except ImportError:
            from chatops_bot import MetricsService, LogsService, AlertsService
        
        self.metrics = MetricsService()
        self.logs_service = LogsService()
        self.alerts = AlertsService()
        
        # Расширенные сервисы
        self.ai = EnhancedAIAnalyzer()
        self.dashboard_gen = GrafanaDashboardGenerator(self.ai)
        self.log_rag = LogRAG(self.ai)
        self.annotations = GrafanaAnnotations()
        self.predictor = PredictiveAnalytics()
        
        self.allowed_users = [u.strip() for u in ALLOWED_USERS if u.strip()]
    
    def is_authorized(self, update: Update) -> bool:
        """Проверка авторизации."""
        if not self.allowed_users:
            return True
        
        user = update.effective_user
        user_id = str(user.id)
        username = user.username or ''
        
        return user_id in self.allowed_users or username in self.allowed_users
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /start."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data='status'),
                InlineKeyboardButton("🤖 AI Analyze", callback_data='analyze'),
            ],
            [
                InlineKeyboardButton("📚 RAG Logs", callback_data='rag_help'),
                InlineKeyboardButton("🔮 Predict", callback_data='predict_help'),
            ],
            [
                InlineKeyboardButton("🎨 Dashboard", callback_data='dashboard_help'),
                InlineKeyboardButton("❓ Help", callback_data='help'),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 <b>Sattva Enhanced ChatOps Bot</b>\n\n"
            "<b>Новые AI-команды:</b>\n"
            "📚 /rag [вопрос] - Умный поиск по логам\n"
            "🔮 /predict [metric] [hours] - Прогноз ресурсов\n"
            "🎨 /dashboard [описание] - Создать дашборд\n"
            "📍 /annotate [текст] - Добавить аннотацию\n\n"
            "<b>Базовые команды:</b>\n"
            "/status - Статус системы\n"
            "/analyze - AI-анализ\n"
            "/logs [query] - Поиск логов\n"
            "/alerts - Активные алерты",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /help."""
        help_text = """
🤖 <b>Enhanced ChatOps Bot - Справка</b>

<b>📚 RAG Поиск по логам:</b>
<code>/rag почему вчера упал backend?</code>
<code>/rag что за ошибки с подключением к БД?</code>
<code>/rag timeout ошибки за последние сутки</code>

<b>🔮 Предиктивный анализ:</b>
<code>/predict cpu 24</code> - прогноз CPU на 24ч
<code>/predict disk 48</code> - прогноз диска на 48ч
<code>/predict memory 12</code> - прогноз памяти на 12ч

<b>🎨 Генерация дашбордов:</b>
<code>/dashboard CPU и память за неделю</code>
<code>/dashboard HTTP метрики с ошибками</code>
<code>/dashboard все системные метрики</code>

<b>📍 Аннотации Grafana:</b>
<code>/annotate Деплой v1.2.3</code>
<code>/annotate Исправлен баг #123</code>

<b>AI-провайдер:</b> {provider}
"""
        await update.message.reply_text(
            help_text.format(provider=AI_PROVIDER),
            parse_mode='HTML'
        )
    
    # =========================
    # RAG COMMAND
    # =========================
    
    async def rag_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /rag - RAG поиск по логам."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        query = ' '.join(context.args) if context.args else None
        
        if not query:
            await update.message.reply_text(
                "📚 <b>RAG Поиск по логам</b>\n\n"
                "Использование: <code>/rag [ваш вопрос]</code>\n\n"
                "Примеры:\n"
                "• <code>/rag почему вчера был downtime?</code>\n"
                "• <code>/rag ошибки подключения к PostgreSQL</code>\n"
                "• <code>/rag что за 500 ошибки в API?</code>",
                parse_mode='HTML'
            )
            return
        
        msg = await update.message.reply_text("🔍 Анализирую логи с помощью AI...")
        
        try:
            result = await self.log_rag.search_with_context(query, hours=24)
            
            if result['status'] == 'no_logs':
                await msg.edit_text(
                    f"📭 <b>Логи не найдены</b>\n\n"
                    f"Запрос: {query}\n"
                    f"Ключевые слова: {', '.join(result['keywords'])}",
                    parse_mode='HTML'
                )
                return
            
            response = f"📚 <b>RAG Анализ логов</b>\n\n"
            response += f"🔎 Запрос: {query}\n"
            response += f"📊 Найдено логов: {result['logs_found']}\n"
            response += f"⏰ Период: последние {result['time_range']}\n\n"
            response += f"🤖 <b>AI Анализ:</b>\n{result['analysis']}"
            
            # Обрезаем если слишком длинный
            if len(response) > 4000:
                response = response[:3900] + "\n\n... (ответ обрезан)"
            
            await msg.edit_text(response, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"RAG error: {e}")
            await msg.edit_text(f"❌ Ошибка: {e}")
    
    # =========================
    # PREDICT COMMAND
    # =========================
    
    async def predict_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /predict - прогноз метрик."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        args = context.args or []
        
        if len(args) < 1:
            metrics = ', '.join(PredictiveAnalytics.SUPPORTED_METRICS.keys())
            await update.message.reply_text(
                f"🔮 <b>Предиктивный анализ</b>\n\n"
                f"Использование: <code>/predict [metric] [hours]</code>\n\n"
                f"Доступные метрики: {metrics}\n\n"
                f"Примеры:\n"
                f"• <code>/predict cpu 24</code> - CPU на 24 часа\n"
                f"• <code>/predict disk 48</code> - Диск на 48 часов\n"
                f"• <code>/predict memory 12</code> - Память на 12 часов",
                parse_mode='HTML'
            )
            return
        
        metric = args[0].lower()
        hours = int(args[1]) if len(args) > 1 and args[1].isdigit() else 24
        hours = min(max(1, hours), 168)  # Ограничение 1-168 часов
        
        msg = await update.message.reply_text(f"🔮 Строю прогноз {metric} на {hours} часов...")
        
        try:
            result = await self.predictor.predict(metric, hours)
            
            if result['status'] == 'error':
                await msg.edit_text(f"❌ {result['message']}")
                return
            
            analysis = result['analysis']
            
            response = f"🔮 <b>Прогноз: {result['metric_name']}</b>\n\n"
            response += f"📊 Текущее значение: {result['current_value']:.1f}{result['unit']}\n"
            response += f"⏰ Горизонт прогноза: {hours} часов\n"
            response += f"⚠️ Порог предупреждения: {result['warning']}{result['unit']}\n"
            response += f"🔴 Критический порог: {result['threshold']}{result['unit']}\n\n"
            response += f"<b>Результат:</b>\n{analysis['message']}\n\n"
            response += f"📈 Максимум прогноза: {analysis['max_predicted']:.1f}{result['unit']}"
            
            if analysis['hours_to_threshold']:
                response += f"\n⏳ До критического порога: {analysis['hours_to_threshold']:.1f}ч"
            
            await msg.edit_text(response, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Predict error: {e}")
            await msg.edit_text(f"❌ Ошибка прогнозирования: {e}")
    
    # =========================
    # DASHBOARD COMMAND
    # =========================
    
    async def dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /dashboard - генерация дашборда."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        prompt = ' '.join(context.args) if context.args else None
        
        if not prompt:
            await update.message.reply_text(
                "🎨 <b>Генератор дашбордов</b>\n\n"
                "Использование: <code>/dashboard [описание]</code>\n\n"
                "Примеры:\n"
                "• <code>/dashboard CPU и память за неделю</code>\n"
                "• <code>/dashboard HTTP метрики с latency</code>\n"
                "• <code>/dashboard полный мониторинг системы</code>\n"
                "• <code>/dashboard сеть и база данных</code>",
                parse_mode='HTML'
            )
            return
        
        msg = await update.message.reply_text("🎨 Генерирую дашборд...")
        
        try:
            # Генерация JSON дашборда
            dashboard = await self.dashboard_gen.generate_from_prompt(prompt)
            
            # Создание в Grafana
            success, result = await self.dashboard_gen.create_dashboard(dashboard)
            
            if success:
                panels = dashboard['dashboard']['panels']
                panel_names = [p['title'] for p in panels]
                
                response = f"✅ <b>Дашборд создан!</b>\n\n"
                response += f"📝 Запрос: {prompt}\n"
                response += f"📊 Панелей: {len(panels)}\n"
                response += f"📈 Метрики: {', '.join(panel_names)}\n\n"
                response += f"🔗 <a href='{result}'>Открыть дашборд</a>"
                
                await msg.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
            else:
                # Показываем JSON если не удалось создать
                response = f"⚠️ Дашборд сгенерирован, но не создан в Grafana:\n{result}\n\n"
                response += f"JSON доступен для ручного импорта."
                await msg.edit_text(response)
                
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            await msg.edit_text(f"❌ Ошибка: {e}")
    
    # =========================
    # ANNOTATE COMMAND
    # =========================
    
    async def annotate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /annotate - создание аннотации."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        text = ' '.join(context.args) if context.args else None
        
        if not text:
            await update.message.reply_text(
                "📍 <b>Grafana Аннотации</b>\n\n"
                "Использование: <code>/annotate [текст]</code>\n\n"
                "Примеры:\n"
                "• <code>/annotate Деплой версии 1.2.3</code>\n"
                "• <code>/annotate Начало нагрузочного теста</code>\n"
                "• <code>/annotate Исправлен баг #123</code>",
                parse_mode='HTML'
            )
            return
        
        success, result = await self.annotations.create_annotation(
            text=text,
            tags=["chatops", "manual"]
        )
        
        if success:
            await update.message.reply_text(
                f"✅ <b>Аннотация создана</b>\n\n"
                f"📝 {text}\n"
                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"🏷️ Tags: chatops, manual",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(f"❌ Ошибка: {result}")
    
    # =========================
    # CALLBACK HANDLER
    # =========================
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопок."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'help':
            await self.help_command(update, context)
        elif data == 'rag_help':
            context.args = []
            await self.rag_command(update, context)
        elif data == 'predict_help':
            context.args = []
            await self.predict_command(update, context)
        elif data == 'dashboard_help':
            context.args = []
            await self.dashboard_command(update, context)
    
    # =========================
    # RUN BOT
    # =========================
    
    def run(self):
        """Запуск бота."""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN не задан!")
            return
        
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Новые команды
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("rag", self.rag_command))
        application.add_handler(CommandHandler("predict", self.predict_command))
        application.add_handler(CommandHandler("dashboard", self.dashboard_command))
        application.add_handler(CommandHandler("annotate", self.annotate_command))
        
        # Callback
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("Enhanced ChatOps Bot запущен!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = EnhancedChatOpsBot()
    bot.run()
