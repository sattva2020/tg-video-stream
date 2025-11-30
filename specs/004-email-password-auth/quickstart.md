# Quickstart Guide: Email & Password Authentication

This guide provides a high-level overview of the steps a developer should take to implement the email and password authentication feature.

## 1. Setup Backend Dependencies

1.  **Add New Libraries**: Add the following libraries to `backend/requirements.txt`:
    ```
    passlib[bcrypt]
    fastapi-mail
    ```

2.  **Install Dependencies**: Refresh the virtual environment to install the new packages.
    ```bash
    # Deactivate and reactivate venv or run:
    pip install -r backend/requirements.txt
    ```

## 2. Update the Database

1.  **Create a Migration**: Use Alembic to generate a new migration file that adds the `hashed_password` column to the `users` table.
    ```bash
    # From the `backend` directory
    alembic revision --autogenerate -m "Add hashed_password to users table"
    ```

2.  **Review and Apply Migration**: Inspect the generated migration script in `backend/alembic/versions/` to ensure it's correct, then apply it to the database.
    ```bash
    # From the `backend` directory
    alembic upgrade head
    ```

## 3. Implement Backend Logic

1.  **Create Authentication Utilities**:
    *   In a new file, e.g., `backend/src/auth/password.py`, create functions to `hash_password` and `verify_password` using `passlib`.

2.  **Configure Email**:
    *   Update the application's configuration (e.g., in `.env` and `config.py`) to include SMTP server settings for `fastapi-mail`.
    *   Create an email utility service to send the password reset email using templates.

3.  **Implement API Endpoints**:
    *   In `backend/src/api/auth.py` (or a new dedicated file), add the new endpoints:
        *   `POST /api/auth/register`: Handles user registration. It should hash the password and create a new `User` record.
        *   `POST /api/auth/login`: Authenticates a user with email/password. On success, it generates and returns a JWT access token using the existing `python-jose` logic.
        *   `POST /api/auth/forgot-password`: Generates a signed, timed token using `itsdangerous` and sends it to the user's email.
        *   `POST /api/auth/reset-password`: Verifies the token, hashes the new password, and updates the user's record.

4.  **Update Pydantic Schemas**:
    *   Create new schemas in `backend/src/lib/schemas.py` for the request and response bodies of the new endpoints (e.g., `UserCreate`, `UserLogin`, `Token`).

## 4. Implement Frontend UI

1.  **Create New Pages/Views**:
    *   In the `frontend/src/pages` directory, create new React components for:
        *   Registration Page (`Register.tsx`)
        *   Login Page (`Login.tsx`) - This might involve modifying the existing login page to support both Google and email/password.
        *   Forgot Password Page (`ForgotPassword.tsx`)
        *   Reset Password Page (`ResetPassword.tsx`)

2.  **Build UI Components**:
    *   Create reusable form components in `frontend/src/components` for email and password inputs.

3.  **Implement API Calls**:
    *   In a frontend service module (e.g., `frontend/src/services/api.ts`), add functions to call the new backend endpoints (`/register`, `/login`, etc.).

4.  **Manage Auth State**:
    *   Update the frontend's authentication context or state management (e.g., React Context, Redux) to handle the JWT token received from the backend. This includes storing the token securely (e.g., in `localStorage`) and attaching it to authenticated API requests.
