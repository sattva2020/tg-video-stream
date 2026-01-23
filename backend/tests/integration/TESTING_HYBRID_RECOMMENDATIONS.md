# Testing Hybrid Recommendations

## Overview

This integration test verifies that the hybrid recommendation system correctly combines collaborative filtering and content-based filtering strategies to provide recommendations.

## Test File

`test_hybrid_recommendations.py` - Comprehensive test suite for hybrid recommendations

## Test Data

### Playlist Items (20 items)

The test creates 20 playlist items organized into 4 metadata similarity groups:

- **Group A (items 0-4)**: "Rock Music..." - Similar titles for content-based filtering
  - Rock Music Anthem
  - Rock Music Ballad
  - Rock Music Hits
  - Rock Music Festival
  - Rock Music Classics

- **Group B (items 5-9)**: "Pop Song..." - Similar titles for content-based filtering
  - Pop Song Summer
  - Pop Song Dance
  - Pop Song Love
  - Pop Song Party
  - Pop Song Hits

- **Group C (items 10-14)**: "Jazz Classics..." - Similar titles for content-based filtering
  - Jazz Classics Blue
  - Jazz Classics Night
  - Jazz Classics Smooth
  - Jazz Classics Modern
  - Jazz Classics Soul

- **Group D (items 15-19)**: "Electronic Beats..." - Similar titles for content-based filtering
  - Electronic Beats Deep
  - Electronic Beats House
  - Electronic Beats Techno
  - Electronic Beats Ambient
  - Electronic Beats Trance

### Users (3 users)

- **User1**: Likes Rock Music (high completion rate on items 0-4)
- **User2**: Likes Pop Song (high completion rate on items 5-9)
- **User3**: Likes Jazz Classics (high completion rate on items 10-14)

## Algorithm Details

### Hybrid Recommendation Strategy

The hybrid recommender combines collaborative filtering and content-based filtering using one of three strategies:

1. **Weighted Hybrid** (default, tested):
   - Formula: `final_score = 0.7 * collaborative_score + 0.3 * content_score`
   - Combines scores from both algorithms
   - Items recommended by both algorithms get higher scores

2. **Switching Hybrid**:
   - Uses collaborative filtering if avg_collaborative_score >= 0.3
   - Falls back to content-based otherwise

3. **Cascade Hybrid**:
   - Takes 70% from collaborative filtering
   - Fills remaining slots with content-based recommendations

### Collaborative Filtering

- Uses TruncatedSVD for matrix factorization
- Calculates ratings from interactions:
  - like = 5.0
  - share = 4.5
  - watch = 2.0-4.0 (based on completion_rate)
  - click = 1.5
  - skip = 0.5
- Finds similar users based on interaction patterns
- Recommends items liked by similar users

### Content-Based Filtering

- Uses TF-IDF vectorization on titles (max_features=100, ngram_range=(1,2))
- One-hot encoding for type (youtube/local/stream)
- Categorical encoding for channel_id
- StandardScaler for duration normalization
- Cosine similarity matrix for item-item similarity
- Recommends items similar to user's liked items

## Test Cases

### Test 1: Create Test Data
**Purpose**: Verify test data creation
**Checks**:
- 20 playlist items created
- 4 groups with similar titles (5 items each)
- 3 test users created

### Test 2: Train Both Models
**Purpose**: Train collaborative and content-based models
**Steps**:
1. Create user interactions (User1→Rock, User2→Pop, User3→Jazz)
2. Train collaborative model via Celery task
3. Train content-based model via Celery task
**Checks**:
- Collaborative model trained with >=3 users, >=15 items
- Content-based model trained with all 20 items
- Models saved successfully

### Test 3: Fetch Hybrid Recommendations (Weighted)
**Purpose**: Verify hybrid recommendations work
**Steps**:
1. Fetch recommendations with algorithm='hybrid'
2. Check response structure
**Checks**:
- Recommendations returned (not empty)
- All scores in range 0-1
- Algorithm field = 'hybrid'

