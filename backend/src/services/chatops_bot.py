"""
ChatOps Telegram Bot с AI
Telegram-бот для мониторинга и анализа метрик с использованием AI.

Команды:
/status - Текущий статус системы
/metrics - Детальные метрики
/logs [query] - Поиск по логам
/analyze - AI-анализ текущего состояния
/alerts - Активные алерты
/help - Справка

Автор: Jarvis
Дата: 2025-12-29
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json

import httpx
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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
QWEN_API_KEY = os.getenv('QWEN_API_KEY', '')
ZAI_API_KEY = os.getenv('ZAI_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai')  # openai, anthropic, openrouter, deepseek, qwen, zai, gemini
ALLOWED_USERS = os.getenv('ALLOWED_USERS', '').split(',')


class MetricsService:
    """Сервис для получения метрик."""
    
    def __init__(self):
        self.prom = PrometheusConnect(url=PROMETHEUS_URL, disable_ssl=True)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Получить общий статус системы."""
        queries = {
            'cpu': '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'memory': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
            'disk': '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
            'uptime': 'time() - node_boot_time_seconds',
        }
        
        result = {}
        for name, query in queries.items():
            try:
                data = self.prom.custom_query(query=query)
                if data and len(data) > 0:
                    result[name] = float(data[0]['value'][1])
                else:
                    result[name] = None
            except Exception as e:
                logger.warning(f"Ошибка запроса {name}: {e}")
                result[name] = None
        
        return result
    
    async def get_detailed_metrics(self) -> Dict[str, Any]:
        """Получить детальные метрики."""
        queries = {
            'cpu_usage': '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'cpu_load_1m': 'node_load1',
            'cpu_load_5m': 'node_load5',
            'memory_used_gb': '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024 / 1024',
            'memory_total_gb': 'node_memory_MemTotal_bytes / 1024 / 1024 / 1024',
            'disk_used_gb': '(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_avail_bytes{mountpoint="/"}) / 1024 / 1024 / 1024',
            'disk_total_gb': 'node_filesystem_size_bytes{mountpoint="/"} / 1024 / 1024 / 1024',
            'network_rx_bytes': 'sum(rate(node_network_receive_bytes_total[5m]))',
            'network_tx_bytes': 'sum(rate(node_network_transmit_bytes_total[5m]))',
            'http_requests_rate': 'sum(rate(http_requests_total[5m]))',
            'http_errors_rate': 'sum(rate(http_requests_total{status=~"5.."}[5m]))',
            'http_latency_p95': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            'db_connections': 'pg_stat_activity_count',
            'active_streams': 'stream_active_total',
        }
        
        result = {}
        for name, query in queries.items():
            try:
                data = self.prom.custom_query(query=query)
                if data and len(data) > 0:
                    result[name] = float(data[0]['value'][1])
                else:
                    result[name] = None
            except Exception as e:
                result[name] = None
        
        return result
    
    async def get_metric_history(self, query: str, hours: int = 1) -> List[Dict]:
        """Получить историю метрики."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        try:
            result = self.prom.custom_query_range(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step='1m'
            )
            
            if result and len(result) > 0:
                return [
                    {'time': datetime.fromtimestamp(float(v[0])), 'value': float(v[1])}
                    for v in result[0]['values']
                ]
        except Exception as e:
            logger.error(f"Ошибка получения истории: {e}")
        
        return []


class LogsService:
    """Сервис для работы с логами Loki."""
    
    def __init__(self):
        self.loki_url = LOKI_URL
    
    async def search_logs(self, query: str, limit: int = 20) -> List[Dict]:
        """Поиск по логам."""
        url = f"{self.loki_url}/loki/api/v1/query_range"
        
        # Построение LogQL запроса
        logql = f'{{job=~".+"}} |~ "{query}"'
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)
        
        params = {
            'query': logql,
            'start': int(start_time.timestamp() * 1e9),
            'end': int(end_time.timestamp() * 1e9),
            'limit': limit,
            'direction': 'backward'
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=10)
                data = response.json()
                
                logs = []
                if data.get('status') == 'success':
                    for stream in data.get('data', {}).get('result', []):
                        labels = stream.get('stream', {})
                        for value in stream.get('values', []):
                            logs.append({
                                'timestamp': datetime.fromtimestamp(int(value[0]) / 1e9),
                                'message': value[1],
                                'labels': labels
                            })
                
                return logs[:limit]
                
            except Exception as e:
                logger.error(f"Ошибка поиска логов: {e}")
                return []
    
    async def get_error_logs(self, limit: int = 10) -> List[Dict]:
        """Получить последние ошибки."""
        return await self.search_logs('error|ERROR|Error|exception|Exception', limit)


class AIAnalyzer:
    """AI-анализатор метрик с поддержкой множества провайдеров."""
    
    # Конфигурация провайдеров
    PROVIDERS = {
        'openai': {'base_url': None, 'model': 'gpt-4o-mini'},
        'anthropic': {'base_url': None, 'model': 'claude-3-haiku-20240307'},
        'openrouter': {'base_url': 'https://openrouter.ai/api/v1', 'model': 'anthropic/claude-3-haiku'},
        'deepseek': {'base_url': 'https://api.deepseek.com/v1', 'model': 'deepseek-chat'},
        'qwen': {'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'model': 'qwen-turbo'},
        'zai': {'base_url': 'https://api.z.ai/v1', 'model': 'z1-mini'},
        'gemini': {'base_url': None, 'model': 'gemini-1.5-flash'},
    }
    
    def __init__(self):
        self.provider = AI_PROVIDER
        self.keys = {
            'openai': OPENAI_API_KEY,
            'anthropic': ANTHROPIC_API_KEY,
            'openrouter': OPENROUTER_API_KEY,
            'deepseek': DEEPSEEK_API_KEY,
            'qwen': QWEN_API_KEY,
            'zai': ZAI_API_KEY,
            'gemini': GEMINI_API_KEY,
        }
    
    def get_available_providers(self) -> List[str]:
        """Получить список доступных провайдеров."""
        return [p for p, key in self.keys.items() if key]
    
    async def analyze(self, metrics: Dict[str, Any], logs: List[Dict] = None) -> str:
        """Анализ метрик с помощью AI."""
        
        # Формирование промпта
        prompt = self._build_prompt(metrics, logs)
        
        # Выбор провайдера
        provider = self.provider
        if not self.keys.get(provider):
            # Fallback на первый доступный
            available = self.get_available_providers()
            provider = available[0] if available else None
        
        if not provider:
            return self._fallback_analysis(metrics)
        
        # Роутинг по провайдерам
        if provider == 'anthropic':
            return await self._analyze_anthropic(prompt)
        elif provider == 'gemini':
            return await self._analyze_gemini(prompt)
        elif provider in ['openai', 'openrouter', 'deepseek', 'qwen', 'zai']:
            return await self._analyze_openai_compatible(prompt, provider)
        else:
            return self._fallback_analysis(metrics)
    
    def _build_prompt(self, metrics: Dict, logs: List[Dict] = None) -> str:
        """Построение промпта для AI."""
        prompt = """Ты — DevOps AI-ассистент. Проанализируй метрики сервера и дай краткие рекомендации.

