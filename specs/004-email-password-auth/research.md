# Research: Email & Password Authentication

This document outlines the research and decisions made for selecting technologies to implement email and password-based authentication.

## 1. Password Hashing

**Requirement**: The system must securely store user passwords by hashing them.

**Analysis**: The existing `backend/requirements.txt` does not include a dedicated password hashing library. `passlib` is the de-facto standard for this purpose in the Python ecosystem due to its simplicity and strong security.

-   **Decision**: Use `passlib` with the `bcrypt` algorithm.
-   **Rationale**:
    -   `bcrypt` is a strong, adaptive hashing algorithm specifically designed for passwords.
    -   `passlib` provides a simple, high-level API for hashing and verifying passwords, handling salt generation automatically.
-   **Alternatives Considered**:
    -   **`werkzeug.security`**: While effective, it's part of the Werkzeug library (a Flask dependency) and would be an unnecessary addition to a FastAPI project.
    -   **Manual `hashlib`**: Using Python's built-in `hashlib` is too low-level and error-prone for password security, as it doesn't handle salting or adaptive hashing correctly without significant manual implementation.

## 2. Secure Token Generation (for Password Reset)

**Requirement**: A secure, temporary token must be generated and sent to the user for password recovery.

**Analysis**: The `backend/requirements.txt` file already lists `itsdangerous`. This library is specifically designed for signing data to prevent tampering, making it ideal for generating secure tokens for password resets, email confirmations, etc.

-   **Decision**: Use the existing `itsdangerous` dependency.
-   **Rationale**:
    -   It's already part of the project, so no new dependency is needed.
    -   It provides a `URLSafeTimedSerializer` that can create tokens that are URL-safe, signed, and expire after a specified time. This is exactly what is needed for a password reset link.
-   **Alternatives Considered**:
    -   **Python `secrets` module**: Could be used to generate a raw token, but it would require manual implementation for signing, timestamping, and serialization, which `itsdangerous` handles out of the box.

## 3. Email Sending

**Requirement**: The system must be able to send emails to users for password recovery.

**Analysis**: There is no email library currently listed in `backend/requirements.txt`. `fastapi-mail` is a popular choice for FastAPI applications.

-   **Decision**: Use `fastapi-mail`.
-   **Rationale**:
    -   It is designed specifically for FastAPI, providing simple integration.
    -   It supports asynchronous email sending, which is crucial for a non-blocking application like FastAPI.
    -   It supports templates, which will be useful for formatting the password reset email.
-   **Alternatives Considered**:
    -   **`smtplib`**: Python's built-in library is very low-level and would require significant boilerplate code to use within an async FastAPI application.
    -   **SendGrid/Mailgun SDKs**: Using a specific service's SDK would lock the application into that provider. A generic library like `fastapi-mail` is more flexible as it can be configured with any SMTP provider.
