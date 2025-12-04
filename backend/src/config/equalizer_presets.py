"""
Equalizer Presets Configuration

Конфигурация пресетов для 10-полосного эквалайзера (GStreamer equalizer-10bands).

Частотные полосы (Hz):
0: 29, 1: 59, 2: 119, 3: 237, 4: 474, 5: 947, 6: 1889, 7: 3770, 8: 7523, 9: 15011

Значения в dB: от -24 до +12 (рекомендуемый диапазон: -6 до +6)
"""

from typing import Dict, List
from dataclasses import dataclass


@dataclass
class EqualizerPreset:
    """
    Пресет эквалайзера.
    
    Attributes:
        name: Название пресета
        display_name: Отображаемое название (русское)
        description: Описание звучания
        bands: Массив из 10 значений (в dB) для каждой частотной полосы
        category: Категория пресета (standard, meditation)
    """
    name: str
    display_name: str
    description: str
    bands: List[float]
    category: str = "standard"
    
    def __post_init__(self):
        """Валидация пресета."""
        if len(self.bands) != 10:
            raise ValueError(f"Equalizer preset must have exactly 10 bands, got {len(self.bands)}")
        
        for i, value in enumerate(self.bands):
            if not -24 <= value <= 12:
                raise ValueError(
                    f"Band {i} value {value} out of range [-24, 12]. "
                    f"Recommended range: [-6, 6]"
                )


