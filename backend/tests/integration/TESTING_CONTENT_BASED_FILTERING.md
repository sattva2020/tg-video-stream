# Content-Based Filtering Integration Tests

## Overview

This document describes the integration tests for content-based filtering recommendations. Content-based filtering recommends items similar to those a user has liked in the past, based on item metadata similarity.

## Test File

**File**: `backend/tests/integration/test_content_based_filtering_recommendations.py`

## Test Structure

### Fixtures

#### `content_based_test_items`
Creates 20 PlaylistItem items across 4 metadata similarity groups:
- **Group A (Rock Music)**: 5 items with titles containing "Rock Music"
  - Rock Music Anthem, Rock Music Ballad, Rock Music Hits, Rock Music Festival, Rock Music Classics
- **Group B (Pop Song)**: 5 items with titles containing "Pop Song"
  - Pop Song Summer, Pop Song Dance, Pop Song Love, Pop Song Party, Pop Song Hits
- **Group C (Jazz Classics)**: 5 items with titles containing "Jazz Classics"
  - Jazz Classics Blue, Jazz Classics Night, Jazz Classics Smooth, Jazz Classics Modern, Jazz Classics Soul
- **Group D (Electronic Beats)**: 5 items with titles containing "Electronic Beats"
  - Electronic Beats Deep, Electronic Beats House, Electronic Beats Techno, Electronic Beats Ambient, Electronic Beats Trance

Each group has:
- Similar titles (for TF-IDF similarity)
- Different types (youtube/local)
- Different durations (175-260 seconds)
- Unique channel_id per group

#### `test_user`
Creates a single test user for recommendations testing.

#### `recommendation_service`
Creates a RecommendationService instance with database session.

#### Helper Function: `create_user_interactions_for_content`
Creates UserItemInteraction records for testing user preferences.

## Test Methods

### 1. `test_create_playlist_items_with_similar_metadata`
**Purpose**: Verify that test data is created correctly with similar metadata groups.

**Steps**:
1. Create 20 PlaylistItem with 4 groups of similar titles
2. Verify each group has 5 items
3. Verify metadata (title, channel_id) is correct

**Expected Result**: 20 items created with 4 distinct metadata similarity groups.

### 2. `test_train_content_based_model`
**Purpose**: Verify that content-based model trains successfully.

**Steps**:
1. Call `train_content_based_model()`
2. Verify training success
3. Check metrics (items_count, trained_at)

**Expected Result**: Model trains successfully with 20 items.

### 3. `test_fetch_content_based_recommendations_for_liked_rock_items`
**Purpose**: Verify content-based recommendations for a user who likes Rock Music.

**Steps**:
1. User likes all 5 "Rock Music" items
2. Train content-based model
3. Fetch recommendations with `algorithm="content_based"`
4. Verify recommendations exclude already liked items
5. Verify algorithm and scores are correct

**Expected Result**: User gets recommendations based on Rock Music similarity.

### 4. `test_verify_content_based_similarity_by_title`
**Purpose**: Verify that content-based filtering recommends items with similar titles.

**Steps**:
1. User likes 2 specific "Pop Song" items
2. Train content-based model
3. Fetch recommendations
4. Verify recommended items include other "Pop Song" items

**Expected Result**: Recommendations include items with similar titles ("Pop Song...").

### 5. `test_find_similar_items_directly`
**Purpose**: Test the `find_similar_items()` method directly.

**Steps**:
1. Train content-based model
2. Call `find_similar_items()` for "Rock Music Anthem"
3. Verify similar items are returned
4. Check that similar items have "Rock" in titles

**Expected Result**: Method returns items with similar titles and valid scores.

### 6. `test_content_based_with_different_types_and_durations`
**Purpose**: Verify content-based filtering considers type and duration metadata.

**Steps**:
1. User likes youtube Rock Music items (duration ~180-200s)
2. Train content-based model
3. Fetch recommendations
4. Verify recommendations consider type and duration

**Expected Result**: Recommendations based on combined metadata similarity (title + type + duration).

### 7. `test_end_to_end_content_based_filtering`
**Purpose**: End-to-end test of content-based filtering pipeline.

**Steps**:
1. User likes all 5 "Jazz Classics" items
2. Verify interactions in database
3. Train content-based model
4. Fetch recommendations
5. Verify recommendations exclude liked items
6. Verify recommendations have valid metadata

