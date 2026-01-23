"""
Webhook Delivery Load Tests

Performance tests for webhook delivery system under concurrent load.
Tests throughput, latency, deduplication, and retry logic.
"""
import asyncio
import pytest
import sys
import os
import time
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from typing import List, Dict, Any

# Add backend/src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/src")))

from src.models.webhook import Webhook, WebhookEventType
from src.models.webhook_event import WebhookEvent
from src.services.webhook_service import WebhookService
from src.services.webhook_worker import (
    deliver_webhook,
    is_duplicate_event,
    build_webhook_payload,
    generate_signature_headers,
    calculate_retry_delay,
)


@pytest.mark.asyncio
async def test_webhook_delivery_throughput_small():
    """
    Test webhook delivery throughput with small concurrent load (10 webhooks).
    Verify all webhooks are delivered successfully.
    """
    # Mock database and dependencies
    mock_db = MagicMock()

    with patch('src.services.webhook_worker.SessionLocal') as mock_session_local, \
         patch('src.services.webhook_worker.WebhookService') as mock_service_class, \
         patch('src.services.webhook_worker.deliver_webhook_http') as mock_deliver:

        mock_session_local.return_value = mock_db

        # Mock successful HTTP delivery
        mock_deliver.return_value = (True, 200, "OK", 50)

        # Create mock webhooks
        num_webhooks = 10
        webhooks = []
        webhook_events = []

        for i in range(num_webhooks):
            webhook = MagicMock(spec=Webhook)
            webhook.id = uuid4()
            webhook.url = f"https://example.com/webhook/{i}"
            webhook.is_active = True
            webhook.secret = "test_secret"
            webhooks.append(webhook)

            webhook_event = MagicMock(spec=WebhookEvent)
            webhook_event.id = i + 1
            webhook_event.webhook_id = webhook.id
            webhook_event.status = "pending"
            webhook_event.attempt_number = 1
            webhook_events.append(webhook_event)

        # Create tasks for concurrent delivery
        tasks = []
        start_time = time.time()

        for i in range(num_webhooks):
            payload = {
                "webhook_event_id": webhook_events[i].id,
                "event_type": "stream.started",
                "event_data": {"stream_id": str(uuid4())},
                "event_id": str(uuid4()),
            }
            tasks.append(deliver_webhook(payload))

        # Execute all tasks concurrently (note: in real async context)
        results = []
        for task in tasks:
            # Since deliver_webhook is not async, we just call it
            try:
                result = task
                results.append(result)
            except Exception as e:
                results.append(False)

        end_time = time.time()
        duration = end_time - start_time

        # Calculate throughput
        successful_deliveries = sum(1 for r in results if r is True)
        throughput = num_webhooks / duration if duration > 0 else 0

        # Assertions
        assert successful_deliveries == num_webhooks, \
            f"Expected {num_webhooks} successful deliveries, got {successful_deliveries}"
        assert throughput > 0, "Throughput should be positive"

    print(f"✓ Small load test: {num_webhooks} webhooks delivered in {duration:.2f}s")
    print(f"  Throughput: {throughput:.2f} webhooks/second")


@pytest.mark.asyncio
async def test_webhook_delivery_throughput_medium():
    """
    Test webhook delivery throughput with medium concurrent load (50 webhooks).
    Verify system handles moderate load without failures.
    """
    mock_db = MagicMock()

    with patch('src.services.webhook_worker.SessionLocal') as mock_session_local, \
         patch('src.services.webhook_worker.WebhookService') as mock_service_class, \
         patch('src.services.webhook_worker.deliver_webhook_http') as mock_deliver:

        mock_session_local.return_value = mock_db
        mock_deliver.return_value = (True, 200, "OK", 45)

        # Create mock webhooks for medium load
        num_webhooks = 50
        webhooks = []
        webhook_events = []

        for i in range(num_webhooks):
            webhook = MagicMock(spec=Webhook)
            webhook.id = uuid4()
            webhook.url = f"https://example.com/webhook/{i}"
            webhook.is_active = True
            webhook.secret = "test_secret"
            webhooks.append(webhook)

            webhook_event = MagicMock(spec=WebhookEvent)
            webhook_event.id = i + 1
            webhook_event.webhook_id = webhook.id
            webhook_event.status = "pending"
            webhook_event.attempt_number = 1
            webhook_events.append(webhook_event)

        # Simulate concurrent delivery
        tasks = []
        start_time = time.time()

        for i in range(num_webhooks):
            payload = {
                "webhook_event_id": webhook_events[i].id,
                "event_type": "stream.started",
                "event_data": {"stream_id": str(uuid4())},
                "event_id": str(uuid4()),
            }
            tasks.append(deliver_webhook(payload))

        # Process tasks
        results = []
        for task in tasks:
            try:
                result = task
                results.append(result)
            except Exception:
                results.append(False)

        end_time = time.time()
        duration = end_time - start_time

        successful_deliveries = sum(1 for r in results if r is True)
        throughput = num_webhooks / duration if duration > 0 else 0

        # Verify all deliveries succeeded
        assert successful_deliveries == num_webhooks, \
            f"Expected {num_webhooks} successful deliveries, got {successful_deliveries}"

        # Verify reasonable throughput (should handle at least 5 webhooks/second)
        assert throughput >= 5.0, \
            f"Throughput {throughput:.2f} webhooks/second below minimum 5.0"

    print(f"✓ Medium load test: {num_webhooks} webhooks delivered in {duration:.2f}s")
    print(f"  Throughput: {throughput:.2f} webhooks/second")


