# Testing Recommendation Quality Metrics

## Overview
This document describes the integration tests for tracking and measuring recommendation quality metrics (CTR, watch time, feedback rate).

## Feature: 014-ai-powered-content-recommendations
## Subtask: 6-6 - Measure recommendation quality metrics (CTR, watch time)

## What is being tested?

These tests verify that the recommendation system properly tracks and measures quality metrics:

1. **Recommendation Impressions**: When recommendations are fetched via the API, they are saved to the `recommendations` table
2. **User Interactions**: When users click, watch, skip, like, or share recommended content, it's tracked in `user_item_interactions` table
3. **Quality Metrics**: The stats endpoint calculates and returns:
   - **CTR (Click-Through Rate)**: ratio of interactions to recommendations shown
   - **Average Watch Time**: average duration of watch interactions
   - **Positive Feedback Rate**: ratio of likes to total feedback

## Database Schema

### Recommendations Table
Stores every recommendation shown to users (impressions):
- `user_id`: User who received the recommendation
- `playlist_item_id`: Recommended content
- `algorithm`: collaborative_filtering, content_based, or hybrid
- `score`: Confidence score (0-1)
- `created_at`: When the recommendation was shown

### UserItemInteractions Table
Stores user interactions with content:
- `user_id`: User who interacted
- `playlist_item_id`: Content that was interacted with
- `interaction_type`: watch, skip, like, share, click
- `duration_seconds`: Duration of watch (if applicable)
- `completion_rate`: Proportion of content watched (0-1)
- `interacted_at`: When the interaction occurred

### RecommendationFeedback Table
Stores explicit user feedback:
- `user_id`: User who provided feedback
- `playlist_item_id`: Content being rated
- `feedback_type`: like or dislike
- `created_at`: When feedback was submitted

## Test Cases

### 1. test_create_recommendations_tracked_as_impressions
**Purpose**: Verify recommendations are saved when fetched

**Steps**:
1. Call `get_recommendations()` API
2. Query `recommendations` table
3. Verify records exist with correct fields (user_id, playlist_item_id, algorithm, score, created_at)

**Expected Result**: Recommendations are persisted to database

### 2. test_track_clicks_and_watches_on_recommendations
**Purpose**: Verify interactions are tracked

**Steps**:
1. Get recommendations
2. Call `record_interaction()` with type="click"
3. Call `record_interaction()` with type="watch"
4. Query `user_item_interactions` table
5. Verify records exist with correct data

**Expected Result**: Interactions are persisted with correct metadata

### 3. test_stats_endpoint_returns_correct_ctr
**Purpose**: Verify CTR is calculated correctly

**Formula**: CTR = interactions / recommendations

**Steps**:
1. Create 10 recommendations (impressions)
2. Record 5 click interactions
3. Call `get_stats(period="7d")`
4. Verify CTR ≈ 0.5 (5/10)

**Query Logic**:
```sql
SELECT COUNT(ui.id)
FROM user_item_interactions ui
JOIN recommendations r ON
  ui.playlist_item_id = r.playlist_item_id
  AND ui.user_id = r.user_id
  AND ui.interacted_at >= r.created_at
WHERE ui.interacted_at >= :cutoff_date
```

**Expected Result**: CTR between 0 and 1

### 4. test_stats_endpoint_returns_correct_watch_time
**Purpose**: Verify average watch time is calculated correctly

**Steps**:
1. Record watch interactions with durations: [60, 90, 120, 180, 240] seconds
2. Call `get_stats(period="7d")`
3. Verify average_watch_time_seconds ≈ 138 seconds (average of durations)

**Query Logic**:
```sql
SELECT AVG(ui.duration_seconds)
FROM user_item_interactions ui
WHERE ui.interaction_type = 'watch'
  AND ui.interacted_at >= :cutoff_date
```

**Expected Result**: Average watch time > 0

### 5. test_stats_endpoint_returns_correct_feedback_rate
**Purpose**: Verify positive feedback rate is calculated correctly

**Formula**: Positive Rate = likes / (likes + dislikes)

**Steps**:
1. Submit 5 likes and 3 dislikes
2. Call `get_stats(period="7d")`
3. Verify feedback_positive_rate ≈ 0.625 (5/8)

**Query Logic**:
```sql
-- Total feedback
SELECT COUNT(*) FROM recommendation_feedback
WHERE created_at >= :cutoff_date

-- Positive feedback
SELECT COUNT(*) FROM recommendation_feedback
WHERE created_at >= :cutoff_date
  AND feedback_type = 'like'
```

**Expected Result**: Feedback rate between 0 and 1

### 6. test_end_to_end_quality_metrics_tracking
**Purpose**: Full E2E test of metrics tracking pipeline

