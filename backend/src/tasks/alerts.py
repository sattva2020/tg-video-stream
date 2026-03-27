"""Periodic alert checking and evaluation task.

This module provides `check_periodic_alerts()` which will either:
- enqueue a background job using Celery (if CELERY_BROKER_URL is configured), or
- fall back to a synchronous call (dev-mode)

The task evaluates all enabled alert rules and triggers alerts when conditions are met.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID, uuid4

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

    @celery_app.task(name='alerts.trigger', bind=True, max_retries=3, default_retry_delay=60)
    def trigger_alert_task(self, payload: Dict):
        """Worker entrypoint for async alert notification.

        This task processes alert triggers asynchronously and sends notifications
        through configured channels using the notification routing service.

        Args:
            payload: Dict containing alert trigger information:
                - instance_id: UUID of the alert instance
                - rule_id: UUID of the alert rule
                - rule_name: Name of the alert rule
                - alert_type: Type of alert (e.g., 'system_resource', 'stream_failure')
                - severity: Severity level ('critical', 'warning', 'info')
                - subject: Notification subject
                - body: Notification body
                - context: Additional context for template rendering
                - notification_channels: Dict of configured channels

        Returns:
            bool: True if notifications sent successfully, False otherwise
        """
        logger.info("[worker] trigger_alert_task started", extra={"payload": payload})
        from database import SessionLocal
        from src.services.alert_service import AlertService
        from src.services.notifications.routing import NotificationRoutingService, EventPayload

        db = SessionLocal()
        try:
            alert_service = AlertService(db)
            routing_service = NotificationRoutingService(db)

            instance_id = payload.get("instance_id")
            rule_id = payload.get("rule_id")

            if not instance_id:
                logger.error("Missing instance_id in payload")
                return False

            # Get the alert instance
            instance = alert_service.get_instance(instance_id)
            if not instance:
                logger.error(f"Alert instance not found: {instance_id}")
                return False

            # Get the rule to access notification channels
            rule = alert_service.get_rule(rule_id) if rule_id else None
            if not rule:
                logger.error(f"Alert rule not found: {rule_id}")
                return False

            notification_channels = rule.notification_channels
            if not notification_channels:
                logger.info(f"No notification channels configured for rule {rule.name}")
                instance.notification_sent = False
                db.commit()
                return True

            # Build event payload for routing
            event_id = payload.get("event_id") or str(uuid4())
            event_payload = EventPayload(
                event_id=event_id,
                severity=payload.get("severity"),
                tags=payload.get("context", {}).get("tags"),
                host=payload.get("context", {}).get("host"),
                context=payload.get("context", {}),
                subject=payload.get("subject"),
                body=payload.get("body"),
            )

            # Build delivery plan through routing service
            delivery_plan = routing_service.build_delivery_plan(event_payload)

            if not delivery_plan:
                logger.info(f"No delivery plan created for alert {instance_id}")
                instance.notification_sent = False
                db.commit()
                return True

            # Import celery_app to send notification tasks
            from src.celery_app import celery_app as main_celery_app

            if not main_celery_app:
                logger.warning("Celery app not configured, skipping notification send")
                instance.notification_sent = False
                db.commit()
                return False

            # Send notifications for each delivery plan item
            success_count = 0
            error_count = 0

            for plan_item in delivery_plan:
                try:
                    for channel_id in plan_item.get("channel_ids", []):
                        notification_payload = {
                            "event_id": event_id,
                            "rule_id": plan_item.get("rule_id"),
                            "channel_id": channel_id,
                            "recipient_id": plan_item.get("recipient_id"),
                            "context": plan_item.get("context", {}),
                        }

                        # Send to notification processing task
                        main_celery_app.send_task(
                            "notifications.process_event",
                            args=[notification_payload],
                        )

                        success_count += 1
                        logger.info(
                            f"Notification queued for alert {instance_id}",
                            extra={
                                "channel_id": str(channel_id),
                                "recipient_id": str(plan_item.get("recipient_id")),
                            },
                        )

                except Exception as exc:
                    error_count += 1
                    logger.exception(
                        f"Failed to queue notification for alert {instance_id}",
                        extra={"error": str(exc)},
                    )

            # Update instance status
            instance.notification_sent = success_count > 0
            instance.notification_channels = {
                "queued": success_count,
                "errors": error_count,
                "channels": list(notification_channels.keys()),
            }
            db.commit()

            logger.info(
                f"Alert notifications processed: {instance_id}",
                extra={
                    "success_count": success_count,
                    "error_count": error_count,
                    "notification_sent": instance.notification_sent,
                },
            )

            return success_count > 0

        except Exception as exc:
            logger.exception("Failed to process alert trigger task")
            # Update instance with error status if possible
            try:
                instance_id = payload.get("instance_id")
                if instance_id:
                    instance = alert_service.get_instance(instance_id)
                    if instance:
                        instance.notification_sent = False
                        instance.notification_channels = {
                            "error": str(exc),
                            "failed_at": datetime.utcnow().isoformat(),
                        }
                        db.commit()
            except Exception:
                logger.error("Failed to update instance with error status")

            # Retry with exponential backoff
            raise self.retry(exc=exc)

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


def trigger_alert(
    instance_id: str,
    rule_id: str,
    rule_name: str,
    alert_type: str,
    severity: str,
    subject: str,
    body: str,
    context: Optional[Dict] = None,
    notification_channels: Optional[Dict] = None,
) -> bool:
    """Attempt to trigger an alert notification asynchronously.

    If Celery is configured, send the task to the worker.
    Otherwise, process the notification synchronously (dev-mode).

    Args:
        instance_id: UUID of the alert instance
        rule_id: UUID of the alert rule
        rule_name: Name of the alert rule
        alert_type: Type of alert
        severity: Severity level
        subject: Notification subject
        body: Notification body
        context: Additional context data
        notification_channels: Dict of configured channels

    Returns:
        bool: True if notification was queued/sent successfully, False otherwise
    """
    payload = {
        "instance_id": str(instance_id),
        "event_id": str(uuid4()),
        "rule_id": str(rule_id),
        "rule_name": rule_name,
        "alert_type": alert_type,
        "severity": severity,
        "subject": subject,
        "body": body,
        "context": context or {},
        "notification_channels": notification_channels or {},
    }

    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _build_celery_app()
        try:
            app.send_task('alerts.trigger', args=[payload])
            logger.info(
                "Enqueued alert trigger notification",
                extra={
                    "instance_id": str(instance_id),
                    "rule_name": rule_name,
                },
            )
            return True
        except Exception:
            logger.exception("Failed to enqueue alert trigger task")
            # fall through to sync
    # Dev fallback (synchronous)
    logger.info("Dev-mode: triggering alert notification synchronously")
    try:
        return trigger_alert_sync(payload)
    except Exception:
        logger.exception("Failed to trigger alert notification synchronously")
        return False


def trigger_alert_sync(payload: Dict) -> bool:
    """Process alert trigger notification synchronously.

    This is a fallback for development when Celery is not configured.

    Args:
        payload: Alert trigger payload

    Returns:
        bool: True if successful, False otherwise
    """
    from database import SessionLocal
    from src.services.alert_service import AlertService

    db = SessionLocal()
    try:
        alert_service = AlertService(db)
        instance_id = payload.get("instance_id")

        if not instance_id:
            logger.error("Missing instance_id in payload")
            return False

        # Update instance to show notification was attempted
        instance = alert_service.get_instance(instance_id)
        if not instance:
            logger.error(f"Alert instance not found: {instance_id}")
            return False

        # In dev mode, we just log and mark as sent
        # Real notification delivery happens via Celery in production
        logger.info(
            f"Alert notification (dev-mode): {payload.get('subject')}",
            extra={
                "instance_id": str(instance_id),
                "rule_name": payload.get("rule_name"),
                "severity": payload.get("severity"),
                "body": payload.get("body"),
            },
        )

        instance.notification_sent = True
        instance.notification_channels = {
            "dev_mode": True,
            "channels": list(payload.get("notification_channels", {}).keys()),
        }
        db.commit()

        return True

    except Exception as exc:
        logger.exception("Failed to process alert trigger synchronously")
        return False

    finally:
        db.close()


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