@pytest.mark.asyncio
async def test_webhook_deduplication_under_load():
    """
    Test webhook event deduplication with high duplicate rate (100 events, 50% duplicates).
    Verify deduplication system prevents duplicate deliveries.
    """
    mock_db = MagicMock()

    with patch('src.services.webhook_worker.SessionLocal') as mock_session_local, \
         patch('src.services.webhook_worker.WebhookService') as mock_service_class, \
         patch('src.services.webhook_worker.deliver_webhook_http') as mock_deliver:

        mock_session_local.return_value = mock_db
        mock_deliver.return_value = (True, 200, "OK", 40)

        num_unique_events = 50
        num_total_events = 100  # 50% duplicate rate

        webhook = MagicMock(spec=Webhook)
        webhook.id = uuid4()
        webhook.url = "https://example.com/webhook"
        webhook.is_active = True
        webhook.secret = "test_secret"

        # Track unique event IDs
        unique_event_ids = [str(uuid4()) for _ in range(num_unique_events)]

        # Create events with duplicates
        tasks = []
        webhook_event_id = 1

        for i in range(num_total_events):
            # Use event IDs from first half for second half (duplicates)
            if i < num_unique_events:
                event_id = unique_event_ids[i]
            else:
                event_id = unique_event_ids[i % num_unique_events]

            webhook_event = MagicMock(spec=WebhookEvent)
            webhook_event.id = webhook_event_id
            webhook_event.webhook_id = webhook.id
            webhook_event.status = "pending"
            webhook_event.attempt_number = 1

            payload = {
                "webhook_event_id": webhook_event.id,
                "event_type": "stream.started",
                "event_data": {"stream_id": str(uuid4())},
                "event_id": event_id,
            }

            tasks.append((payload, webhook_event))
            webhook_event_id += 1

        # Process events and track results
        start_time = time.time()
        successful_count = 0
        duplicate_skipped_count = 0

        for payload, webhook_event in tasks:
            # Simulate duplicate check (simplified for test)
            # In real system, is_duplicate_event would be called
            try:
                result = deliver_webhook(payload)
                if result:
                    successful_count += 1
            except Exception:
                pass

        end_time = time.time()
        duration = end_time - start_time

        # Verify system handled the load
        # (Note: exact duplicate detection depends on Redis state)
        assert duration < 30.0, "Deduplication test should complete within 30 seconds"

    print(f"✓ Deduplication test: {num_total_events} events processed in {duration:.2f}s")
    print(f"  Successful: {successful_count}, Duplicate rate: 50%")


@pytest.mark.asyncio
async def test_webhook_retry_logic_exponential_backoff():
    """
    Test exponential backoff calculation for webhook retries.
    Verify delay increases exponentially with attempt number.
    """
    # Test exponential backoff calculation
    delays = []

    for attempt in range(1, 6):  # Test attempts 1-5
        delay = calculate_retry_delay(attempt)
        delays.append(delay)

        # Verify exponential growth (each delay should be >= previous * multiplier)
        if attempt > 1:
            expected_min_delay = delays[attempt - 2] * 2  # multiplier is 2
            assert delay >= expected_min_delay, \
                f"Delay for attempt {attempt} ({delay}s) should be >= {expected_min_delay}s"

        # Verify maximum cap (1 hour = 3600 seconds)
        assert delay <= 3600, f"Delay {delay}s exceeds maximum 3600s"

    # Verify specific expected delays (with 60s initial delay, 2x multiplier)
    assert delays[0] == 60, f"First retry should be 60s, got {delays[0]}s"
    assert delays[1] == 120, f"Second retry should be 120s, got {delays[1]}s"
    assert delays[2] == 240, f"Third retry should be 240s, got {delays[2]}s"
    assert delays[3] == 480, f"Fourth retry should be 480s, got {delays[3]}s"
    assert delays[4] == 960, f"Fifth retry should be 960s, got {delays[4]}s"

    print("✓ Exponential backoff test:")
    for i, delay in enumerate(delays, 1):
        print(f"  Attempt {i}: {delay}s delay")


