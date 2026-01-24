"""
API routes for rate limit monitoring and management.

Endpoints:
  GET /api/v1/rate-limits/status - Get current rate limit status across all accounts
  GET /api/v1/rate-limits/metrics - Get detailed rate limit metrics and predictions
  GET /api/v1/rate-limits/predictions - Get current rate limit predictions and breach times
  GET /api/v1/rate-limits/accounts - Get account pool status and distribution
  GET /api/v1/rate-limits/queue - Get queue statistics and pending requests
  POST /api/v1/rate-limits/accounts - Add account to multi-account pool
  PUT /api/v1/rate-limits/accounts/{account_id} - Update account status (enable/disable)
  DELETE /api/v1/rate-limits/accounts/{account_id} - Remove account from pool
  PUT /api/v1/rate-limits/settings - Configure alert thresholds and notification preferences
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user
from ...models.user import User
from ...database import get_db
from ...services.rate_limit_queue_service import RateLimitQueueService
from ...services.rate_limit_predictor import RateLimitPredictor
from ...services.multi_account_rate_limiter import MultiAccountRateLimiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/rate-limits", tags=["rate-limits"])


# Request/Response Models

class AccountLimitStatus(BaseModel):
    """Rate limit status for a single account."""
    account_id: str = Field(..., description="Account identifier")
    endpoint_type: str = Field(..., description="Type of API endpoint")
    current_usage: int = Field(..., description="Current request count")
    limit: int = Field(..., description="Rate limit threshold")
    usage_percent: float = Field(..., description="Usage as percentage of limit")
    status: str = Field(..., description="Status: healthy, warning, critical")
    predicted_breach_time: Optional[str] = Field(None, description="Predicted breach time (ISO 8601)")
    time_until_breach_seconds: Optional[int] = Field(None, description="Seconds until limit breach")


class RateLimitStatusResponse(BaseModel):
    """Overall rate limit status across all accounts."""
    overall_status: str = Field(..., description="Overall system status: healthy, warning, critical")
    total_accounts: int = Field(..., description="Total number of accounts in pool")
    active_accounts: int = Field(..., description="Number of active accounts")
    rate_limited_accounts: int = Field(..., description="Number of accounts currently rate-limited")
    accounts: List[AccountLimitStatus] = Field(..., description="Per-account status details")
    timestamp: str = Field(..., description="Status timestamp (ISO 8601)")


class UsageMetrics(BaseModel):
    """Detailed usage metrics for an account."""
    account_id: str = Field(..., description="Account identifier")
    requests_per_minute: float = Field(..., description="Current request rate")
    trend: str = Field(..., description="Trend: increasing, stable, decreasing")
    confidence: float = Field(..., description="Prediction confidence (0.0-1.0)")
    window_start: Optional[str] = Field(None, description="Metrics window start")
    window_end: Optional[str] = Field(None, description="Metrics window end")


class PredictionMetrics(BaseModel):
    """Prediction data for rate limits."""
    endpoint_type: str = Field(..., description="API endpoint type")
    current_usage: int = Field(..., description="Current usage count")
    limit: int = Field(..., description="Rate limit")
    usage_percent: float = Field(..., description="Usage percentage")
    predicted_breach_time: Optional[str] = Field(None, description="Predicted breach time")
    time_until_breach_seconds: Optional[int] = Field(None, description="Seconds until breach")
    trend: str = Field(..., description="Usage trend")
    confidence: float = Field(..., description="Prediction confidence")
    alert_triggered: bool = Field(..., description="Whether alert was triggered")
    is_critical: bool = Field(..., description="Whether usage is critical (≥90%)")


class RateLimitPrediction(BaseModel):
    """Rate limit prediction for a single account and endpoint."""
    account_id: str = Field(..., description="Account identifier")
    endpoint_type: str = Field(..., description="API endpoint type")
    current_usage: int = Field(..., description="Current usage count")
    limit: int = Field(..., description="Rate limit threshold")
    usage_percent: float = Field(..., description="Usage as percentage of limit")
    predicted_breach_time: Optional[str] = Field(None, description="Predicted breach time (ISO 8601)")
    time_until_breach_seconds: Optional[int] = Field(None, description="Seconds until limit breach")
    trend: str = Field(..., description="Usage trend: increasing, stable, decreasing")
    confidence: float = Field(..., description="Prediction confidence (0.0-1.0)")
    status: str = Field(..., description="Status: healthy, warning, critical")


class RateLimitMetricsResponse(BaseModel):
    """Detailed rate limit metrics and predictions."""
    usage_metrics: List[UsageMetrics] = Field(..., description="Per-account usage metrics")
    predictions: List[PredictionMetrics] = Field(..., description="Rate limit predictions")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    timestamp: str = Field(..., description="Metrics timestamp (ISO 8601)")


class PredictionsResponse(BaseModel):
    """Rate limit predictions for all accounts."""
    predictions: List[RateLimitPrediction] = Field(..., description="Predictions for each account and endpoint type")
    summary: Dict[str, Any] = Field(..., description="Summary statistics including overall status")
    timestamp: str = Field(..., description="Predictions timestamp (ISO 8601)")


class AccountInfo(BaseModel):
    """Information about a single account."""
    account_id: str = Field(..., description="Account identifier")
    status: str = Field(..., description="Account status: active, rate_limited, disabled, failed, banned")
    health: str = Field(..., description="Health state: healthy, degraded, failed, disabled")
    usage_percent: float = Field(..., description="Current usage percentage")
    success_count: int = Field(..., description="Number of successful requests")
    failure_count: int = Field(..., description="Number of failed requests")
    last_used: Optional[str] = Field(None, description="Last usage timestamp (ISO 8601)")


class AccountDistributionResponse(BaseModel):
    """Account pool distribution and status."""
    total_accounts: int = Field(..., description="Total accounts in pool")
    active_accounts: int = Field(..., description="Currently active accounts")
    rate_limited_accounts: int = Field(..., description="Accounts in rate limit")
    disabled_accounts: int = Field(..., description="Disabled accounts")
    failed_accounts: int = Field(..., description="Failed accounts")
    accounts: List[AccountInfo] = Field(..., description="Per-account information")
    selection_strategy: str = Field(..., description="Current account selection strategy")
    timestamp: str = Field(..., description="Response timestamp (ISO 8601)")


class QueueStats(BaseModel):
    """Queue statistics for priority levels."""
    priority_level: str = Field(..., description="Priority level: HIGH, MEDIUM, LOW")
    pending_requests: int = Field(..., description="Number of pending requests")
    processing_requests: int = Field(..., description="Number of requests being processed")
    completed_last_minute: int = Field(..., description="Requests completed in last minute")
    average_wait_time_seconds: float = Field(..., description="Average wait time for requests")


class QueueStatsResponse(BaseModel):
    """Queue statistics and pending requests."""
    total_pending: int = Field(..., description="Total pending requests across all priorities")
    total_processing: int = Field(..., description="Total requests being processed")
    stats_by_priority: List[QueueStats] = Field(..., description="Statistics by priority level")
    batch_size: int = Field(..., description="Current batch size for processing")
    batch_timeout_seconds: int = Field(..., description="Batch timeout in seconds")
    timestamp: str = Field(..., description="Statistics timestamp (ISO 8601)")


class AccountAddRequest(BaseModel):
    """Request to add an account to the pool."""
    account_id: str = Field(..., description="Account identifier (TelegramAccount ID)")
    phone: str = Field(..., description="Phone number associated with the account")


class AccountUpdateRequest(BaseModel):
    """Request to update account status."""
    status: str = Field(..., description="New status: active, disabled, failed")


class AccountOperationResponse(BaseModel):
    """Response for account management operations."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Operation result message")
    account_id: str = Field(..., description="Account identifier")