ТЕКУЩИЕ МЕТРИКИ:
"""
        for key, value in metrics.items():
            if value is not None:
                prompt += f"- {key}: {value:.2f}\n"
            else:
                prompt += f"- {key}: N/A\n"
        
        if logs:
            prompt += "\nПОСЛЕДНИЕ ОШИБКИ:\n"
            for log in logs[:5]:
                prompt += f"- [{log['timestamp']}] {log['message'][:200]}\n"
        
        prompt += """
ЗАДАЧА:
1. Оцени общее состояние системы (🟢 отлично / 🟡 требует внимания / 🔴 критично)
2. Выдели 1-3 главные проблемы (если есть)
3. Дай 1-3 конкретные рекомендации

Отвечай кратко, на русском языке, используй emoji для наглядности.
"""
        return prompt
    
    async def _analyze_openai_compatible(self, prompt: str, provider: str) -> str:
        """Анализ через OpenAI-совместимые API (OpenAI, OpenRouter, DeepSeek, Qwen, z.ai)."""
        try:
            import openai
            
            config = self.PROVIDERS.get(provider, {})
            api_key = self.keys.get(provider)
            base_url = config.get('base_url')
            model = config.get('model', 'gpt-4o-mini')
            
            # Дополнительные заголовки для OpenRouter
            default_headers = {}
            if provider == 'openrouter':
                default_headers = {
                    'HTTP-Referer': 'https://sattva.app',
                    'X-Title': 'Sattva ChatOps'
                }
            
            client = openai.AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=default_headers if default_headers else None
            )
            
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Ты — опытный DevOps инженер."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка {provider}: {e}")
            return f"Ошибка AI анализа ({provider}): {e}"
    
    async def _analyze_anthropic(self, prompt: str) -> str:
        """Анализ через Anthropic Claude."""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.keys.get('anthropic'))
            
            response = await client.messages.create(
                model=self.PROVIDERS['anthropic']['model'],
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Ошибка Anthropic: {e}")
            return f"Ошибка AI анализа (anthropic): {e}"
    
    async def _analyze_gemini(self, prompt: str) -> str:
        """Анализ через Google Gemini."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.keys.get('gemini'))
            model = genai.GenerativeModel(self.PROVIDERS['gemini']['model'])
            
            response = await asyncio.to_thread(
                model.generate_content,
                f"Ты — опытный DevOps инженер.\n\n{prompt}"
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Ошибка Gemini: {e}")
            return f"Ошибка AI анализа (gemini): {e}"
    
    def _fallback_analysis(self, metrics: Dict) -> str:
        """Простой анализ без AI."""
        issues = []
        status = "🟢"
        
        cpu = metrics.get('cpu_usage')
        if cpu and cpu > 80:
            issues.append(f"⚠️ Высокая нагрузка CPU: {cpu:.1f}%")
            status = "🔴" if cpu > 90 else "🟡"
        
        memory = metrics.get('memory_used_gb')
        memory_total = metrics.get('memory_total_gb')
        if memory and memory_total:
            mem_pct = (memory / memory_total) * 100
            if mem_pct > 85:
                issues.append(f"⚠️ Высокое использование памяти: {mem_pct:.1f}%")
                status = "🔴" if mem_pct > 95 else "🟡"
        
        disk = metrics.get('disk_used_gb')
        disk_total = metrics.get('disk_total_gb')
        if disk and disk_total:
            disk_pct = (disk / disk_total) * 100
            if disk_pct > 85:
                issues.append(f"⚠️ Мало места на диске: {disk_pct:.1f}%")
                status = "🔴" if disk_pct > 95 else "🟡"
        
        errors = metrics.get('http_errors_rate')
        if errors and errors > 0.1:
            issues.append(f"⚠️ Высокий уровень ошибок: {errors:.2f}/сек")
            status = "🟡"
        
        result = f"{status} <b>Статус системы</b>\n\n"
        
        if issues:
            result += "<b>Проблемы:</b>\n"
            for issue in issues:
                result += f"{issue}\n"
        else:
            result += "✅ Все показатели в норме\n"
        
        return result


class AlertsService:
    """Сервис для работы с алертами."""
    
    async def get_active_alerts(self) -> List[Dict]:
        """Получить активные алерты из Alertmanager."""
        url = f"http://alertmanager:9093/api/v2/alerts"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10)
                return response.json()
            except Exception as e:
                logger.error(f"Ошибка получения алертов: {e}")
                return []


