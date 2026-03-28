# Collaborative Filtering Integration Tests

## Overview
This test suite verifies the collaborative filtering recommendation system with simulated users.

## Test File
`test_collaborative_filtering_recommendations.py`

## Test Structure

### Fixtures
1. **test_playlist_items** - Creates 20 playlist items across 3 genres:
   - Rock (items 1-7)
   - Pop (items 8-14)
   - Jazz (items 15-20)

2. **test_users** - Creates 5 test users with different preferences

3. **recommendation_service** - RecommendationService instance

### Helper Functions
- **create_user_interactions()** - Creates UserItemInteraction records with specified completion rates

### Test Cases

#### 1. test_create_simulated_users_with_similar_patterns
- Creates users with similar viewing patterns
- User1 & User2: Rock lovers
- User3: Pop lover
- User4 & User5: Jazz lovers
- Verifies interactions are created correctly

#### 2. test_train_collaborative_filtering_model
- Trains the collaborative filtering model via Celery task
- Verifies model metrics:
  - users_count ≥ 5
  - items_count ≥ 15
  - interactions_count ≥ 35
  - explained_variance > 0

#### 3. test_fetch_recommendations_for_similar_users
- Fetches recommendations for User1 and User2 (both rock lovers)
- Verifies recommendations are returned
- Checks for overlapping recommendations between similar users

#### 4. test_verify_collaborative_filtering_working
- Compares recommendations for users with different tastes
- Rock lover vs Pop lover
- Verifies recommendations are not identical (overlap < 100%)

#### 5. test_end_to_end_collaborative_filtering
- Complete E2E test:
  1. Creates interactions for all user groups
  2. Trains model
  3. Fetches recommendations for each user
  4. Verifies overlap for similar users (rock group, jazz group)
  5. Verifies differentiation for different tastes (rock vs pop)

## Running the Tests

```bash
cd backend
pytest tests/integration/test_collaborative_filtering_recommendations.py -v
```

## Expected Behavior

- Users with similar tastes should receive overlapping recommendations
- Users with different tastes should receive different recommendations
- Collaborative filtering model should train successfully
- Recommendations should have valid scores (0-1)

## Verification Steps

✅ Create test users with similar viewing patterns
✅ Trigger model training via Celery
✅ Fetch recommendations for similar users
✅ Verify recommendations overlap (collaborative filtering working)
