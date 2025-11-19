# Feature Specification: Email & Password Authentication

**Feature Branch**: `004-email-password-auth`
**Created**: 2025-11-18
**Status**: Draft
**Input**: User description: "2. Добавить классическую аутентификацию (email/пароль) Сейчас система работает только с Google. Можно добавить традиционную регистрацию и вход по электронной почте и паролю. Это сделает приложение доступным для пользователей, которые не хотят использовать аккаунт Google. * Что для этого нужно: * Добавить поле hashed_password в модель User. * Создать эндпоинты для регистрации, входа и, возможно, сброса пароля. * Добавить на фронтенде соответствующие формы."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New User Registration (Priority: P1)

As a new user, I want to create an account using my email address and a password, so that I can access the application without needing a Google account.

**Why this priority**: This is the core functionality that enables access for a new segment of users, directly addressing the main goal of the feature.

**Independent Test**: A user can navigate to a registration page, enter their email and a password, and successfully create an account. Upon completion, they should be logged in or directed to the login page.

**Acceptance Scenarios**:

1.  **Given** a user is on the registration page, **When** they enter a valid, unique email address and a compliant password, **Then** their account is created successfully.
2.  **Given** a user is on the registration page, **When** they enter an email address that is already registered, **Then** they are shown an error message indicating the email is already in use.
3.  **Given** a user is on the registration page, **When** they enter a password that does not meet complexity requirements, **Then** they are shown an error message detailing the requirements.

---

### User Story 2 - Existing User Login (Priority: P1)

As a registered user, I want to log in to my account using my email and password, so that I can access my data and use the application.

**Why this priority**: This is essential for users who have registered to be able to re-access their accounts.

**Independent Test**: A user can navigate to a login page, enter the credentials of a previously created account, and successfully access the application.

**Acceptance Scenarios**:

1.  **Given** a user with a registered email/password account exists, **When** they enter their correct email and password on the login page, **Then** they are successfully authenticated and granted access.
2.  **Given** a user with a registered email/password account exists, **When** they enter an incorrect password, **Then** they are shown an "invalid credentials" error message.

---

### User Story 3 - Password Recovery (Priority: P2)

As a user who has forgotten my password, I want to request a password reset link via email so that I can regain access to my account.

**Why this priority**: While not as critical as initial login, this is a standard and expected feature for user autonomy and reduces support load.

**Independent Test**: A user can go to the login page, click "Forgot Password", enter their email, receive an email, and follow the link to successfully set a new password.

**Acceptance Scenarios**:

1.  **Given** a user has an existing account, **When** they request a password reset for their email address, **Then** they receive an email containing a unique, time-sensitive link to reset their password.
2.  **Given** a user has clicked the reset link from their email, **When** they enter and confirm a new, compliant password, **Then** their password is updated, and they can log in with the new password.
3.  **Given** a user has requested a password reset, **When** they use an expired or invalid link, **Then** they are shown a message explaining the link is invalid and prompted to request a new one.

## Requirements *(mandatory)*

### Functional Requirements

+ **FR-001**: The system MUST provide a user interface for new users to register with an email address and a password.
+ **FR-002**: The system MUST provide a user interface for existing users to log in with their email address and password.
+ **FR-003**: The system MUST validate that the provided email address is in a valid format during registration.
+ **FR-004**: The system MUST enforce a set of password complexity rules (e.g., minimum length, character types).
  + Implementation note: define exact policy in `specs/004-email-password-auth/plan.md` and enforce server-side. Recommended baseline policy:
    + minimum length: 12 characters
    + must contain at least: 1 uppercase, 1 lowercase, 1 digit, 1 special character
    + reject easily-guessed passwords (common/password list), optionally consult Have I Been Pwned API for breached passwords (optional)
+ **FR-005**: The system MUST ensure that user passwords are not stored in plaintext and are securely managed.
+ **FR-006**: The system MUST provide a full, self-service password recovery mechanism. This includes a "Forgot Password" feature that sends a secure reset link to the user's registered email address.
 
## User Story 4 - Account Linking (Priority: P2)

As a user who originally registered via Google OAuth, I want to be able to sign in with Google and optionally link or create an email/password credential, so that I can use either login method securely.

**Why this priority**: Prevent duplicate accounts / confusion when a user later tries to sign up with email matching their Google account.

**Independent Test**: A user who has signed in with Google cannot create a second, separate account by registering with the same email address; instead, the system presents linking options or instructs to sign in with Google.

**Acceptance Scenarios**:

1.  **Given** a user has an existing Google-auth account, **When** they attempt to register with the same email via email/password, **Then** the system displays a message that the email is already used and provides a link to sign in via Google or to link accounts after verifying ownership.
2.  **Given** a user signed up via Google and has access to the email, **When** they choose to set a password and link accounts, **Then** the system allows them to set a password after verification and save `hashed_password` for future email logins.

### Key Entities *(include if feature involves data)*

-   **User**: Represents an individual with access to the system. For this feature, it will include authentication credentials associated with an email address.

## Success Criteria *(mandatory)*

### Measurable Outcomes

-   **SC-001**: New users can complete the email/password registration process and log in for the first time in under 90 seconds.
-   **SC-002**: The success rate for new user registrations (for users providing valid data) is at least 98%.
-   **SC-003**: The introduction of email/password authentication increases the overall user sign-up rate by at least 10% within the first month post-launch.
-   **SC-004**: The login success rate for returning email/password users is at least 99%.
-   **SC-005**: Users can successfully reset their password using the self-service flow in under 3 minutes.