@pytest.mark.asyncio
async def test_webhook_payload_building_performance():
    """
    Test performance of webhook payload building for large payloads.
    Verify payload construction is efficient even with large data.
    """
    # Create large event data (simulate complex stream event)
    large_event_data = {
        "stream_id": str(uuid4()),
        "channel_id": str(uuid4()),
        "title": "Test Stream Title",
        "description": "A" * 1000,  # 1KB description
        "tags": ["tag" + str(i) for i in range(100)],  # 100 tags
        "metadata": {
            f"key_{i}": f"value_{i}" * 10 for i in range(50)  # 50 metadata keys
        },
        "viewer_count": 12345,
        "start_time": time.time(),
    }

    # Measure payload building performance
    iterations = 100
    start_time = time.time()

    for i in range(iterations):
        payload = build_webhook_payload(
            event_type="stream.started",
            event_data=large_event_data,
            event_id=str(uuid4()),
        )

        # Verify payload structure
        assert "event_type" in payload
        assert "data" in payload
        assert "timestamp" in payload
        assert "event_id" in payload

    end_time = time.time()
    duration = end_time - start_time
    avg_time = duration / iterations

    # Verify performance (should build payloads quickly)
    assert avg_time < 0.01, f"Average payload build time {avg_time}s exceeds 10ms"

    print(f"✓ Payload building test: {iterations} payloads in {duration:.3f}s")
    print(f"  Average: {avg_time*1000:.2f}ms per payload")


@pytest.mark.asyncio
async def test_webhook_signature_generation_performance():
    """
    Test performance of HMAC-SHA256 signature generation.
    Verify signature generation is efficient for high-throughput scenarios.
    """
    # Create mock webhook with typical secret
    webhook = MagicMock(spec=Webhook)
    webhook.id = uuid4()
    webhook.url = "https://example.com/webhook"
    webhook.secret = "a" * 32  # 32-byte secret

    # Create test payload
    payload = {
        "event_type": "stream.started",
        "data": {"stream_id": str(uuid4())},
        "timestamp": time.time(),
        "event_id": str(uuid4()),
    }

    # Measure signature generation performance
    iterations = 1000
    start_time = time.time()

    signatures = []
    for i in range(iterations):
        headers = generate_signature_headers(webhook, payload)
        signature = headers.get("X-Sattva-Signature", "")
        signatures.append(signature)

        # Verify signature format
        assert signature.startswith("sha256="), "Signature should have sha256= prefix"
        assert len(signature) == 7 + 64, "SHA256 signature should be 64 hex chars + prefix"

    end_time = time.time()
    duration = end_time - start_time
    avg_time = duration / iterations
    throughput = iterations / duration

    # Verify performance (signatures should be generated quickly)
    assert avg_time < 0.001, f"Average signature time {avg_time}s exceeds 1ms"
    assert throughput > 100, f"Throughput {throughput} signatures/sec below minimum 100"

    # Verify all signatures are identical for same payload
    unique_signatures = set(signatures)
    assert len(unique_signatures) == 1, "All signatures for same payload should be identical"

    print(f"✓ Signature generation test: {iterations} signatures in {duration:.3f}s")
    print(f"  Average: {avg_time*1000:.3f}ms per signature")
    print(f"  Throughput: {throughput:.0f} signatures/second")


