"""
EdgeLocation Value Object для CDN edge локаций (Feature 024).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: CDN routing service, health monitoring, geolocation.
"""

from dataclasses import dataclass
from typing import Optional

from src.domain.errors import ValidationError
from src.shared.kernel.result import Result
from src.shared.kernel.value_object import ValueObject


@dataclass(frozen=True)
class EdgeLocation(ValueObject):
    """
    Географическая локация edge узла CDN.

    **Validation**:
    - Код города не пустой (IATA код: 3 буквы)
    - Название города не пустое
    - Широта и долгота в валидных диапазонах
    - Страна не пустая

    Examples:
        >>> location = EdgeLocation(
        ...     code="AMS",
        ...     city="Amsterdam",
        ...     country="Netherlands",
        ...     region="Europe",
        ...     latitude=52.3676,
        ...     longitude=4.9041,
        ...     active=True
        ... )
        >>> location.code
        'AMS'
    """

    code: str  # IATA код города (например, AMS, JFK, NRT)
    city: str  # Название города
    country: str  # Название страны
    region: str  # Регион (Europe, Asia, North America, etc.)
    latitude: float  # Широта (-90 to 90)
    longitude: float  # Долгота (-180 to 180)
    active: bool = True  # Активна ли локация

    def __post_init__(self):
        """Валидация локации при создании."""
        if not self._is_valid(self.code, self.city, self.country, self.latitude, self.longitude):
            raise ValidationError(
                f"Invalid EdgeLocation: code={self.code}, city={self.city}, "
                f"country={self.country}, lat={self.latitude}, lon={self.longitude}"
            )

    @staticmethod
    def _is_valid(
        code: str,
        city: str,
        country: str,
        latitude: float,
        longitude: float
    ) -> bool:
        """
        Проверяет валидность локации.

        **Rules**:
        - Code: 3 символа, все заглавные буквы
        - City: не пустой
        - Country: не пустой
        - Latitude: -90 to 90
        - Longitude: -180 to 180
        """
        if not code or not isinstance(code, str):
            return False
        if len(code) != 3 or not code.isupper():
            return False
        if not city or not isinstance(city, str):
            return False
        if not country or not isinstance(country, str):
            return False
        if not isinstance(latitude, (int, float)):
            return False
        if not isinstance(longitude, (int, float)):
            return False
        if latitude < -90 or latitude > 90:
            return False
        if longitude < -180 or longitude > 180:
            return False
        return True

    @staticmethod
    def create(
        code: str,
        city: str,
        country: str,
        region: str,
        latitude: float,
        longitude: float,
        active: bool = True
    ) -> Result["EdgeLocation", ValidationError]:
        """
        Factory method с Result pattern для безопасного создания EdgeLocation.

        Args:
            code: IATA код города (3 символа)
            city: Название города
            country: Название страны
            region: Регион
            latitude: Широта
            longitude: Долгота
            active: Активна ли локация

        Returns:
            Result[EdgeLocation, ValidationError]: Ok(EdgeLocation) или Err(ValidationError)
        """
        if not EdgeLocation._is_valid(code, city, country, latitude, longitude):
            return Result.failure(
                ValidationError(f"Invalid edge location: {city} ({code})")
            )

        return Result.success(
            EdgeLocation(
                code=code.upper(),
                city=city,
                country=country,
                region=region,
                latitude=float(latitude),
                longitude=float(longitude),
                active=active
            )
        )

    def is_in_region(self, region: str) -> bool:
        """Проверяет, находится ли локация в указанном регионе."""
        return self.region.lower() == region.lower()

    def is_in_europe(self) -> bool:
        """True если локация в Европе."""
        return self.is_in_region("Europe")

    def is_in_asia(self) -> bool:
        """True если локация в Азии."""
        return self.is_in_region("Asia")

    def is_in_north_america(self) -> bool:
        """True если локация в Северной Америке."""
        return self.is_in_region("North America")

    def calculate_distance(
        self,
        other_latitude: float,
        other_longitude: float
    ) -> float:
        """
        Вычисляет расстояние до указанной точки в километрах.

        Использует формулу Haversine для расчёта расстояния
        между двумя точками на сфере.

        Args:
            other_latitude: Широта второй точки
            other_longitude: Долгота второй точки

        Returns:
            Расстояние в километрах

        Examples:
            >>> ams = EdgeLocation(
            ...     code="AMS", city="Amsterdam", country="Netherlands",
            ...     region="Europe", latitude=52.3676, longitude=4.9041
            ... )
            >>> lhr = EdgeLocation(
            ...     code="LHR", city="London", country="UK",
            ...     region="Europe", latitude=51.4700, longitude=-0.4543
            ... )
            >>> distance = ams.calculate_distance(lhr.latitude, lhr.longitude)
            >>> round(distance, 1)
            358.6
        """
        import math

        # Конвертация в радианы
        lat1_rad = math.radians(self.latitude)
        lon1_rad = math.radians(self.longitude)
        lat2_rad = math.radians(other_latitude)
        lon2_rad = math.radians(other_longitude)

        # Разности координат
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Формула Haversine
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(lat1_rad) * math.cos(lat2_rad) *
            math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Радиус Земли в километрах
        earth_radius_km = 6371

        return c * earth_radius_km

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return f"EdgeLocation({self.code} - {self.city}, {self.country})"


@dataclass(frozen=True)
class EdgeHealthStatus(ValueObject):
    """
    Статус здоровья edge локации.

    **Attributes**:
    - location: Edge локация
    - status: Статус (healthy, degraded, unhealthy)
    - response_time_ms: Время отклика в миллисекундах
    - last_check: Время последней проверки
    - error: Ошибка если локация нездорова

    Examples:
        >>> status = EdgeHealthStatus(
        ...     location=ams_location,
        ...     status="healthy",
        ...     response_time_ms=45.2
        ... )
    """

    location: EdgeLocation
    status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: float
    last_check: Optional[str] = None  # ISO format datetime string
    error: Optional[str] = None

    def __post_init__(self):
        """Валидация статуса при создании."""
        valid_statuses = ["healthy", "degraded", "unhealthy"]
        if self.status not in valid_statuses:
            raise ValidationError(
                f"Invalid status: {self.status}. Must be one of {valid_statuses}"
            )
        if self.response_time_ms < 0:
            raise ValidationError(
                f"Response time must be non-negative: {self.response_time_ms}"
            )

    def is_healthy(self) -> bool:
        """True если локация здорова."""
        return self.status == "healthy"

    def is_degraded(self) -> bool:
        """True если производительность снижена."""
        return self.status == "degraded"

    def is_unhealthy(self) -> bool:
        """True если локация недоступна."""
        return self.status == "unhealthy"

    def __str__(self) -> str:
        """String representation."""
        return f"EdgeHealthStatus({self.location.code}: {self.status}, {self.response_time_ms}ms)"
