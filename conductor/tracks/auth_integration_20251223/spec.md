# Spec: User Authentication Flow with Email/Password and Telegram Integration

## 1. Overview

This document specifies the requirements for implementing a user authentication system that combines traditional email/password registration with Telegram-based verification. The goal is to provide a secure and user-friendly authentication flow that leverages the existing Telegram infrastructure for user verification and bot interaction.

## 2. Functional Requirements

### 2.1. User Registration

-   **Endpoint:** `POST /api/auth/register`
-   **Request Body:**
    -   `email` (string, required)
    -   `password` (string, required, min 8 characters)
    -   `telegram_username` (string, required)
-   **Process:**
    1.  The system shall accept user registration details.
    2.  A new user record shall be created with a `pending_verification` status.
    3.  The system shall send a unique verification code to the user's provided Telegram username via a Telegram bot.
    4.  The system shall return a success message indicating that a verification code has been sent.

### 2.2. User Verification

-   **Endpoint:** `POST /api/auth/verify`
-   **Request Body:**
    -   `email` (string, required)
    -   `verification_code` (string, required)
-   **Process:**
    1.  The system shall validate the provided verification code against the one sent to the user's Telegram.
    2.  Upon successful validation, the user's status shall be updated to `active`.
    3.  A JSON Web Token (JWT) shall be generated and returned to the user for subsequent authenticated requests.

### 2.3. User Login

-   **Endpoint:** `POST /api/auth/login`
-   **Request Body:**
    -   `email` (string, required)
    -   `password` (string, required)
-   **Process:**
    1.  The system shall authenticate the user based on their email and password.
    2.  If the credentials are valid and the user's account is `active`, a new JWT shall be generated and returned.
    3.  If the account is `pending_verification`, the system shall return an error message prompting the user to verify their account.

### 2.4. Telegram Bot Interaction

-   The system shall include a Telegram bot responsible for:
    -   Sending verification codes to new users.
    -   Responding to basic commands (e.g., `/start`, `/help`).

## 3. Non-Functional Requirements

### 3.1. Security

-   Passwords shall be securely hashed and salted before being stored in the database.
-   The verification code shall be time-sensitive and expire after a configurable duration (e.g., 15 minutes).
-   All communication between the client and server shall be over HTTPS.

### 3.2. Performance

-   API response times for authentication endpoints should be under 500ms under normal load.

### 3.3. Scalability

-   The authentication service should be horizontally scalable.

## 4. Out of Scope

-   Password reset functionality.
-   Social login (e.g., Google, GitHub).
-   Two-factor authentication (other than Telegram verification).