**Steps**:
1. Create recommendations (impressions)
2. Record interactions (clicks, watches)
3. Submit feedback (likes, dislikes)
4. Call `get_stats(period="7d")`
5. Verify all metrics are present and reasonable

**Expected Result**: All metrics calculated correctly, algorithm_performance includes counts

### 7. test_stats_endpoint_with_different_periods
**Purpose**: Verify stats work for different time periods

**Steps**:
1. Create recommendations and interactions
2. Call `get_stats(period="7d")`
3. Call `get_stats(period="30d")`
4. Call `get_stats(period="90d")`

**Expected Result**: Stats returned for all periods, period field matches request

### 8. test_recommendations_and_interactions_linking
**Purpose**: Verify proper linking between recommendations and interactions

**Steps**:
1. Create recommendation for user
2. Record interaction for same user and item
3. Query both tables
4. Verify user_id and playlist_item_id match

**Expected Result**: Records properly linked by user_id and playlist_item_id

## API Endpoints

### GET /api/recommendations
Fetches personalized recommendations and saves impressions to database.

**Request**:
```json
{
  "user_id": "user123",
  "limit": 10,
  "algorithm": "hybrid",
  "exclude_watched": true
}
```

**Side Effect**: Creates records in `recommendations` table (top 20)

### POST /api/recommendations/feedback
Submits user feedback (like/dislike).

**Request**:
```json
{
  "playlist_item_id": "uuid",
  "feedback_type": "like"
}
```

**Side Effect**: Creates record in `recommendation_feedback` table

### GET /api/recommendations/stats?period=7d
Returns quality metrics for the specified period.

**Response**:
```json
{
  "period": "7d",
  "quality_metrics": {
    "click_through_rate": 0.15,
    "average_watch_time_seconds": 125.5,
    "feedback_positive_rate": 0.75,
    "total_recommendations_shown": 1000,
    "total_interactions": 150
  },
  "algorithm_performance": [
    {"algorithm": "collaborative_filtering", "count": 400},
    {"algorithm": "content_based", "count": 300},
    {"algorithm": "hybrid", "count": 300}
  ],
  "cached_at": "2026-01-24T10:00:00Z"
}
```

## How CTR is Calculated (Improved)

The improved query joins on three conditions:
1. **Same playlist_item_id**: Interaction is for the recommended item
2. **Same user_id**: The user who received the recommendation also interacted with it
3. **Time constraint**: Interaction happened AFTER the recommendation was shown

This ensures we only count interactions that are actually responses to recommendations.

## Running the Tests

```bash
# Run all quality metrics tests
cd backend
pytest tests/integration/test_recommendation_quality_metrics.py -v

# Run specific test
pytest tests/integration/test_recommendation_quality_metrics.py::TestRecommendationQualityMetrics::test_stats_endpoint_returns_correct_ctr -v

# Run with coverage
pytest tests/integration/test_recommendation_quality_metrics.py -v --cov=src.services.recommendation_service
```

## Expected Test Results

All tests should pass with:
- ✅ Recommendations tracked as impressions
- ✅ Interactions tracked correctly
- ✅ CTR calculated accurately (0-1 range)
- ✅ Watch time calculated correctly (>0)
- ✅ Feedback rate calculated correctly (0-1 range)
- ✅ Different periods work correctly
- ✅ E2E flow completes successfully

## Troubleshooting

### Issue: CTR is always 0
**Cause**: No interactions recorded for recommended items
**Solution**: Verify that:
1. Recommendations are being saved (check `recommendations` table)
2. Interactions are being recorded with correct user_id and playlist_item_id
3. Time constraint is satisfied (interacted_at >= recommendation.created_at)

### Issue: CTR is greater than 1
**Cause**: Query counting more interactions than recommendations
**Solution**: Verify the join conditions include user_id match

### Issue: Average watch time is 0
**Cause**: No watch interactions in the period
**Solution**:
1. Check `user_item_interactions` table for records with interaction_type='watch'
2. Verify duration_seconds is not NULL
3. Check interacted_at is within the period

### Issue: Feedback rate is 0
**Cause**: No feedback submitted in the period
**Solution**:
1. Check `recommendation_feedback` table has records
2. Verify created_at is within the period
3. Check feedback_type values are 'like' or 'dislike'

## Success Criteria

✅ All 8 test cases pass
✅ CTR is in range [0, 1]
✅ Watch time is positive (>0)
✅ Feedback rate is in range [0, 1]
✅ Stats endpoint returns data for all periods (7d, 30d, 90d)
✅ Algorithm performance breakdown is included
✅ No SQL errors in logs
