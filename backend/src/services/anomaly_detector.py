"""
Anomaly Detection Service
ML-сервис для предсказания проблем в инфраструктуре.

Использует Isolation Forest для обнаружения аномалий в метриках:
- CPU usage
- Memory usage
- Disk usage
- Request latency
- Error rate

Автор: Jarvis
Дата: 2025-12-29
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from prometheus_api_client import PrometheusConnect

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
ALERTMANAGER_URL = os.getenv('ALERTMANAGER_URL', 'http://alertmanager:9093')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
DETECTION_INTERVAL = int(os.getenv('DETECTION_INTERVAL', '60'))  # секунды
TRAINING_HOURS = int(os.getenv('TRAINING_HOURS', '24'))
MODEL_PATH = '/app/models'


class MetricsCollector:
    """Сбор метрик из Prometheus."""
    
    def __init__(self, prometheus_url: str):
        self.prom = PrometheusConnect(url=prometheus_url, disable_ssl=True)
        
    async def get_current_metrics(self) -> Dict[str, float]:
        """Получить текущие значения метрик."""
        metrics = {}
        
        queries = {
            'cpu_usage': '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'memory_usage': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
            'disk_usage': '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
            'request_latency': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            'error_rate': 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
            'db_connections': 'pg_stat_activity_count',
        }
        
        for name, query in queries.items():
            try:
                result = self.prom.custom_query(query=query)
                if result and len(result) > 0:
                    metrics[name] = float(result[0]['value'][1])
                else:
                    metrics[name] = 0.0
            except Exception as e:
                logger.warning(f"Ошибка получения метрики {name}: {e}")
                metrics[name] = 0.0
                
        return metrics
    
    async def get_historical_metrics(self, hours: int = 24) -> pd.DataFrame:
        """Получить исторические данные для обучения модели."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        queries = {
            'cpu_usage': '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'memory_usage': '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
            'disk_usage': '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
            'request_latency': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            'error_rate': 'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
        }
        
        all_data = []
        
        for name, query in queries.items():
            try:
                result = self.prom.custom_query_range(
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                    step='1m'
                )
                
                if result and len(result) > 0:
                    for point in result[0]['values']:
                        timestamp, value = point
                        all_data.append({
                            'timestamp': datetime.fromtimestamp(float(timestamp)),
                            'metric': name,
                            'value': float(value) if value != 'NaN' else 0.0
                        })
            except Exception as e:
                logger.warning(f"Ошибка получения истории {name}: {e}")
        
        if not all_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_data)
        df_pivot = df.pivot_table(
            index='timestamp', 
            columns='metric', 
            values='value', 
            aggfunc='first'
        ).reset_index()
        
        return df_pivot.fillna(0)


class AnomalyDetector:
    """ML-модель для обнаружения аномалий."""
    
    def __init__(self):
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: List[str] = [
            'cpu_usage', 'memory_usage', 'disk_usage', 
            'request_latency', 'error_rate'
        ]
        self.contamination = 0.05  # Ожидаемый % аномалий
        
    def train(self, data: pd.DataFrame) -> bool:
        """Обучить модель на исторических данных."""
        try:
            if data.empty or len(data) < 100:
                logger.warning("Недостаточно данных для обучения")
                return False
            
            # Подготовка признаков
            features = []
            for col in self.feature_names:
                if col in data.columns:
                    features.append(data[col].values)
                else:
                    features.append(np.zeros(len(data)))
            
            X = np.column_stack(features)
            
            # Масштабирование
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Обучение Isolation Forest
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100,
                max_samples='auto',
                n_jobs=-1
            )
            self.model.fit(X_scaled)
            
            # Сохранение модели
            self._save_model()
            
            logger.info(f"Модель обучена на {len(data)} образцах")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обучения модели: {e}")
            return False
    
    def predict(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Предсказать аномалию для текущих метрик."""
        if self.model is None or self.scaler is None:
            self._load_model()
            
        if self.model is None:
            return {
                'is_anomaly': False,
                'score': 0,
                'message': 'Модель не обучена'
            }
        
        try:
            # Подготовка признаков
            features = []
            for col in self.feature_names:
                features.append(metrics.get(col, 0.0))
            
            X = np.array(features).reshape(1, -1)
            X_scaled = self.scaler.transform(X)
            
            # Предсказание
            prediction = self.model.predict(X_scaled)[0]
            score = self.model.score_samples(X_scaled)[0]
            
            is_anomaly = prediction == -1
            
            # Анализ что именно аномально
            anomaly_details = []
            if is_anomaly:
                for i, (name, value) in enumerate(zip(self.feature_names, features)):
                    # Простая эвристика для определения проблемной метрики
                    if name == 'cpu_usage' and value > 80:
                        anomaly_details.append(f"🔥 CPU: {value:.1f}%")
                    if name == 'memory_usage' and value > 85:
                        anomaly_details.append(f"💾 Memory: {value:.1f}%")
                    if name == 'disk_usage' and value > 90:
                        anomaly_details.append(f"💿 Disk: {value:.1f}%")
                    if name == 'request_latency' and value > 1.0:
                        anomaly_details.append(f"⏱️ Latency: {value:.2f}s")
                    if name == 'error_rate' and value > 5:
                        anomaly_details.append(f"❌ Error rate: {value:.1f}%")
            
            return {
                'is_anomaly': is_anomaly,
                'score': float(score),
                'details': anomaly_details,
                'metrics': metrics,
                'message': 'Обнаружена аномалия!' if is_anomaly else 'Всё в норме'
            }
            
        except Exception as e:
            logger.error(f"Ошибка предсказания: {e}")
            return {
                'is_anomaly': False,
                'score': 0,
                'message': f'Ошибка: {e}'
            }
    
    def _save_model(self):
        """Сохранить модель на диск."""
        os.makedirs(MODEL_PATH, exist_ok=True)
        joblib.dump(self.model, f'{MODEL_PATH}/anomaly_model.joblib')
        joblib.dump(self.scaler, f'{MODEL_PATH}/scaler.joblib')
        logger.info("Модель сохранена")
    
    def _load_model(self):
        """Загрузить модель с диска."""
        try:
            model_file = f'{MODEL_PATH}/anomaly_model.joblib'
            scaler_file = f'{MODEL_PATH}/scaler.joblib'
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                self.model = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                logger.info("Модель загружена")
            else:
                logger.warning("Файлы модели не найдены")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")


class AlertSender:
    """Отправка алертов."""
    
    def __init__(self):
        self.telegram_token = TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = TELEGRAM_CHAT_ID
        self.alertmanager_url = ALERTMANAGER_URL
        
    async def send_telegram(self, message: str):
        """Отправить уведомление в Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram не настроен")
            return
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json={
                    'chat_id': self.telegram_chat_id,
                    'text': message,
                    'parse_mode': 'HTML'
                })
                logger.info("Telegram уведомление отправлено")
            except Exception as e:
                logger.error(f"Ошибка отправки в Telegram: {e}")
    
    async def send_alertmanager(self, alert: Dict[str, Any]):
        """Отправить алерт в Alertmanager."""
        url = f"{self.alertmanager_url}/api/v2/alerts"
        
        alert_data = [{
            'labels': {
                'alertname': 'AnomalyDetected',
                'severity': 'warning',
                'source': 'ml-detector'
            },
            'annotations': {
                'summary': alert.get('message', 'Anomaly detected'),
                'description': json.dumps(alert.get('details', []))
            }
        }]
        
        async with httpx.AsyncClient() as client:
            try:
                await client.post(url, json=alert_data)
                logger.info("Alertmanager уведомление отправлено")
            except Exception as e:
                logger.error(f"Ошибка отправки в Alertmanager: {e}")


