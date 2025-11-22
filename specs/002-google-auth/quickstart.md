# Quickstart Guide: User Authentication with Google

**Feature Branch**: `002-google-auth`
**Created**: 17.11.2025
**Status**: Draft

## Overview

This guide provides a quick overview of how to set up and test the Google Authentication feature. It assumes the backend and frontend services are running and configured correctly with Google OAuth 2.0 credentials.

## Prerequisites

1.  **Google OAuth 2.0 Credentials**:
    *   A Google Cloud Project with OAuth 2.0 Client ID and Client Secret.
    *   Authorized redirect URIs configured for your backend callback (e.g., `http://localhost:8000/api/v1/auth/google/callback`).
2.  **Backend Service**: Running and accessible (e.g., `http://localhost:8000`).
3.  **Frontend Service**: Running and accessible (e.g., `http://localhost:3000`).

## Testing the Flow

### 1. Initiate Google Login (Frontend)

*   Navigate to the frontend application's login page (e.g., `http://localhost:3000/login`).
*   Click the "Sign in with Google" button.
*   You will be redirected to Google's consent screen. Authenticate with your Google account and grant the necessary permissions.
*   Upon successful authentication, Google will redirect you back to your frontend application. The frontend will then communicate with the backend's `/auth/google/callback` endpoint.

### 2. Verify Backend Interaction

*   The backend's `/auth/google/callback` endpoint will receive the authorization code from Google.
*   It will exchange this code for Google tokens, fetch user information, and either create a new user or log in an existing one.
*   The backend will issue an application-specific JWT access token to the frontend.

### 3. Access Authenticated Resources

*   Once logged in, the frontend should store the received JWT access token.
*   You can then test authenticated endpoints, for example, by making a request to `GET /api/v1/users/me` with the `Authorization: Bearer <your_jwt_token>` header.

## Example API Calls (using `curl`)

### Initiate Google OAuth (Backend - for direct testing, usually done via frontend)

```bash
# This is typically handled by the frontend redirect.
# For direct testing, you would manually construct the Google OAuth URL.
# Example (replace with your actual client_id and redirect_uri):
# https://accounts.google.com/o/oauth2/v2/auth?
#   scope=openid%20profile%20email&
#   access_type=offline&
#   include_granted_scopes=true&
#   response_type=code&
#   state=security_string&
#   redirect_uri=http://localhost:8000/api/v1/auth/google/callback&
#   client_id=YOUR_GOOGLE_CLIENT_ID
```

### Logout

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
     -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```

### Get Current User Profile

```bash
curl -X GET "http://localhost:8000/api/v1/users/me" \
     -H "Authorization: Bearer <YOUR_JWT_TOKEN>"
```