class ChatOpsBot:
    """Telegram бот для ChatOps."""
    
    def __init__(self):
        self.metrics = MetricsService()
        self.logs = LogsService()
        self.ai = AIAnalyzer()
        self.alerts = AlertsService()
        self.allowed_users = [u.strip() for u in ALLOWED_USERS if u.strip()]
    
    def is_authorized(self, update: Update) -> bool:
        """Проверка авторизации пользователя."""
        if not self.allowed_users:
            return True  # Если список пуст - разрешить всем
        
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
                InlineKeyboardButton("📈 Metrics", callback_data='metrics'),
            ],
            [
                InlineKeyboardButton("🤖 AI Analyze", callback_data='analyze'),
                InlineKeyboardButton("🚨 Alerts", callback_data='alerts'),
            ],
            [
                InlineKeyboardButton("📜 Logs", callback_data='logs'),
                InlineKeyboardButton("❓ Help", callback_data='help'),
            ],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 <b>Sattva ChatOps Bot</b>\n\n"
            "Выберите команду или введите:\n"
            "/status - Статус системы\n"
            "/metrics - Детальные метрики\n"
            "/analyze - AI-анализ\n"
            "/logs [запрос] - Поиск по логам\n"
            "/alerts - Активные алерты",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /help."""
        help_text = """
