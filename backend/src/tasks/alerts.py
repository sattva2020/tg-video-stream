"""Periodic alert checking and evaluation task.

This module provides `check_periodic_alerts()` which will either:
- enqueue a background job using Celery (if CELERY_BROKER_URL is configured), or
- fall back to a synchronous call (dev-mode)

The task evaluates all enabled alert rules and triggers alerts when conditions are met.
"""
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Try to lazily import Celery when available
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except Exception:
    Celery = None
    CELERY_AVAILABLE = False


def _build_celery_app():
    """Build Celery app instance for task execution."""
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    app = Celery('tg_video_streamer', broker=broker)
    return app


# Define the actual worker function (registered only if Celery available)
if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _build_celery_app()

    @celery_app.task(name='alerts.check_periodic')
    def check_periodic_alerts_task():
        """Worker entrypoint for periodic alert evaluation.

        This task is called by Celery beat to evaluate all enabled alert rules
        and trigger alerts when conditions are met.
        """
        logger.info("[worker] check_periodic_alerts_task started")
        from database import SessionLocal

        db = SessionLocal()
        try:
            return check_periodic_alerts_sync(db)
        finally:
            db.close()


def check_periodic_alerts():
    """Attempt to schedule a periodic alert check job.

    If Celery is configured, call the Celery task `.delay()`.
    Otherwise call the check function synchronously (dev-mode).
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _build_celery_app()
        try:
            app.send_task('alerts.check_periodic')
            logger.info("Enqueued periodic alert check")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task")
            # fall through to sync
    # Dev fallback (synchronous) — attempt to perform check now
    logger.info("Dev-mode: checking periodic alerts synchronously")
    try:
        from database import SessionLocal
        db = SessionLocal()
        try:
            return check_periodic_alerts_sync(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to check periodic alerts synchronously")
        return False


def check_periodic_alerts_sync(db) -> dict:
    """Perform periodic alert evaluation synchronously.

    This is the core logic that evaluates all enabled alert rules
    and triggers alerts when conditions are met.

    Args:
        db: Database session

    Returns:
        dict with results: {"rules_evaluated": int, "alerts_triggered": int, "errors": list}
    """
    from src.services.alert_evaluator import AlertEvaluator, EvaluationContext
    from src.services.alert_service import AlertService
    from src.services.alert_trigger_service import AlertTriggerService
    from src.services.alert_grouping_service import AlertGroupingService

    results = {
        "rules_evaluated": 0,
        "alerts_triggered": 0,
        "errors": [],
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        # Initialize services
        evaluator = AlertEvaluator(db)
        trigger_service = AlertTriggerService(db)
        grouping_service = AlertGroupingService(db)

        # Get all enabled rules for evaluation
        rules = evaluator.get_rules_for_evaluation(enabled_only=True)
        results["rules_evaluated"] = len(rules)

        logger.info(
            f"Starting periodic alert check",
            extra={"rules_count": len(rules)}
        )

        for rule in rules:
            try:
                # Create evaluation context with metric value
                # Note: In a real implementation, you would fetch actual metrics here
                # For now, we use a placeholder context that can be overridden
                context = _create_evaluation_context(rule)

                # Evaluate the rule
                evaluation_result = evaluator.evaluate_rule(rule, context)

                if evaluation_result and evaluation_result.triggered:
                    logger.info(
                        f"Alert rule triggered: {rule.name}",
                        extra={
                            "rule_id": str(rule.id),
                            "severity": evaluation_result.severity,
                            "trigger_value": evaluation_result.trigger_value,
                        }
                    )

                    # Find or create alert group
                    group, created = grouping_service.find_or_create_group(
                        rule=rule,
                        context=evaluation_result.context,
                        alert_type=evaluation_result.alert_type,
                        severity=evaluation_result.severity,
                    )

                    # Trigger the alert
                    instance = trigger_service.trigger_alert(
                        result=evaluation_result,
                        group_id=group.id if group else None,
                        group_key=_generate_group_key(rule, evaluation_result.context) if group else None,
                    )

                    if instance:
                        results["alerts_triggered"] += 1
                        logger.info(
                            f"Alert instance created",
                            extra={
                                "instance_id": str(instance.id),
                                "group_id": str(group.id) if group else None,
                            }
                        )

            except Exception as e:
                error_msg = f"Failed to evaluate rule {rule.name}: {str(e)}"
                logger.exception(error_msg, extra={"rule_id": str(rule.id)})
                results["errors"].append(error_msg)

        logger.info(
            f"Periodic alert check completed",
            extra={
                "rules_evaluated": results["rules_evaluated"],
                "alerts_triggered": results["alerts_triggered"],
                "errors_count": len(results["errors"]),
            }
        )

    except Exception as e:
        error_msg = f"Failed to run periodic alert check: {str(e)}"
        logger.exception(error_msg)
        results["errors"].append(error_msg)

    return results


def _create_evaluation_context(rule):
    """Create evaluation context for a rule.

    This is a placeholder that fetches or simulates metric data.
    In production, this would integrate with monitoring systems
    to fetch real metrics.

    Args:
        rule: AlertRule to create context for

    Returns:
        EvaluationContext with metric data
    """
    from src.services.alert_evaluator import EvaluationContext

    # Placeholder: In real implementation, fetch actual metrics here
    # Examples:
    # - Query monitoring system for stream quality
    # - Check database for error rates
    # - Query system metrics for CPU/memory usage

    metric_value = None  # To be implemented with actual metric fetching

    context = EvaluationContext(
        metric_value=metric_value,
        timestamp=datetime.utcnow(),
        host=None,  # Can be set based on rule conditions
        service=None,  # Can be set based on rule conditions
        tags={},  # Additional tags for grouping
        additional_context={},  # Any additional context needed
    )

    return context


def _generate_group_key(rule, context):
    """Generate a unique group key for alert grouping.

    Args:
        rule: AlertRule
        context: Evaluation context dict

    Returns:
        str: Unique group key
    """
    parts = [str(rule.id)]

    # Add host/service to key if present for host-based grouping
    if context.get("host"):
        parts.append(f"host:{context['host']}")
    if context.get("service"):
        parts.append(f"service:{context['service']}")

    # Add key tags for more granular grouping
    tags = context.get("tags", {})
    if tags:
        tag_parts = [f"{k}:{v}" for k, v in sorted(tags.items()) if v is not None]
        if tag_parts:
            parts.extend(tag_parts)

    return "|".join(parts)