class AnomalyDetectionService:
    """Основной сервис детекции аномалий."""
    
    def __init__(self):
        self.collector = MetricsCollector(PROMETHEUS_URL)
        self.detector = AnomalyDetector()
        self.alerter = AlertSender()
        self.scheduler = AsyncIOScheduler()
        self.last_anomaly_time: Optional[datetime] = None
        self.cooldown_minutes = 15  # Минимум между алертами
        
    async def train_model(self):
        """Переобучить модель на свежих данных."""
        logger.info("Начало обучения модели...")
        
        data = await self.collector.get_historical_metrics(hours=TRAINING_HOURS)
        
        if self.detector.train(data):
            logger.info("Модель успешно переобучена")
        else:
            logger.warning("Не удалось обучить модель")
    
    async def check_anomalies(self):
        """Проверить текущие метрики на аномалии."""
        try:
            metrics = await self.collector.get_current_metrics()
            result = self.detector.predict(metrics)
            
            if result['is_anomaly']:
                # Проверка cooldown
                now = datetime.now()
                if self.last_anomaly_time:
                    elapsed = (now - self.last_anomaly_time).total_seconds() / 60
                    if elapsed < self.cooldown_minutes:
                        logger.info(f"Cooldown активен ({elapsed:.1f} мин)")
                        return
                
                self.last_anomaly_time = now
                
                # Формирование сообщения
                message = self._format_alert_message(result)
                
                # Отправка алертов
                await self.alerter.send_telegram(message)
                await self.alerter.send_alertmanager(result)
                
                logger.warning(f"Аномалия обнаружена: {result['details']}")
            else:
                logger.debug("Метрики в норме")
                
        except Exception as e:
            logger.error(f"Ошибка проверки аномалий: {e}")
    
    def _format_alert_message(self, result: Dict[str, Any]) -> str:
        """Форматирование сообщения для Telegram."""
        details = result.get('details', [])
        metrics = result.get('metrics', {})
        score = result.get('score', 0)
        
        message = "🚨 <b>ML Anomaly Detection Alert</b>\n\n"
        message += f"⚠️ Anomaly Score: {abs(score):.3f}\n\n"
        
        if details:
            message += "<b>Проблемные метрики:</b>\n"
            for detail in details:
                message += f"  {detail}\n"
            message += "\n"
        
        message += "<b>Все метрики:</b>\n"
        for name, value in metrics.items():
            message += f"  • {name}: {value:.2f}\n"
        
        message += f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message
    
    async def run(self):
        """Запуск сервиса."""
        logger.info("Запуск Anomaly Detection Service...")
        
        # Первоначальное обучение
        await self.train_model()
        
        # Планировщик задач
        self.scheduler.add_job(
            self.check_anomalies,
            'interval',
            seconds=DETECTION_INTERVAL,
            id='check_anomalies'
        )
        
        # Переобучение каждые 6 часов
        self.scheduler.add_job(
            self.train_model,
            'interval',
            hours=6,
            id='retrain_model'
        )
        
        self.scheduler.start()
        
        logger.info(f"Сервис запущен. Проверка каждые {DETECTION_INTERVAL} сек")
        
        # Держим сервис запущенным
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Остановка сервиса...")
            self.scheduler.shutdown()


# Health check endpoint
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Подавляем логи HTTP


def run_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthHandler)
    server.serve_forever()


if __name__ == '__main__':
    # Запуск health check в отдельном потоке
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Запуск основного сервиса
    service = AnomalyDetectionService()
    asyncio.run(service.run())