🤖 <b>Sattva ChatOps Bot - Справка</b>

<b>Команды:</b>
/start - Главное меню
/status - Краткий статус системы
/metrics - Детальные метрики
/analyze - AI-анализ состояния
/logs [query] - Поиск по логам
/alerts - Активные алерты
/help - Эта справка

<b>Примеры:</b>
• <code>/logs error</code> - найти ошибки
• <code>/logs timeout</code> - найти таймауты
• <code>/analyze</code> - попросить AI оценить состояние

<b>AI-провайдеры:</b>
Бот поддерживает OpenAI и Anthropic Claude.
Текущий: {provider}
"""
        await update.message.reply_text(
            help_text.format(provider=AI_PROVIDER),
            parse_mode='HTML'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /status."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        await update.message.reply_text("⏳ Получаю статус...")
        
        status = await self.metrics.get_system_status()
        
        cpu = status.get('cpu')
        memory = status.get('memory')
        disk = status.get('disk')
        uptime = status.get('uptime')
        
        # Определение статуса
        health = "🟢"
        if cpu and cpu > 80 or memory and memory > 85 or disk and disk > 90:
            health = "🔴" if (cpu and cpu > 95 or memory and memory > 95 or disk and disk > 95) else "🟡"
        
        # Форматирование uptime
        uptime_str = "N/A"
        if uptime:
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            uptime_str = f"{days}д {hours}ч"
        
        message = f"""
{health} <b>Статус системы</b>