class AlertThresholds(BaseModel):
    """Alert threshold configuration."""
    warning_threshold_percent: float = Field(default=75.0, ge=0, le=100, description="Warning threshold as percentage (0-100)")
    critical_threshold_percent: float = Field(default=90.0, ge=0, le=100, description="Critical threshold as percentage (0-100)")


class NotificationPreferences(BaseModel):
    """Notification preferences for rate limit alerts."""
    enabled: bool = Field(default=True, description="Whether notifications are enabled")
    channels: List[str] = Field(default_factory=list, description="List of notification channel IDs")
    notify_on_warning: bool = Field(default=True, description="Whether to notify on warning threshold")
    notify_on_critical: bool = Field(default=True, description="Whether to notify on critical threshold")
    cooldown_seconds: int = Field(default=300, ge=0, description="Minimum seconds between notifications for same account")


class RateLimitSettingsRequest(BaseModel):
    """Request to update rate limit settings."""
    alert_thresholds: Optional[AlertThresholds] = Field(None, description="Alert threshold configuration")
    notification_preferences: Optional[NotificationPreferences] = Field(None, description="Notification preferences")


class RateLimitSettingsResponse(BaseModel):
    """Response containing current rate limit settings."""
    alert_thresholds: AlertThresholds = Field(..., description="Current alert thresholds")
    notification_preferences: NotificationPreferences = Field(..., description="Current notification preferences")
    timestamp: str = Field(..., description="Settings timestamp (ISO 8601)")