### Test 4: Verify Combines Both Strategies
**Purpose**: Confirm hybrid combines collaborative and content-based
**Steps**:
1. Fetch collaborative recommendations
2. Fetch content-based recommendations
3. Fetch hybrid recommendations
4. Compare IDs across all three sets
**Checks**:
- Hybrid includes items from collaborative recommendations
- Hybrid includes items from content-based recommendations
- Hybrid is not identical to either individual algorithm

### Test 5: Confidence Scores Are Reasonable
**Purpose**: Verify score quality
**Steps**:
1. Fetch recommendations from all algorithms
2. Analyze score distribution
**Checks**:
- All scores in range 0-1
- Scores vary (not all identical)
- Average score in reasonable range (0.1-0.9)
- Score statistics logged

### Test 6: Different Strategies
**Purpose**: Test different hybrid strategies
**Note**: Currently tests default/weighted strategy (API may not support strategy selection)
**Checks**:
- Recommendations returned
- Algorithm field indicates hybrid variant

### Test 7: End-to-End Hybrid Recommendations
**Purpose**: Complete E2E workflow
**Steps**:
1. Use existing test data and trained models
2. Fetch recommendations for all 3 users
**Checks**:
- Each user receives recommendations
- All scores valid (0-1)
- No errors or crashes

### Test 8: Hybrid Recommendations Quality
**Purpose**: Verify recommendation quality
**Steps**:
1. Fetch recommendations with exclude_watched=True
2. Check for duplicates
3. Verify watched items excluded
**Checks**:
- No duplicate items in recommendations
- Watched items excluded from recommendations
- Recommendations relevant to user preferences

## Running the Tests

```bash
# Run all hybrid recommendation tests
cd backend
pytest tests/integration/test_hybrid_recommendations.py -v

# Run specific test
pytest tests/integration/test_hybrid_recommendations.py::test_fetch_hybrid_recommendations_weighted -v

# Run with detailed output
pytest tests/integration/test_hybrid_recommendations.py -vv -s
```

## Expected Behavior

1. **Data Creation**: 20 items with metadata similarity + 3 users with different tastes
2. **Model Training**: Both models train successfully without errors
3. **Hybrid Recommendations**: Combine results from both algorithms
4. **Score Quality**: All scores in 0-1 range, varied distribution
5. **No Duplicates**: Each item appears at most once in recommendations
6. **Exclusions**: Watched items excluded when exclude_watched=True

## Comparison with Other Algorithms

| Algorithm | Data Source | Recommendation Logic | Pros | Cons |
|-----------|-------------|---------------------|------|------|
| **Collaborative Filtering** | User-item interactions | Similar users → their liked items | Good for discovering new content, personalized | Cold start problem, needs interaction data |
| **Content-Based Filtering** | Item metadata (title, type, duration, channel) | Similar items to user's liked items | No cold start, transparent | Limited to similar content, no discovery |
| **Hybrid** | Both interactions + metadata | Combines both with weights/strategies | Best of both, robust | More complex, requires both models trained |

## Key Differences from Other Tests

- **test_collaborative_filtering_recommendations.py**: Focuses on user similarity, tests with generic genre titles
- **test_content_based_filtering_recommendations.py**: Focuses on metadata similarity, tests TF-IDF on titles
- **test_hybrid_recommendations.py**: Combines both, verifies combination strategies and score aggregation

## Troubleshooting

### Issue: No recommendations returned
**Possible causes**:
- Models not trained (run Tests 2 first)
- No user interactions created
- Insufficient data for algorithms

**Solution**: Ensure tests run in order, check models trained successfully

### Issue: All scores are 0 or identical
**Possible causes**:
- Model training failed
- Insufficient interaction data
- All users have identical interactions

**Solution**: Check model training logs, verify user interactions differ

### Issue: Hybrid identical to collaborative or content-based
**Possible causes**:
- One algorithm returning empty results
- Weighted combination with one weight = 0
- Cache not invalidated

**Solution**: Check both algorithms return results, verify weights (0.7/0.3), clear cache

## Success Criteria

- ✅ All 8 tests pass
- ✅ Hybrid recommendations combine both algorithms
- ✅ Scores in valid range (0-1)
- ✅ No duplicates in recommendations
- ✅ Watched items properly excluded
- ✅ Reasonable score distribution
