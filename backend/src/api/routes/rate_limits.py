"""
API routes for rate limit monitoring and management.

Endpoints:
  GET /api/v1/rate-limits/status - Get current rate limit status across all accounts
  GET /api/v1/rate-limits/metrics - Get detailed rate limit metrics and predictions
  GET /api/v1/rate-limits/accounts - Get account pool status and distribution
  GET /api/v1/rate-limits/queue - Get queue statistics and pending requests
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


class RateLimitMetricsResponse(BaseModel):
    """Detailed rate limit metrics and predictions."""
    usage_metrics: List[UsageMetrics] = Field(..., description="Per-account usage metrics")
    predictions: List[PredictionMetrics] = Field(..., description="Rate limit predictions")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")
    timestamp: str = Field(..., description="Metrics timestamp (ISO 8601)")


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