# Route Handlers

@router.get("/status", response_model=RateLimitStatusResponse, status_code=200)
async def get_rate_limit_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current rate limit status across all accounts.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 60 requests/minute per user (Standard)

    **Returns**:
        - Overall system status (healthy/warning/critical)
        - Account pool statistics
        - Per-account rate limit status
        - Predicted breach times for approaching limits

    **Example Response**:
    ```json
    {
      "overall_status": "healthy",
      "total_accounts": 5,
      "active_accounts": 4,
      "rate_limited_accounts": 1,
      "accounts": [
        {
          "account_id": "account-1",
          "endpoint_type": "messages",
          "current_usage": 45,
          "limit": 60,
          "usage_percent": 75.0,
          "status": "warning",
          "predicted_breach_time": "2025-01-24T12:30:00Z",
          "time_until_breach_seconds": 1200
        }
      ],
      "timestamp": "2025-01-24T12:00:00Z"
    }
    ```
    """
    try:
        # Initialize services
        predictor = RateLimitPredictor()
        multi_account_limiter = MultiAccountRateLimiter(db)

        # Get all accounts from the pool
        accounts = await multi_account_limiter.get_all_accounts()

        if not accounts:
            return RateLimitStatusResponse(
                overall_status="healthy",
                total_accounts=0,
                active_accounts=0,
                rate_limited_accounts=0,
                accounts=[],
                timestamp=_get_timestamp()
            )

        # Get predictions for all accounts
        all_predictions = []
        rate_limited_count = 0
        active_count = 0

        for account in accounts:
            predictions_dict = await predictor.get_predictions(account.account_id)

            # Count accounts by status
            if account.status.value == "active":
                active_count += 1
            elif account.status.value == "rate_limited":
                rate_limited_count += 1

            # Convert prediction dictionaries to response models
            for pred_dict in predictions_dict:
                all_predictions.append(AccountLimitStatus(
                    account_id=pred_dict.get("account_id", account.account_id),
                    endpoint_type=pred_dict.get("endpoint_type", "unknown"),
                    current_usage=pred_dict.get("current_usage", 0),
                    limit=pred_dict.get("limit", 0),
                    usage_percent=pred_dict.get("usage_percent", 0.0),
                    status=_determine_status(pred_dict.get("usage_percent", 0.0)),
                    predicted_breach_time=pred_dict.get("predicted_breach_time"),
                    time_until_breach_seconds=pred_dict.get("time_until_breach_seconds")
                ))

        # Determine overall status
        overall_status = _determine_overall_status(all_predictions)

        logger.info(f"User {current_user.id} retrieved rate limit status for {len(accounts)} accounts")

        return RateLimitStatusResponse(
            overall_status=overall_status,
            total_accounts=len(accounts),
            active_accounts=active_count,
            rate_limited_accounts=rate_limited_count,
            accounts=all_predictions,
            timestamp=_get_timestamp()
        )

    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit status"
        )


@router.get("/metrics", response_model=RateLimitMetricsResponse, status_code=200)
async def get_rate_limit_metrics(
    account_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed rate limit metrics and predictions.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 30 requests/minute per user (Lower limit for expensive queries)

    **Query Parameters**:
    - `account_id`: Optional account ID to filter metrics for specific account

    **Returns**:
        - Usage metrics (requests per minute, trends)
        - Predictions for all endpoint types
        - Confidence scores for predictions
        - Alert triggers status

    **Example Response**:
    ```json
    {
      "usage_metrics": [
        {
          "account_id": "account-1",
          "requests_per_minute": 15.5,
          "trend": "increasing",
          "confidence": 0.85,
          "window_start": "2025-01-24T11:00:00Z",
          "window_end": "2025-01-24T12:00:00Z"
        }
      ],
      "predictions": [
        {
          "endpoint_type": "messages",
          "current_usage": 45,
          "limit": 60,
          "usage_percent": 75.0,
          "predicted_breach_time": "2025-01-24T12:30:00Z",
          "time_until_breach_seconds": 1200,
          "trend": "increasing",
          "confidence": 0.85,
          "alert_triggered": false,
          "is_critical": false
        }
      ],
      "summary": {
        "total_accounts": 5,
        "avg_usage_percent": 65.5,
        "critical_predictions": 0
      },
      "timestamp": "2025-01-24T12:00:00Z"
    }
    ```
    """
    try:
        predictor = RateLimitPredictor()
        multi_account_limiter = MultiAccountRateLimiter(db)

        # Get all accounts
        accounts = await multi_account_limiter.get_all_accounts()
        if account_id:
            accounts = [acc for acc in accounts if acc.account_id == account_id]
            if not accounts:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account {account_id} not found"
                )

        # Collect metrics for all accounts
        usage_metrics_list = []
        all_predictions = []
        total_usage_percent = 0
        critical_count = 0

        for account in accounts:
            # Get usage stats
            stats = await predictor.get_usage_stats(account.account_id)
            for stat in stats:
                usage_metrics_list.append(UsageMetrics(
                    account_id=stat.account_id,
                    requests_per_minute=stat.requests_per_minute,
                    trend=stat.trend,
                    confidence=0.0,  # Confidence is in predictions
                    window_start=stat.window_start.isoformat() if stat.window_start else None,
                    window_end=stat.window_end.isoformat() if stat.window_end else None
                ))

            # Get predictions (returns list of dicts)
            predictions_dict = await predictor.get_predictions(account.account_id)
            for pred_dict in predictions_dict:
                all_predictions.append(PredictionMetrics(**pred_dict))
                total_usage_percent += pred_dict.get("usage_percent", 0.0)
                if pred_dict.get("usage_percent", 0.0) >= 90:
                    critical_count += 1

        # Build summary
        avg_usage = total_usage_percent / len(all_predictions) if all_predictions else 0
        summary = {
            "total_accounts": len(accounts),
            "avg_usage_percent": round(avg_usage, 2),
            "critical_predictions": critical_count,
            "total_predictions": len(all_predictions)
        }

        logger.info(f"User {current_user.id} retrieved rate limit metrics for {len(accounts)} accounts")

        return RateLimitMetricsResponse(
            usage_metrics=usage_metrics_list,
            predictions=all_predictions,
            summary=summary,
            timestamp=_get_timestamp()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rate limit metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit metrics"
        )


