# Testing Feedback Loop - Documentation

## Overview

This integration test verifies that the feedback loop works correctly - when users provide like/dislike feedback, the recommendation system learns from it and improves future recommendations.

## Test File

`test_feedback_loop_recommendations.py`

## What Is Tested

### 1. Initial Recommendations (`test_fetch_initial_recommendations`)
- Verifies that recommendations can be fetched for a new user
- Checks response structure (algorithm, generated_at, recommendations list)
- Establishes baseline before feedback

### 2. Submit Feedback (`test_submit_feedback_via_api`)
- Submits like feedback for 6 Classical Music items via API
- Verifies `RecommendationFeedback` records are created in database
- Validates feedback response structure (id, playlist_item_id, feedback_type, created_at)

### 3. Convert Feedback to Interactions (`test_convert_feedback_to_interactions`)
- Converts feedback to `UserItemInteraction` records for collaborative filtering
- Like feedback → interaction_type="like" with completion_rate=1.0
- This is necessary because collaborative filtering trains on UserItemInteraction data

### 4. Model Retraining (`test_train_model_after_feedback`)
- Trains collaborative filtering model via `train_collaborative_model()` Celery task
- Validates training metrics:
  - users_count ≥ 1
  - items_count ≥ 6
  - interactions_count ≥ 6
  - explained_variance > 0

### 5. Updated Recommendations Reflect Feedback (`test_updated_recommendations_reflect_feedback`)
- Fetches recommendations after model retraining
- Verifies recommendations are valid (scores 0-1, correct algorithm, reason provided)
- Collaborative filtering now considers the new interaction data

### 6. Content-Based Immediate Effect (`test_content_based_feedback_immediate_effect`)
- Tests content-based filtering (uses feedback directly without retraining)
- `_get_liked_items()` combines RecommendationFeedback + high completion_rate watches
- Content-based recommendations update immediately after feedback

### 7. End-to-End Feedback Loop (`test_end_to_end_feedback_loop`)
- Complete E2E test covering:
  1. Fetch initial recommendations
  2. Submit like feedback (Classical Music) + dislike feedback (Electronic Dance)
  3. Create interactions from feedback
  4. Retrain model
  5. Fetch updated recommendations (collaborative, content-based, hybrid)
- Validates full feedback loop workflow

## How Feedback Loop Works

### Immediate Effect (Content-Based & Hybrid)
1. User submits feedback via `submit_feedback()`
2. Creates `RecommendationFeedback` record
3. `_get_liked_items()` reads feedback (likes) + high completion_rate watches
4. Content-based filtering uses liked items directly:
   - `predict_for_user(user_id, liked_items=[...])`
   - Finds similar items via TF-IDF + cosine similarity
5. **No retraining required** - effect is immediate

### Delayed Effect (Collaborative Filtering)
1. Feedback creates `RecommendationFeedback` record
2. For collaborative filtering to use feedback, it must be converted to `UserItemInteraction`
3. Model trained via `train_collaborative_model()` Celery task
4. Trained model includes new interaction data
5. **Retraining required** - effect after next training cycle

## Test Data

### Playlist Items (18 items in 3 groups)
- **Group A: Classical Music** (items 1-6) - "liked" group
  - Classical Symphony, Concerto, Sonata, Orchestra, Chamber, Opera
- **Group B: Electronic Dance** (items 7-12) - "disliked" group
  - Electronic Dance Mix, House, Techno, Trance, Dubstep, Drum
- **Group C: Hip Hop Rap** (items 13-18) - neutral/unseen group
  - Hip Hop Rap Song, Beat, Flow, Style, Verse, Rhyme

### User Preferences
- **User likes**: Classical Music items (1-6)
- **User dislikes**: Electronic Dance items (7-12)
- **Expected**: Recommendations should favor Classical Music over Electronic Dance

## Running the Tests

```bash
# Run all feedback loop tests
cd backend
pytest tests/integration/test_feedback_loop_recommendations.py -v

# Run specific test
pytest tests/integration/test_feedback_loop_recommendations.py::TestFeedbackLoopImprovesRecommendations::test_end_to_end_feedback_loop -v

# Run with detailed output
pytest tests/integration/test_feedback_loop_recommendations.py -vv -s
```