💻 CPU: {cpu:.1f}% {self._get_bar(cpu)}
💾 RAM: {memory:.1f}% {self._get_bar(memory)}
💿 Disk: {disk:.1f}% {self._get_bar(disk)}
⏱️ Uptime: {uptime_str}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await update.message.reply_text(message, parse_mode='HTML')
    
    def _get_bar(self, value: float, width: int = 10) -> str:
        """Создать текстовый прогресс-бар."""
        if value is None:
            return "░" * width
        filled = int(value / 100 * width)
        return "█" * filled + "░" * (width - filled)
    
    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /metrics."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        await update.message.reply_text("⏳ Собираю метрики...")
        
        metrics = await self.metrics.get_detailed_metrics()
        
        message = "<b>📈 Детальные метрики</b>\n\n"
        
        # CPU
        message += "<b>CPU:</b>\n"
        message += f"  • Usage: {self._fmt(metrics.get('cpu_usage'))}%\n"
        message += f"  • Load 1m: {self._fmt(metrics.get('cpu_load_1m'))}\n"
        message += f"  • Load 5m: {self._fmt(metrics.get('cpu_load_5m'))}\n\n"
        
        # Memory
        message += "<b>Memory:</b>\n"
        message += f"  • Used: {self._fmt(metrics.get('memory_used_gb'))} GB\n"
        message += f"  • Total: {self._fmt(metrics.get('memory_total_gb'))} GB\n\n"
        
        # Disk
        message += "<b>Disk:</b>\n"
        message += f"  • Used: {self._fmt(metrics.get('disk_used_gb'))} GB\n"
        message += f"  • Total: {self._fmt(metrics.get('disk_total_gb'))} GB\n\n"
        
        # Network
        message += "<b>Network:</b>\n"
        rx = metrics.get('network_rx_bytes')
        tx = metrics.get('network_tx_bytes')
        message += f"  • RX: {self._fmt_bytes(rx)}/s\n"
        message += f"  • TX: {self._fmt_bytes(tx)}/s\n\n"
        
        # HTTP
        message += "<b>HTTP:</b>\n"
        message += f"  • Requests: {self._fmt(metrics.get('http_requests_rate'))}/s\n"
        message += f"  • Errors: {self._fmt(metrics.get('http_errors_rate'))}/s\n"
        latency = metrics.get('http_latency_p95')
        message += f"  • Latency P95: {self._fmt(latency * 1000 if latency else None)} ms\n\n"
        
        # Services
        message += "<b>Services:</b>\n"
        message += f"  • DB Connections: {self._fmt(metrics.get('db_connections'), 0)}\n"
        message += f"  • Active Streams: {self._fmt(metrics.get('active_streams'), 0)}\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    def _fmt(self, value: float, decimals: int = 2) -> str:
        """Форматирование числа."""
        if value is None:
            return "N/A"
        if decimals == 0:
            return str(int(value))
        return f"{value:.{decimals}f}"
    
    def _fmt_bytes(self, bytes_val: float) -> str:
        """Форматирование байтов."""
        if bytes_val is None:
            return "N/A"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} TB"
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /analyze."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        await update.message.reply_text("🤖 AI анализирует метрики...")
        
        metrics = await self.metrics.get_detailed_metrics()
        error_logs = await self.logs.get_error_logs(limit=5)
        
        analysis = await self.ai.analyze(metrics, error_logs)
        
        await update.message.reply_text(
            f"🤖 <b>AI Анализ</b>\n\n{analysis}",
            parse_mode='HTML'
        )
    
    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /logs."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        query = ' '.join(context.args) if context.args else 'error'
        
        await update.message.reply_text(f"🔍 Ищу логи: {query}...")
        
        logs = await self.logs.search_logs(query, limit=10)
        
        if not logs:
            await update.message.reply_text("📭 Логи не найдены")
            return
        
        message = f"📜 <b>Логи ({len(logs)} записей)</b>\n\n"
        
        for log in logs[:10]:
            timestamp = log['timestamp'].strftime('%H:%M:%S')
            msg = log['message'][:100]
            message += f"<code>{timestamp}</code> {msg}\n\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик /alerts."""
        if not self.is_authorized(update):
            await update.message.reply_text("⛔ Доступ запрещён")
            return
        
        alerts = await self.alerts.get_active_alerts()
        
        if not alerts:
            await update.message.reply_text("✅ Нет активных алертов")
            return
        
        message = f"🚨 <b>Активные алерты ({len(alerts)})</b>\n\n"
        
        for alert in alerts[:10]:
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            
            name = labels.get('alertname', 'Unknown')
            severity = labels.get('severity', 'unknown')
            summary = annotations.get('summary', '')
            
            severity_emoji = {'critical': '🔴', 'warning': '🟡', 'info': '🔵'}.get(severity, '⚪')
            
            message += f"{severity_emoji} <b>{name}</b>\n"
            message += f"   {summary}\n\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки."""
        query = update.callback_query
        await query.answer()
        
        # Создаём фейковый Update для вызова команд
        if query.data == 'status':
            await self.status_command(update, context)
        elif query.data == 'metrics':
            await self.metrics_command(update, context)
        elif query.data == 'analyze':
            await self.analyze_command(update, context)
        elif query.data == 'alerts':
            await self.alerts_command(update, context)
        elif query.data == 'logs':
            context.args = []
            await self.logs_command(update, context)
        elif query.data == 'help':
            await self.help_command(update, context)
    
    def run(self):
        """Запуск бота."""
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN не задан!")
            return
        
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("metrics", self.metrics_command))
        application.add_handler(CommandHandler("analyze", self.analyze_command))
        application.add_handler(CommandHandler("logs", self.logs_command))
        application.add_handler(CommandHandler("alerts", self.alerts_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        logger.info("ChatOps Bot запущен!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    bot = ChatOpsBot()
    bot.run()