@router.get("/predictions", response_model=PredictionsResponse, status_code=200)
async def get_rate_limit_predictions(
    account_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current rate limit predictions and breach times.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 30 requests/minute per user (Lower limit for expensive queries)

    **Query Parameters**:
    - `account_id`: Optional account ID to filter predictions for specific account

    **Returns**:
        - Predicted breach times for all accounts and endpoint types
        - Time until breach in seconds
        - Usage trends and confidence scores
        - Current usage status

    **Example Response**:
    ```json
    {
      "predictions": [
        {
          "account_id": "account-1",
          "endpoint_type": "messages",
          "current_usage": 45,
          "limit": 60,
          "usage_percent": 75.0,
          "predicted_breach_time": "2025-01-24T12:30:00Z",
          "time_until_breach_seconds": 1200,
          "trend": "increasing",
          "confidence": 0.85,
          "status": "warning"
        }
      ],
      "summary": {
        "total_predictions": 5,
        "approaching_limit": 2,
        "critical_predictions": 0,
        "overall_status": "warning"
      },
      "timestamp": "2025-01-24T12:00:00Z"
    }
    ```
    """
    try:
        predictor = RateLimitPredictor()
        multi_account_limiter = MultiAccountRateLimiter(db)

        # Get all accounts
        accounts = await multi_account_limiter.get_all_accounts()
        if account_id:
            accounts = [acc for acc in accounts if acc.account_id == account_id]
            if not accounts:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account {account_id} not found"
                )

        # Collect predictions for all accounts
        all_predictions = []
        approaching_count = 0
        critical_count = 0

        for account in accounts:
            # Get predictions (returns list of dicts)
            predictions_dict = await predictor.get_predictions(account.account_id)
            for pred_dict in predictions_dict:
                usage_percent = pred_dict.get("usage_percent", 0.0)
                status = _determine_status(usage_percent)

                all_predictions.append(RateLimitPrediction(
                    account_id=pred_dict.get("account_id", account.account_id),
                    endpoint_type=pred_dict.get("endpoint_type", "unknown"),
                    current_usage=pred_dict.get("current_usage", 0),
                    limit=pred_dict.get("limit", 0),
                    usage_percent=usage_percent,
                    predicted_breach_time=pred_dict.get("predicted_breach_time"),
                    time_until_breach_seconds=pred_dict.get("time_until_breach_seconds"),
                    trend=pred_dict.get("trend", "stable"),
                    confidence=pred_dict.get("confidence", 0.0),
                    status=status
                ))

                # Count for summary
                if usage_percent >= 75:
                    approaching_count += 1
                if usage_percent >= 90:
                    critical_count += 1

        # Determine overall status
        overall_status = "healthy"
        if critical_count > 0:
            overall_status = "critical"
        elif approaching_count > 0:
            overall_status = "warning"

        # Build summary
        summary = {
            "total_predictions": len(all_predictions),
            "approaching_limit": approaching_count,
            "critical_predictions": critical_count,
            "overall_status": overall_status
        }

        logger.info(f"User {current_user.id} retrieved rate limit predictions for {len(accounts)} accounts")

        return PredictionsResponse(
            predictions=all_predictions,
            summary=summary,
            timestamp=_get_timestamp()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rate limit predictions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit predictions"
        )


@router.get("/accounts", response_model=AccountDistributionResponse, status_code=200)
async def get_account_distribution(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get account pool status and distribution information.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 60 requests/minute per user (Standard)

    **Returns**:
        - Total accounts and their status breakdown
        - Per-account health and usage information
        - Current selection strategy
        - Success/failure counts

    **Example Response**:
    ```json
    {
      "total_accounts": 5,
      "active_accounts": 4,
      "rate_limited_accounts": 1,
      "disabled_accounts": 0,
      "failed_accounts": 0,
      "accounts": [
        {
          "account_id": "account-1",
          "status": "active",
          "health": "healthy",
          "usage_percent": 75.0,
          "success_count": 450,
          "failure_count": 5,
          "last_used": "2025-01-24T12:00:00Z"
        }
      ],
      "selection_strategy": "least_used",
      "timestamp": "2025-01-24T12:00:00Z"
    }
    ```
    """
    try:
        multi_account_limiter = MultiAccountRateLimiter(db)

        # Get all accounts
        accounts = await multi_account_limiter.get_all_accounts()

        accounts_info = []
        active_count = 0
        rate_limited_count = 0
        disabled_count = 0
        failed_count = 0

        for account in accounts:
            # Count by status
            status_value = account.status.value
            if status_value == "active":
                active_count += 1
            elif status_value == "rate_limited":
                rate_limited_count += 1
            elif status_value == "disabled":
                disabled_count += 1
            elif status_value in ["failed", "banned"]:
                failed_count += 1

            # Calculate usage percent from request count
            # Assuming 100 requests per minute as a baseline limit
            usage_percent = min(100.0, (account.request_count / 100.0) * 100) if account.request_count else 0.0

            accounts_info.append(AccountInfo(
                account_id=account.account_id,
                status=status_value,
                health="healthy" if account.is_available else "degraded",
                usage_percent=usage_percent,
                success_count=int(account.request_count * account.success_rate) if account.request_count else 0,
                failure_count=account.failure_count,
                last_used=account.last_used.isoformat() if account.last_used else None
            ))

        # Get selection strategy (it's a property, not a method)
        strategy = multi_account_limiter.selection_strategy

        logger.info(f"User {current_user.id} retrieved account distribution for {len(accounts)} accounts")

        return AccountDistributionResponse(
            total_accounts=len(accounts),
            active_accounts=active_count,
            rate_limited_accounts=rate_limited_count,
            disabled_accounts=disabled_count,
            failed_accounts=failed_count,
            accounts=accounts_info,
            selection_strategy=strategy.value,
            timestamp=_get_timestamp()
        )

    except Exception as e:
        logger.error(f"Error getting account distribution: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve account distribution"
        )


@router.get("/queue", response_model=QueueStatsResponse, status_code=200)
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get queue statistics and pending requests.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 60 requests/minute per user (Standard)

    **Returns**:
        - Total pending and processing requests
        - Statistics by priority level
        - Batch processing configuration
        - Average wait times

    **Example Response**:
    ```json
    {
      "total_pending": 150,
      "total_processing": 5,
      "stats_by_priority": [
        {
          "priority_level": "HIGH",
          "pending_requests": 10,
          "processing_requests": 2,
          "completed_last_minute": 45,
          "average_wait_time_seconds": 0.5
        },
        {
          "priority_level": "MEDIUM",
          "pending_requests": 40,
          "processing_requests": 2,
          "completed_last_minute": 30,
          "average_wait_time_seconds": 2.0
        },
        {
          "priority_level": "LOW",
          "pending_requests": 100,
          "processing_requests": 1,
          "completed_last_minute": 25,
          "average_wait_time_seconds": 5.0
        }
      ],
      "batch_size": 10,
      "batch_timeout_seconds": 5,
      "timestamp": "2025-01-24T12:00:00Z"
    }
    ```
    """
    try:
        queue_service = RateLimitQueueService()

        # Get overall queue statistics
        stats = await queue_service.get_queue_stats()

        # Build stats by priority
        from ...services.rate_limit_queue_service import RequestPriority

        stats_by_priority = [
            QueueStats(
                priority_level="HIGH",
                pending_requests=stats.high_priority,
                processing_requests=0,  # Not tracked separately in current implementation
                completed_last_minute=0,  # Not tracked in current implementation
                average_wait_time_seconds=stats.oldest_request_age if stats.high_priority > 0 else 0.0
            ),
            QueueStats(
                priority_level="MEDIUM",
                pending_requests=stats.medium_priority,
                processing_requests=0,
                completed_last_minute=0,
                average_wait_time_seconds=stats.oldest_request_age if stats.medium_priority > 0 else 0.0
            ),
            QueueStats(
                priority_level="LOW",
                pending_requests=stats.low_priority,
                processing_requests=0,
                completed_last_minute=0,
                average_wait_time_seconds=stats.oldest_request_age if stats.low_priority > 0 else 0.0
            )
        ]

        logger.info(f"User {current_user.id} retrieved queue stats")

        return QueueStatsResponse(
            total_pending=stats.total_requests,
            total_processing=0,  # Not tracked separately in current implementation
            stats_by_priority=stats_by_priority,
            batch_size=queue_service.batch_size,
            batch_timeout_seconds=int(queue_service.batch_timeout),
            timestamp=_get_timestamp()
        )

    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve queue statistics"
        )


@router.post("/accounts", response_model=AccountOperationResponse, status_code=201)
async def add_account_to_pool(
    request: AccountAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an account to the multi-account pool.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 20 requests/minute per user (Lower limit for modifications)

    **Request Body**:
    ```json
    {
      "account_id": "account-123",
      "phone": "+1234567890"
    }
    ```

    **Returns**:
        - Success status
        - Operation message
        - Account identifier

    **Example Response**:
    ```json
    {
      "success": true,
      "message": "Account added to pool successfully",
      "account_id": "account-123"
    }
    ```
    """
    try:
        multi_account_limiter = MultiAccountRateLimiter()

        # Check if account already exists in pool
        existing_account = await multi_account_limiter.get_account(request.account_id)
        if existing_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account {request.account_id} already exists in pool"
            )

        # Add account to pool
        await multi_account_limiter.add_account(
            account_id=request.account_id,
            phone=request.phone
        )

        logger.info(f"User {current_user.id} added account {request.account_id} to pool")

        return AccountOperationResponse(
            success=True,
            message="Account added to pool successfully",
            account_id=request.account_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding account to pool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add account to pool: {str(e)}"
        )