## Expected Behavior

### Before Feedback
- Recommendations may be generic or empty (no interaction history)
- Collaborative filtering: May have no data
- Content-based: No liked items to base recommendations on
- Hybrid: Falls back to collaborative or empty

### After Feedback (Content-Based)
- **Immediate effect**: Content-based recommends items similar to liked items
- Example: If user liked "Classical Symphony", recommends "Classical Concerto" (similar title)
- Uses TF-IDF similarity on titles, metadata features (type, channel, duration)

### After Feedback + Retraining (Collaborative Filtering)
- **Delayed effect**: Collaborative filtering incorporates new interactions
- User similarity: Finds users with similar Classical Music preferences
- Item similarity: Recommends items liked by similar users
- Example: If User1 likes Classical items, and User2 also likes Classical items, recommend User2's other Classical items to User1

### After Feedback + Retraining (Hybrid)
- Combines both collaborative and content-based approaches
- Weighted strategy: 0.7 * collaborative_score + 0.3 * content_score
- Items recommended by both algorithms get highest scores

## Verification Steps

### 1. Feedback Submission
```bash
# Check feedback records in database
SELECT COUNT(*), feedback_type
FROM recommendation_feedback
WHERE user_id = 'test-user-id'
GROUP BY feedback_type;
# Expected: 6 likes, 6 dislikes (in E2E test)
```

### 2. Interaction Creation
```bash
# Check interaction records created from feedback
SELECT COUNT(*), interaction_type
FROM user_item_interactions
WHERE user_id = 'test-user-id'
GROUP BY interaction_type;
# Expected: 6 'like' interactions
```

### 3. Model Training
```bash
# Check training logs
# Expected: "Collaborative model trained successfully: X users, Y items"
```

### 4. Updated Recommendations
```bash
# Check recommendations after retraining
# Expected: Recommendations include items similar to user's liked items
```

## Troubleshooting

### Issue: No recommendations after feedback
**Possible causes:**
- Model not retrained (collaborative filtering)
- No liked items found (content-based)
- Insufficient interaction data

**Solution:**
- Verify `train_collaborative_model()` completed successfully
- Check `RecommendationFeedback` table for feedback records
- Check `UserItemInteraction` table for interaction records

### Issue: Recommendations don't reflect feedback
**Possible causes:**
- Wrong algorithm specified (collaborative vs content-based)
- Feedback not converted to interactions (for collaborative filtering)
- Model training failed

**Solution:**
- Use `algorithm="content_based"` for immediate effect
- Use `algorithm="collaborative_filtering"` after retraining
- Check Celery task logs for training errors

### Issue: Model training fails
**Possible causes:**
- Insufficient interaction data
- Database connection issues
- Missing scikit-learn dependencies

**Solution:**
- Verify UserItemInteraction records exist
- Check DATABASE_URL environment variable
- Verify scikit-learn, pandas, numpy installed

## Success Criteria

✅ Feedback submission creates RecommendationFeedback records
✅ Feedback converted to UserItemInteraction records
✅ Model training completes successfully with new data
✅ Content-based recommendations update immediately after feedback
✅ Collaborative filtering recommendations update after retraining
✅ Hybrid recommendations combine both approaches
✅ Recommended items are valid (scores 0-1, correct metadata)
✅ E2E test completes without errors

## Related Tests

- `test_recommendations_track_play_integration.py` - TrackPlay → UserItemInteraction flow
- `test_collaborative_filtering_recommendations.py` - Collaborative filtering algorithm
- `test_content_based_filtering_recommendations.py` - Content-based filtering
- `test_hybrid_recommendations.py` - Hybrid recommendation system

## Notes

- Feedback affects content-based filtering **immediately** (no retraining)
- Feedback affects collaborative filtering **after retraining** (requires Celery task)
- Hybrid recommender combines both immediate and delayed effects
- Feedback cache is invalidated on submission (Redis keys deleted)
- Recommendations are logged to `recommendations` table for analytics
