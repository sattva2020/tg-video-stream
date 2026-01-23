#!/usr/bin/env python
"""Verification script for Celery Beat recommendation schedules."""
import sys
sys.path.insert(0, 'src')

from lib.celery_beat import CeleryBeatConfig

def main():
    config = CeleryBeatConfig()
    schedules = config.app.conf.beat_schedule

    # Find recommendation-related schedules
    rec_schedules = [
        k for k in schedules.keys()
        if 'recommendation' in k.lower() or
           'collaborative' in k.lower() or
           'content' in k.lower() or
           'interaction' in k.lower()
    ]

    print("Found recommendation-related schedules:")
    for name in rec_schedules:
        schedule = schedules[name]
        print(f"  - {name}")
        print(f"    Task: {schedule['task']}")
        print(f"    Schedule: {schedule['schedule']}")

    print(f"\nTotal schedules configured: {len(schedules)}")
    print(f"Recommendation schedules: {len(rec_schedules)}")

    # Verify expected schedules exist
    expected = [
        'train-collaborative-filtering-model',
        'train-content-based-model',
        'update-recommendation-interaction-matrix'
    ]

    missing = [name for name in expected if name not in schedules]
    if missing:
        print(f"\nERROR: Missing schedules: {missing}")
        return 1

    print("\n✓ All expected recommendation schedules are configured")
    return 0

if __name__ == '__main__':
    sys.exit(main())