@router.put("/accounts/{account_id}", response_model=AccountOperationResponse, status_code=200)
async def update_account_status(
    account_id: str,
    request: AccountUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update account status (enable/disable account).

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 30 requests/minute per user

    **Path Parameters**:
    - `account_id`: Account identifier

    **Request Body**:
    ```json
    {
      "status": "active"
    }
    ```

    **Valid Status Values**:
    - `active`: Enable account (available for requests)
    - `disabled`: Disable account (manually disabled)
    - `failed`: Mark as failed (automatic exclusion)

    **Returns**:
        - Success status
        - Operation message
        - Account identifier

    **Example Response**:
    ```json
    {
      "success": true,
      "message": "Account status updated to active",
      "account_id": "account-123"
    }
    ```
    """
    try:
        from ...services.multi_account_rate_limiter import AccountStatus

        multi_account_limiter = MultiAccountRateLimiter()

        # Check if account exists
        account = await multi_account_limiter.get_account(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {account_id} not found in pool"
            )

        # Validate status
        valid_statuses = ["active", "disabled", "failed"]
        if request.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )

        # Map status string to AccountStatus enum
        status_map = {
            "active": AccountStatus.ACTIVE,
            "disabled": AccountStatus.DISABLED,
            "failed": AccountStatus.FAILED
        }
        new_status = status_map[request.status]

        # Update account status
        success = await multi_account_limiter.set_account_status(account_id, new_status)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update account status"
            )

        logger.info(
            f"User {current_user.id} updated account {account_id} status to {request.status}"
        )

        return AccountOperationResponse(
            success=True,
            message=f"Account status updated to {request.status}",
            account_id=account_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account status: {str(e)}"
        )


@router.delete("/accounts/{account_id}", response_model=AccountOperationResponse, status_code=200)
async def remove_account_from_pool(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove an account from the multi-account pool.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 20 requests/minute per user (Lower limit for destructive operations)

    **Path Parameters**:
    - `account_id`: Account identifier

    **Returns**:
        - Success status
        - Operation message
        - Account identifier

    **Example Response**:
    ```json
    {
      "success": true,
      "message": "Account removed from pool successfully",
      "account_id": "account-123"
    }
    ```
    """
    try:
        multi_account_limiter = MultiAccountRateLimiter()

        # Check if account exists
        account = await multi_account_limiter.get_account(account_id)
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account {account_id} not found in pool"
            )

        # Remove account from pool
        success = await multi_account_limiter.remove_account(account_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove account from pool"
            )

        logger.info(f"User {current_user.id} removed account {account_id} from pool")

        return AccountOperationResponse(
            success=True,
            message="Account removed from pool successfully",
            account_id=account_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing account from pool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove account from pool: {str(e)}"
        )


