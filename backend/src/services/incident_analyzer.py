"""
AI-агент для анализа инцидентов.

Использует LLM для:
- Классификации проблемы (bug, feature, question, etc.)
- Определения приоритета
- Поиска похожих решённых инцидентов (через embeddings)
- Генерации автоматического ответа/решения
- Извлечения ключевых слов и тегов
"""
import os
import hashlib
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.incident import (
    Incident, IncidentLog, IncidentSolution, IncidentEmbedding,
    IncidentCategory, IncidentPriority
)

# Конфигурация AI провайдеров
AI_PROVIDERS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "embedding_model": "text-embedding-3-small",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-3-haiku",
        "embedding_model": None,  # Использовать OpenAI для embeddings
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "embedding_model": None,
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-1.5-flash",
        "embedding_model": "text-embedding-004",
    }
}


class IncidentAnalyzer:
    """AI-агент для анализа инцидентов."""
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ):
        self.provider = provider
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY") or os.getenv("LLM_API_KEY")
        self.db = db
        
        if provider not in AI_PROVIDERS:
            raise ValueError(f"Unknown AI provider: {provider}")
        
        self.config = AI_PROVIDERS[provider]
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def close(self):
        """Закрытие HTTP клиента."""
        await self.client.aclose()
    
    async def _chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> str:
        """Вызов LLM для chat completion."""
        if not self.api_key:
            # Fallback на keyword-based анализ
            return ""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = os.getenv("FRONTEND_URL", "https://sattva-streamer.top")
            headers["X-Title"] = "Sattva Streamer Support"
        
        payload = {
            "model": self.config["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            if self.provider == "gemini":
                # Gemini API имеет другой формат
                return await self._gemini_completion(messages, temperature, max_tokens)
            
            response = await self.client.post(
                f"{self.config['base_url']}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"AI completion error: {e}")
            return ""
    
    async def _gemini_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Специфичный вызов для Gemini API."""
        # Конвертируем формат сообщений
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        response = await self.client.post(
            f"{self.config['base_url']}/models/{self.config['model']}:generateContent?key={self.api_key}",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Получение embedding для текста."""
        if not self.api_key:
            return None
        
        # Для провайдеров без embeddings используем OpenAI
        embedding_provider = self.provider if self.config["embedding_model"] else "openai"
        embedding_config = AI_PROVIDERS.get(embedding_provider, AI_PROVIDERS["openai"])
        
        if not embedding_config["embedding_model"]:
            return None
        
        api_key = self.api_key if embedding_provider == self.provider else os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            if embedding_provider == "gemini":
                response = await self.client.post(
                    f"{embedding_config['base_url']}/models/{embedding_config['embedding_model']}:embedContent?key={api_key}",
                    json={
                        "model": f"models/{embedding_config['embedding_model']}",
                        "content": {"parts": [{"text": text}]}
                    }
                )
                response.raise_for_status()
                return response.json()["embedding"]["values"]
            else:
                response = await self.client.post(
                    f"{embedding_config['base_url']}/embeddings",
                    headers=headers,
                    json={
                        "model": embedding_config["embedding_model"],
                        "input": text
                    }
                )
                response.raise_for_status()
                return response.json()["data"][0]["embedding"]
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
    
    async def analyze_incident(self, incident: Incident) -> Dict[str, Any]:
        """
        Полный анализ инцидента.
        
        Returns:
            {
                "category": IncidentCategory,
                "priority": IncidentPriority,
                "suggested_solution": str | None,
                "confidence": float,
                "similar_incidents": List[dict],
                "tags": List[str],
                "summary": str
            }
        """
        # Собираем контекст
        logs_summary = await self._summarize_logs(incident)
        
        # Формируем промпт для анализа
        system_prompt = """Ты — AI-агент поддержки платформы Sattva Streamer (музыкальный стриминг).
Проанализируй обращение пользователя и определи:
1. Категорию проблемы
2. Приоритет
3. Ключевые теги
4. Краткое резюме
5. Возможное решение (если очевидно)

Категории:
- bug: ошибка в работе системы
- feature: запрос новой функции
- question: вопрос по использованию
- performance: проблемы производительности
- security: проблемы безопасности
- ui_ux: проблемы интерфейса
- other: прочее

Приоритеты:
- critical: система неработоспособна, затрагивает многих
- high: серьёзная проблема, блокирует работу
- medium: умеренная проблема
- low: косметическая проблема или пожелание

Ответ в JSON формате:
{
  "category": "bug|feature|question|performance|security|ui_ux|other",
  "priority": "critical|high|medium|low",
  "tags": ["tag1", "tag2"],
  "summary": "Краткое описание проблемы",
  "solution": "Предложенное решение или null",
  "confidence": 0.0-1.0
}"""

        user_message = f"""Заголовок: {incident.title}

Описание: {incident.description}

Браузер: {incident.browser_info.get('name', 'Unknown')} {incident.browser_info.get('version', '')}
ОС: {incident.browser_info.get('os', 'Unknown')}
Страница: {incident.page_url}

Логи:
{logs_summary}"""

        # Вызываем LLM
        response = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ])
        
        # Парсим ответ
        result = self._parse_ai_response(response, incident)
        
        # Поиск похожих инцидентов через embeddings
        if self.db:
            result["similar_incidents"] = await self._find_similar_incidents(incident)
            
            # Если есть похожий решённый инцидент, используем его решение
            if result["similar_incidents"] and not result["suggested_solution"]:
                best_match = result["similar_incidents"][0]
                if best_match.get("similarity", 0) > 0.7 and best_match.get("solution"):
                    result["suggested_solution"] = best_match["solution"]
                    result["confidence"] = min(result["confidence"] + 0.2, 1.0)
        
        return result
    
    async def _summarize_logs(self, incident: Incident) -> str:
        """Суммаризация логов инцидента."""
        if not incident.logs:
            return "Логи отсутствуют"
        
        errors = []
        network_errors = []
        actions = []
        
        for log in incident.logs[-50:]:  # Последние 50 логов
            if log.log_type == "console" and log.level == "error":
                errors.append(f"- {log.message[:200]}")
            elif log.log_type == "network" and (log.status_code and log.status_code >= 400):
                network_errors.append(f"- {log.method} {log.url} -> {log.status_code}")
            elif log.log_type == "action":
                actions.append(f"- {log.action}: {log.element or ''}")
        
        summary_parts = []
        
        if errors:
            summary_parts.append(f"Console ошибки ({len(errors)}):\n" + "\n".join(errors[:5]))
        if network_errors:
            summary_parts.append(f"Network ошибки ({len(network_errors)}):\n" + "\n".join(network_errors[:5]))
        if actions:
            summary_parts.append(f"Последние действия:\n" + "\n".join(actions[-10:]))
        
        return "\n\n".join(summary_parts) if summary_parts else "Нет значимых логов"
    
    def _parse_ai_response(self, response: str, incident: Incident) -> Dict[str, Any]:
        """Парсинг ответа AI с fallback на keyword анализ."""
        default_result = self._keyword_analysis(incident)
        
        if not response:
            return default_result
        
        try:
            # Извлекаем JSON из ответа
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start == -1 or json_end == 0:
                return default_result
            
            data = json.loads(response[json_start:json_end])
            
            # Валидация и преобразование
            category_map = {
                "bug": IncidentCategory.BUG,
                "feature": IncidentCategory.FEATURE_REQUEST,
                "question": IncidentCategory.QUESTION,
                "performance": IncidentCategory.PERFORMANCE,
                "security": IncidentCategory.SECURITY,
                "ui_ux": IncidentCategory.UI_UX,
                "other": IncidentCategory.OTHER,
            }
            
            priority_map = {
                "critical": IncidentPriority.CRITICAL,
                "high": IncidentPriority.HIGH,
                "medium": IncidentPriority.MEDIUM,
                "low": IncidentPriority.LOW,
            }
            
            return {
                "category": category_map.get(data.get("category", "other"), IncidentCategory.OTHER),
                "priority": priority_map.get(data.get("priority", "medium"), IncidentPriority.MEDIUM),
                "tags": data.get("tags", [])[:10],
                "summary": data.get("summary", ""),
                "suggested_solution": data.get("solution"),
                "confidence": min(max(float(data.get("confidence", 0.7)), 0.0), 1.0),
                "similar_incidents": []
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"AI response parsing error: {e}")
            return default_result
    
    def _keyword_analysis(self, incident: Incident) -> Dict[str, Any]:
        """Fallback анализ на основе ключевых слов."""
        text = f"{incident.title} {incident.description}".lower()
        
        # Категория
        category = IncidentCategory.OTHER
        if any(w in text for w in ["ошибка", "error", "баг", "bug", "не работает", "сломал", "падает"]):
            category = IncidentCategory.BUG
        elif any(w in text for w in ["медленно", "тормоз", "долго", "slow", "performance", "лаг"]):
            category = IncidentCategory.PERFORMANCE
        elif any(w in text for w in ["хочу", "добавить", "функция", "feature", "можно ли", "было бы"]):
            category = IncidentCategory.FEATURE_REQUEST
        elif any(w in text for w in ["как", "почему", "зачем", "what", "how", "why", "?"]):
            category = IncidentCategory.QUESTION
        elif any(w in text for w in ["интерфейс", "ui", "ux", "дизайн", "кнопка", "меню", "внешний вид"]):
            category = IncidentCategory.UI_UX
        elif any(w in text for w in ["безопасность", "пароль", "доступ", "security", "взлом"]):
            category = IncidentCategory.SECURITY
        
        # Приоритет
        priority = IncidentPriority.MEDIUM
        error_count = sum(1 for log in incident.logs if getattr(log, 'level', None) == "error")
        
        if error_count > 5 or any(w in text for w in ["критично", "urgent", "срочно", "не могу войти", "всё сломалось"]):
            priority = IncidentPriority.CRITICAL
        elif error_count > 2 or any(w in text for w in ["важно", "блокирует", "не могу работать"]):
            priority = IncidentPriority.HIGH
        elif any(w in text for w in ["мелочь", "хотелось бы", "было бы неплохо", "не критично"]):
            priority = IncidentPriority.LOW
        
        # Теги
        tags = []
        tag_keywords = {
            "audio": ["звук", "audio", "музыка", "плеер", "воспроизведение"],
            "playlist": ["плейлист", "playlist", "список", "треки"],
            "schedule": ["расписание", "schedule", "время", "слоты"],
            "auth": ["авторизация", "login", "вход", "регистрация", "пароль"],
            "ui": ["интерфейс", "кнопка", "меню", "дизайн", "отображение"],
            "mobile": ["телефон", "mobile", "android", "ios", "мобильный"],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)
        
        return {
            "category": category,
            "priority": priority,
            "tags": tags[:10],
            "summary": incident.title,
            "suggested_solution": None,
            "confidence": 0.5,
            "similar_incidents": []
        }
    
    async def _find_similar_incidents(self, incident: Incident) -> List[Dict[str, Any]]:
        """Поиск похожих инцидентов через embeddings или текстовый поиск."""
        if not self.db:
            return []
        
        # Получаем embedding для текущего инцидента
        incident_text = f"{incident.title} {incident.description}"
        embedding = await self._get_embedding(incident_text)
        
        if embedding:
            # Векторный поиск
            return await self._vector_search(embedding, incident.id)
        else:
            # Fallback на текстовый поиск
            return await self._text_search(incident)
    
    async def _vector_search(
        self,
        embedding: List[float],
        exclude_id: Any
    ) -> List[Dict[str, Any]]:
        """Векторный поиск похожих инцидентов."""
        # TODO: Реализовать pgvector поиск
        # SELECT * FROM incident_embeddings
        # ORDER BY embedding <-> $1
        # LIMIT 5
        return []
    
    async def _text_search(self, incident: Incident) -> List[Dict[str, Any]]:
        """Текстовый поиск похожих решений."""
        query = select(IncidentSolution).where(
            IncidentSolution.is_active == True
        ).limit(10)
        
        result = await self.db.execute(query)
        solutions = result.scalars().all()
        
        # Простое сравнение по словам
        incident_words = set(incident.title.lower().split())
        similar = []
        
        for solution in solutions:
            solution_words = set(f"{solution.problem_title} {solution.problem_description}".lower().split())
            common = incident_words & solution_words
            
            if len(common) >= 2:
                similarity = len(common) / max(len(incident_words), 1)
                similar.append({
                    "id": str(solution.source_incident_id or solution.id),
                    "title": solution.problem_title,
                    "status": "resolved",
                    "similarity": min(similarity, 0.95),
                    "solution": solution.solution
                })
        
        # Сортируем по схожести
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:3]
    
    async def generate_auto_response(
        self,
        incident: Incident,
        solution: Optional[str] = None
    ) -> str:
        """Генерация автоматического ответа для пользователя."""
        if not self.api_key:
            return self._generate_template_response(incident, solution)
        
        system_prompt = """Ты — дружелюбный AI-ассистент поддержки Sattva Streamer.
Сгенерируй краткий и полезный ответ пользователю на его обращение.
Будь вежлив, используй эмодзи умеренно.
Если есть решение — предложи его.
Если решения нет — уточни детали или пообещай, что команда разберётся."""

        user_message = f"""Обращение: {incident.title}
Описание: {incident.description}

Найденное решение: {solution or 'Не найдено'}

Сгенерируй ответ пользователю (2-4 предложения)."""

        response = await self._chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ], temperature=0.7)
        
        return response or self._generate_template_response(incident, solution)
    
    def _generate_template_response(
        self,
        incident: Incident,
        solution: Optional[str] = None
    ) -> str:
        """Шаблонный ответ если AI недоступен."""
        if solution:
            return f"""👋 Спасибо за обращение!

Мы нашли возможное решение вашей проблемы:

{solution}

Если это не помогло, мы свяжемся с вами в ближайшее время.

С уважением,
Команда Sattva Streamer"""
        else:
            return """👋 Спасибо за обращение!

Мы получили ваш запрос и уже работаем над ним. 
Наша команда свяжется с вами в ближайшее время.

Номер обращения: #{incident_id}

С уважением,
Команда Sattva Streamer""".format(incident_id=str(incident.id)[:8])
    
    async def create_embedding_for_incident(self, incident: Incident) -> Optional[str]:
        """Создание и сохранение embedding для инцидента."""
        if not self.db:
            return None
        
        text = f"{incident.title} {incident.description}"
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Проверяем, есть ли уже embedding
        existing = await self.db.execute(
            select(IncidentEmbedding).where(
                IncidentEmbedding.incident_id == incident.id,
                IncidentEmbedding.text_hash == text_hash
            )
        )
        if existing.scalar_one_or_none():
            return text_hash
        
        # Получаем embedding
        embedding = await self._get_embedding(text)
        if not embedding:
            return None
        
        # Сохраняем
        incident_embedding = IncidentEmbedding(
            incident_id=incident.id,
            embedding=embedding,
            text_hash=text_hash
        )
        self.db.add(incident_embedding)
        await self.db.commit()
        
        return text_hash


