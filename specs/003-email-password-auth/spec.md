# Feature Specification: Email & Password Authentication

**Feature Branch**: `003-email-password-auth`
**Created**: 2025-11-18
**Status**: Draft
**Input**: User description: "Добавить классическую аутентификацию (email/пароль)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - User Registration (Priority: P1)

As a new user, I want to register for an account using my email and a password, so that I can access the application without using a Google account.

**Why this priority**: This is a core feature that provides an alternative way for users to join the platform, increasing accessibility.

**Independent Test**: A new user can visit the registration page, fill in their email and password, and successfully create a new account.

**Acceptance Scenarios**:

1.  **Given** a user is on the registration page, **When** they enter a valid email and a secure password and submit the form, **Then** a new user account is created in the system and they are logged in and redirected to the dashboard.
2.  **Given** a user is on the registration page, **When** they attempt to register with an email that already exists, **Then** the system shows an error message indicating the email is already taken.
3.  **Given** a user is on the registration page, **When** they enter an invalid email or a weak password, **Then** the system shows a validation error message.

---

### User Story 2 - User Login (Priority: P1)

As a registered user, I want to log in to the application using my email and password so that I can access my account.

**Why this priority**: This allows registered users to access their accounts, which is fundamental to using the application.

**Independent Test**: An existing user can visit the login page, enter their correct credentials, and be successfully logged in.

**Acceptance Scenarios**:

1.  **Given** a user has an existing account, **When** they enter their correct email and password on the login page, **Then** the system authenticates them, creates a session, and redirects them to the dashboard.
2.  **Given** a user has an existing account, **When** they enter an incorrect password, **Then** the system shows an "Invalid credentials" error message.

---

### User Story 3 - Password Reset (Priority: P3)

As a registered user who has forgotten my password, I want to be able to reset it so that I can regain access to my account.

**Why this priority**: This is a standard self-service feature that reduces user frustration and support load, but it is less critical than the core registration/login flow for the MVP.

**Independent Test**: A user can request a password reset link via email, and use that link to set a new password.

**Acceptance Scenarios**:

1.  **Given** a user is on the login page, **When** they click the "Forgot Password" link and enter their email, **Then** the system sends a password reset link to their email if the account exists.
2.  **Given** a user has a valid password reset link, **When** they navigate to the link and enter a new secure password, **Then** their password is updated and they can log in with the new password.

---

### Edge Cases

-   How does the system handle repeated failed login attempts for an account (e.g., rate limiting, account lockout)?
-   Password reset links should have a limited expiration time (e.g., 1 hour).

## Requirements *(mandatory)*

### Functional Requirements

-   **FR-001**: The system MUST provide a registration form with fields for email and password.
-   **FR-002**: The system MUST validate that the provided email is in a valid format.
-   **FR-003**: The system MUST enforce password complexity rules (e.g., minimum 8 characters).
-   **FR-004**: The system MUST securely hash and salt user passwords before storing them in the database.
-   **FR-005**: The system MUST NOT allow registration of an email address that is already in use.
-   **FR-006**: The system MUST provide a login form with fields for email and password.
-   **FR-007**: The system MUST validate the user's credentials against the stored hash upon login.
-   **FR-008**: Upon successful login, the system MUST create a user session (e.g., via JWT or session cookie).

### Key Entities *(include if feature involves data)*

-   **User**: The existing User entity will be modified.
    | Attribute | Change | Description |
    |---|---|---|
    | `hashed_password` | Add | A string to store the salted hash of the user's password. Will be `NULL` for users who registered via Google. |
    | `google_id` | Modify | This field will now be nullable, as users registering with email/password will not have a Google ID. |

## Success Criteria *(mandatory)*

### Measurable Outcomes

-   **SC-001**: A new user can complete the email/password registration process in under 90 seconds.
-   **SC-002**: A returning user can log in with their email and password in under 10 seconds.
-   **SC-003**: The login and registration API endpoints MUST have a success rate of over 99%.

## Assumptions

-   A third-party service or local mail server will be available for sending password reset emails.
-   Password complexity will be enforced on the client-side (for immediate feedback) and re-validated on the server-side.