# Стандартные пресеты (из YukkiMusicBot)
STANDARD_PRESETS = {
    "flat": EqualizerPreset(
        name="flat",
        display_name="Плоский",
        description="Без обработки, исходный звук",
        bands=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        category="standard"
    ),
    
    "rock": EqualizerPreset(
        name="rock",
        display_name="Рок",
        description="Усиленные низкие и высокие частоты для рок-музыки",
        bands=[5, 4, 3, 2, -1, -1, 0, 2, 3, 4],
        category="standard"
    ),
    
    "jazz": EqualizerPreset(
        name="jazz",
        display_name="Джаз",
        description="Сбалансированный звук с акцентом на средних частотах",
        bands=[4, 3, 1, 2, -1, -1, 0, 1, 2, 3],
        category="standard"
    ),
    
    "classical": EqualizerPreset(
        name="classical",
        display_name="Классика",
        description="Широкий динамический диапазон для классической музыки",
        bands=[5, 4, 3, 2, -1, -2, 0, 2, 3, 4],
        category="standard"
    ),
    
    "voice": EqualizerPreset(
        name="voice",
        display_name="Голос",
        description="Акцент на вокальном диапазоне (средние частоты)",
        bands=[-2, -1, 0, 3, 5, 5, 4, 2, 0, -2],
        category="standard"
    ),
    
    "bass_boost": EqualizerPreset(
        name="bass_boost",
        display_name="Усиление баса",
        description="Усиленные низкие частоты",
        bands=[6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
        category="standard"
    ),
}


# Пресеты для медитации и релаксации (Sattva-specific)
MEDITATION_PRESETS = {
    "meditation": EqualizerPreset(
        name="meditation",
        display_name="Медитация",
        description="Мягкие низкие + легкие высокие, убраны средние частоты",
        bands=[3, 2, 1, 0, -1, -2, -1, 0, 1, 2],
        category="meditation"
    ),
    
    "relax": EqualizerPreset(
        name="relax",
        display_name="Релаксация",
        description="Теплый звук, усиленный бас, мягкие высокие",
        bands=[2, 3, 2, 1, 0, -1, -1, 0, 1, 1],
        category="meditation"
    ),
    
    "new_age": EqualizerPreset(
        name="new_age",
        display_name="New Age",
        description="Космический звук: бас + высокие, провал средних",
        bands=[4, 3, 2, 0, -2, -2, 0, 2, 3, 4],
        category="meditation"
    ),
    
    "ambient": EqualizerPreset(
        name="ambient",
        display_name="Эмбиент",
        description="Атмосферный: широкий звук с акцентом на низкие/высокие",
        bands=[3, 4, 3, 1, -1, -2, -1, 1, 2, 3],
        category="meditation"
    ),
    
    "sleep": EqualizerPreset(
        name="sleep",
        display_name="Сон",
        description="Максимально мягкий: убраны средние и высокие частоты",
        bands=[2, 2, 1, 0, -1, -2, -2, -1, 0, 0],
        category="meditation"
    ),
    
    "nature": EqualizerPreset(
        name="nature",
        display_name="Природа",
        description="Естественный: ровный с легким подъёмом",
        bands=[1, 2, 2, 1, 0, 0, 1, 2, 2, 1],
        category="meditation"
    ),
}


# Объединенный словарь всех пресетов
EQUALIZER_PRESETS: Dict[str, EqualizerPreset] = {
    **STANDARD_PRESETS,
    **MEDITATION_PRESETS,
}


# Константы для UI
PRESET_CATEGORIES = {
    "standard": "Стандартные",
    "meditation": "Медитация и релаксация",
}


DEFAULT_PRESET = "flat"


def get_preset(name: str) -> EqualizerPreset:
    """
    Получить пресет по имени.
    
    Args:
        name: Название пресета
        
    Returns:
        EqualizerPreset объект
        
    Raises:
        KeyError: Если пресет не найден
    """
    if name not in EQUALIZER_PRESETS:
        raise KeyError(
            f"Unknown equalizer preset: {name}. "
            f"Available presets: {', '.join(EQUALIZER_PRESETS.keys())}"
        )
    
    return EQUALIZER_PRESETS[name]


def get_preset_bands(name: str) -> List[float]:
    """
    Получить массив значений частотных полос для пресета.
    
    Args:
        name: Название пресета
        
    Returns:
        Список из 10 значений (dB) для каждой полосы
    """
    return get_preset(name).bands


def list_presets_by_category() -> Dict[str, List[str]]:
    """Вернуть имена пресетов, сгруппированные по категориям."""

    result: Dict[str, List[str]] = {}
    for preset_name, preset in EQUALIZER_PRESETS.items():
        result.setdefault(preset.category, []).append(preset_name)

    for category in result:
        result[category].sort()

    return result


def list_presets_with_metadata() -> List[dict]:
    """Вернуть сериализованный список всех пресетов с описанием."""

    serialized: List[dict] = []
    for preset in EQUALIZER_PRESETS.values():
        serialized.append(
            {
                "name": preset.name,
                "display_name": preset.display_name,
                "description": preset.description,
                "category": preset.category,
                "bands": preset.bands,
            }
        )
    return serialized


def list_presets_grouped_with_metadata() -> Dict[str, List[dict]]:
    """Вернуть пресеты с метаданными, сгруппированные по категориям."""

    grouped: Dict[str, List[dict]] = {}
    for preset in EQUALIZER_PRESETS.values():
        grouped.setdefault(preset.category, []).append(
            {
                "name": preset.name,
                "display_name": preset.display_name,
                "description": preset.description,
                "category": preset.category,
                "bands": preset.bands,
            }
        )

    for category in grouped:
        grouped[category].sort(key=lambda item: item["display_name"])

    return grouped


def validate_custom_bands(bands: List[float]) -> bool:
    """
    Валидировать кастомные значения частотных полос.
    
    Args:
        bands: Массив из 10 значений
        
    Returns:
        True если валидны
        
    Raises:
        ValueError: Если значения невалидны
    """
    if len(bands) != 10:
        raise ValueError(f"Expected 10 bands, got {len(bands)}")
    
    for i, value in enumerate(bands):
        if not isinstance(value, (int, float)):
            raise ValueError(f"Band {i} must be numeric, got {type(value)}")
        
        if not -24 <= value <= 12:
            raise ValueError(
                f"Band {i} value {value} out of range [-24, 12]. "
                f"Recommended range: [-6, 6]"
            )
    
    return True


# Информация о частотных полосах для UI/documentation
BAND_FREQUENCIES = [
    {"index": 0, "frequency": 29, "label": "29 Hz"},
    {"index": 1, "frequency": 59, "label": "59 Hz"},
    {"index": 2, "frequency": 119, "label": "119 Hz"},
    {"index": 3, "frequency": 237, "label": "237 Hz"},
    {"index": 4, "frequency": 474, "label": "474 Hz"},
    {"index": 5, "frequency": 947, "label": "947 Hz"},
    {"index": 6, "frequency": 1889, "label": "1.9 kHz"},
    {"index": 7, "frequency": 3770, "label": "3.8 kHz"},
    {"index": 8, "frequency": 7523, "label": "7.5 kHz"},
    {"index": 9, "frequency": 15011, "label": "15 kHz"},
]