@router.put("/settings", response_model=RateLimitSettingsResponse, status_code=200)
async def update_rate_limit_settings(
    request: RateLimitSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Configure alert thresholds and notification preferences.

    **Permission**: Authenticated user (admin access recommended)

    **Rate Limit**: 30 requests/minute per user

    **Request Body**:
    ```json
    {
      "alert_thresholds": {
        "warning_threshold_percent": 75.0,
        "critical_threshold_percent": 90.0
      },
      "notification_preferences": {
        "enabled": true,
        "channels": ["channel-1", "channel-2"],
        "notify_on_warning": true,
        "notify_on_critical": true,
        "cooldown_seconds": 300
      }
    }
    ```

    **Returns**:
        - Updated alert thresholds
        - Updated notification preferences
        - Settings timestamp

    **Example Response**:
    ```json
    {
      "alert_thresholds": {
        "warning_threshold_percent": 75.0,
        "critical_threshold_percent": 90.0
      },
      "notification_preferences": {
        "enabled": true,
        "channels": ["channel-1", "channel-2"],
        "notify_on_warning": true,
        "notify_on_critical": true,
        "cooldown_seconds": 300
      },
      "timestamp": "2025-01-24T12:00:00Z"
    }
    ```

    **Notes**:
        - Both `alert_thresholds` and `notification_preferences` are optional
        - Only provided fields will be updated
        - Thresholds must be between 0 and 100
        - Warning threshold should be less than critical threshold (validated automatically)
    """
    try:
        # Import settings manager if available, otherwise use in-memory storage
        # For now, we'll implement a simple in-memory configuration store
        if not hasattr(update_rate_limit_settings, '_settings'):
            # Initialize default settings
            update_rate_limit_settings._settings = {
                "alert_thresholds": AlertThresholds(),
                "notification_preferences": NotificationPreferences()
            }

        # Update alert thresholds if provided
        if request.alert_thresholds is not None:
            # Validate that warning < critical
            if request.alert_thresholds.warning_threshold_percent >= request.alert_thresholds.critical_threshold_percent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="warning_threshold_percent must be less than critical_threshold_percent"
                )
            update_rate_limit_settings._settings["alert_thresholds"] = request.alert_thresholds

        # Update notification preferences if provided
        if request.notification_preferences is not None:
            update_rate_limit_settings._settings["notification_preferences"] = request.notification_preferences

        logger.info(f"User {current_user.id} updated rate limit settings")

        return RateLimitSettingsResponse(
            alert_thresholds=update_rate_limit_settings._settings["alert_thresholds"],
            notification_preferences=update_rate_limit_settings._settings["notification_preferences"],
            timestamp=_get_timestamp()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rate limit settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rate limit settings: {str(e)}"
        )


# Helper Functions

def _get_timestamp() -> str:
    """Get current timestamp in ISO 8601 format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _determine_status(usage_percent: float) -> str:
    """Determine status based on usage percentage."""
    if usage_percent >= 90:
        return "critical"
    elif usage_percent >= 75:
        return "warning"
    else:
        return "healthy"


def _determine_overall_status(accounts: List[AccountLimitStatus]) -> str:
    """Determine overall system status based on all accounts."""
    if not accounts:
        return "healthy"

    has_critical = any(acc.status == "critical" for acc in accounts)
    has_warning = any(acc.status == "warning" for acc in accounts)

    if has_critical:
        return "critical"
    elif has_warning:
        return "warning"
    else:
        return "healthy"