# Фабрика для создания анализатора
def get_incident_analyzer(
    db: Optional[AsyncSession] = None
) -> IncidentAnalyzer:
    """Создание экземпляра анализатора с автоопределением провайдера."""
    # Приоритет провайдеров
    providers = ["openai", "openrouter", "deepseek", "gemini"]
    
    for provider in providers:
        api_key = os.getenv(f"{provider.upper()}_API_KEY")
        if api_key:
            return IncidentAnalyzer(provider=provider, api_key=api_key, db=db)
    
    # Fallback на keyword-based анализ
    return IncidentAnalyzer(provider="openai", db=db)


async def get_incident_analyzer_async(
    db: AsyncSession
) -> IncidentAnalyzer:
    """
    Асинхронная фабрика для создания анализатора.
    Получает API ключи из БД (app_settings) с fallback на .env.
    """
    from src.services.settings_service import get_ai_api_key, get_active_ai_provider
    
    # Получаем активный провайдер и ключ из настроек (БД + .env fallback)
    provider = await get_active_ai_provider(db)
    
    if provider:
        api_key = await get_ai_api_key(db, provider)
        if api_key:
            return IncidentAnalyzer(provider=provider, api_key=api_key, db=db)
    
    # Fallback на keyword-based анализ
    return IncidentAnalyzer(provider="openai", db=db)