**Expected Result**: Full E2E pipeline works correctly.

### 8. `test_content_based_similarity_across_groups`
**Purpose**: Verify similarity is computed correctly within groups, not between groups.

**Steps**:
1. Train content-based model
2. For each genre (Rock, Pop, Jazz, Electronic), find similar items
3. Verify similar items are from the same genre
4. Verify scores are sorted in descending order

**Expected Result**: Items are similar within genre groups, not across them.

## How Content-Based Filtering Works

### Algorithm Steps

1. **Feature Extraction**:
   - **TF-IDF** on titles (max_features=100, ngram_range=(1,2))
   - **One-hot encoding** for type (youtube/local/stream)
   - **Categorical encoding** for channel_id
   - **StandardScaler** for duration normalization

2. **Feature Combination**:
   - All features combined into sparse matrix using `sparse_hstack()`

3. **Similarity Computation**:
   - Cosine similarity matrix computed for all item pairs
   - Formula: `similarity = cosine_similarity(item_features_matrix)`

4. **Recommendation Generation**:
   - For user, get liked items
   - For each liked item, find similar items using similarity matrix
   - Aggregate scores (average similarity across all liked items)
   - Sort by score and return top-N

### Key Differences from Collaborative Filtering

| Aspect | Collaborative Filtering | Content-Based Filtering |
|--------|------------------------|-------------------------|
| **Data Source** | User-item interactions | Item metadata |
| **Recommendation Basis** | Similar users' preferences | Similar item attributes |
| **Cold Start** | Needs interaction history | Works with metadata only |
| **Similarity Metric** | User-user or item-item interactions | Cosine similarity of features |
| **Use Case** | "Users like you also liked..." | "Because you liked X, you might like Y" |

## Running the Tests

```bash
# Run all content-based filtering tests
cd backend
pytest tests/integration/test_content_based_filtering_recommendations.py -v

# Run specific test
pytest tests/integration/test_content_based_filtering_recommendations.py::TestContentBasedFilteringRecommendations::test_end_to_end_content_based_filtering -v

# Run with detailed output
pytest tests/integration/test_content_based_filtering_recommendations.py -v -s
```

## Expected Output

Successful test run should show:
```
✓ Created 20 items with similar metadata: 5 rock, 5 pop, 5 jazz, 5 electronic
✓ Content-based model trained: 20 items, trained at 2026-01-23...
✓ User who liked Rock Music got N content-based recommendations
✓ Content-based filtering: N out of N recommendations have similar titles
✓ Items similar to 'Rock Music Anthem': ['Rock Music Ballad', 'Rock Music Hits', ...]
✓ Content-based recommendations by type: {'youtube': N, 'local': N}
✓ Created 5 user interactions for Jazz Classics
✓ Content-based model trained: 20 items
✓ User got N content-based recommendations
✓ E2E content-based filtering test passed
✓ Rock: 5/5 similar items from same genre
✓ Pop: 5/5 similar items from same genre
✓ Jazz: 5/5 similar items from same genre
✓ Electronic: 5/5 similar items from same genre
```

## Verification Checklist

Before considering this subtask complete, verify:

- [x] Test file created with 8 test methods
- [x] Fixtures create test data with similar metadata
- [x] Tests verify content-based model training
- [x] Tests verify recommendations based on title similarity
- [x] Tests verify `find_similar_items()` method
- [x] Tests verify metadata features (type, duration) are considered
- [x] E2E test validates full pipeline
- [x] Tests follow pattern from `test_collaborative_filtering_recommendations.py`
- [x] Russian comments throughout
- [x] Documentation file created

## Troubleshooting

### Common Issues

1. **Model training fails**:
   - Verify database has at least 2 PlaylistItem
   - Check that items have titles, types, durations

2. **No recommendations returned**:
   - Verify user has liked items (UserItemInteraction records)
   - Check that exclude_watched doesn't exclude all items
   - Ensure model is trained before calling predict

3. **Incorrect similarity**:
   - Verify TF-IDF vectorizer parameters
   - Check cosine similarity matrix computation
   - Ensure features are properly combined

## Notes

- Content-based filtering works well even with no interaction history (unlike collaborative filtering)
- TF-IDF captures word importance in titles (e.g., "Rock" in "Rock Music")
- Similarity scores range from 0 to 1 (cosine similarity)
- Multiple features (title, type, duration) are combined for better recommendations