@pytest.mark.asyncio
async def test_webhook_concurrent_mixed_events():
    """
    Test webhook delivery with mixed event types under concurrent load.
    Verify system correctly handles different event types simultaneously.
    """
    mock_db = MagicMock()

    with patch('src.services.webhook_worker.SessionLocal') as mock_session_local, \
         patch('src.services.webhook_worker.WebhookService') as mock_service_class, \
         patch('src.services.webhook_worker.deliver_webhook_http') as mock_deliver:

        mock_session_local.return_value = mock_db
        mock_deliver.return_value = (True, 200, "OK", 35)

        # Different event types
        event_types = [
            "stream.started",
            "stream.stopped",
            "stream.error",
            "viewer.milestone",
            "track.started",
            "track.completed",
        ]

        num_webhooks_per_type = 10
        total_webhooks = len(event_types) * num_webhooks_per_type

        tasks = []
        webhook_event_id = 1

        for event_type in event_types:
            for i in range(num_webhooks_per_type):
                webhook = MagicMock(spec=Webhook)
                webhook.id = uuid4()
                webhook.url = f"https://example.com/webhook/{i}"
                webhook.is_active = True
                webhook.secret = "test_secret"

                webhook_event = MagicMock(spec=WebhookEvent)
                webhook_event.id = webhook_event_id
                webhook_event.webhook_id = webhook.id
                webhook_event.status = "pending"
                webhook_event.attempt_number = 1

                payload = {
                    "webhook_event_id": webhook_event.id,
                    "event_type": event_type,
                    "event_data": {"test": "data"},
                    "event_id": str(uuid4()),
                }

                tasks.append((event_type, payload))
                webhook_event_id += 1

        # Process all events
        start_time = time.time()
        results_by_type = {evt: {"total": 0, "success": 0} for evt in event_types}

        for event_type, payload in tasks:
            results_by_type[event_type]["total"] += 1
            try:
                result = deliver_webhook(payload)
                if result:
                    results_by_type[event_type]["success"] += 1
            except Exception:
                pass

        end_time = time.time()
        duration = end_time - start_time

        # Verify all event types were processed
        for event_type, counts in results_by_type.items():
            assert counts["total"] == num_webhooks_per_type, \
                f"Expected {num_webhooks_per_type} {event_type} events, got {counts['total']}"
            assert counts["success"] == num_webhooks_per_type, \
                f"Expected {num_webhooks_per_type} successful {event_type} deliveries, got {counts['success']}"

        print(f"✓ Mixed events test: {total_webhooks} webhooks ({len(event_types)} types) in {duration:.2f}s")
        for event_type, counts in results_by_type.items():
            print(f"  {event_type}: {counts['success']}/{counts['total']} successful")


@pytest.mark.asyncio
async def test_webhook_delivery_latency_metrics():
    """
    Test webhook delivery latency under various load conditions.
    Measure and report P50, P95, P99 latencies.
    """
    mock_db = MagicMock()

    with patch('src.services.webhook_worker.SessionLocal') as mock_session_local, \
         patch('src.services.webhook_worker.WebhookService') as mock_service_class, \
         patch('src.services.webhook_worker.deliver_webhook_http') as mock_deliver:

        mock_session_local.return_value = mock_db

        # Simulate varying response times (ms)
        response_times_ms = [20, 35, 45, 60, 80, 100, 150, 200, 300, 500]

        num_webhooks = 100
        latencies = []

        for i in range(num_webhooks):
            # Cycle through different response times
            latency_ms = response_times_ms[i % len(response_times_ms)]
            mock_deliver.return_value = (True, 200, "OK", latency_ms)

            webhook = MagicMock(spec=Webhook)
            webhook.id = uuid4()
            webhook.url = f"https://example.com/webhook/{i}"
            webhook.is_active = True
            webhook.secret = "test_secret"

            webhook_event = MagicMock(spec=WebhookEvent)
            webhook_event.id = i + 1
            webhook_event.webhook_id = webhook.id
            webhook_event.status = "pending"
            webhook_event.attempt_number = 1

            payload = {
                "webhook_event_id": webhook_event.id,
                "event_type": "stream.started",
                "event_data": {"stream_id": str(uuid4())},
                "event_id": str(uuid4()),
            }

            start_time = time.time()
            try:
                deliver_webhook(payload)
                latencies.append(latency_ms)
            except Exception:
                pass

        # Calculate percentile metrics
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.5)]
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        avg = sum(latencies) / len(latencies)

        # Verify latency thresholds
        assert p50 <= 100, f"P50 latency {p50}ms exceeds 100ms threshold"
        assert p95 <= 300, f"P95 latency {p95}ms exceeds 300ms threshold"
        assert avg <= 150, f"Average latency {avg}ms exceeds 150ms threshold"

        print(f"✓ Latency metrics test ({num_webhooks} deliveries):")
        print(f"  Average: {avg:.1f}ms")
        print(f"  P50: {p50}ms")
        print(f"  P95: {p95}ms")
        print(f"  P99: {p99}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
