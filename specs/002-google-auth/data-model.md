# Data Model: User Authentication with Google

**Feature Branch**: `002-google-auth`
**Created**: 17.11.2025
**Status**: Draft

## Entities

### User

**Description**: Represents a user account within the application, linked to a Google identity.

**Attributes**:

*   **id** (UUID/Integer): Unique primary identifier for the user within the application.
*   **google_id** (String): Unique identifier provided by Google for the user's Google account. (Indexed, Unique)
*   **email** (String): User's email address from Google. (Indexed, Unique)
*   **full_name** (String): User's full name from Google.
*   **profile_picture_url** (String, Optional): URL to the user's profile picture from Google.
*   **created_at** (Timestamp): Timestamp when the user account was created.
*   **updated_at** (Timestamp): Timestamp when the user account was last updated.

**Relationships**:

*   None directly defined for this feature.

**Validation Rules**:

*   `google_id` MUST be unique.
*   `email` MUST be unique and a valid email format.
*   `full_name` MUST NOT be empty.
