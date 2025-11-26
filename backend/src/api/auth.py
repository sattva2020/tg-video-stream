import os
import logging
import time
import uuid
 

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import get_db
from pydantic import BaseModel, EmailStr
from models.user import User
from services.auth_service import auth_service, check_password_policy, is_password_pwned
from tasks.notifications import notify_admins_async
from fastapi.security import OAuth2PasswordBearer
from auth import jwt
import models

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = jwt.decode_access_token(token)
    if payload is None:
        logger.warning("Token decoding failed")
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        logger.warning("Token payload missing 'sub'")
        raise credentials_exception
    
    try:
        # Ensure user_id is a valid UUID object for the query
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID in token: {user_id}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

# Simple in-memory rate limiter per IP for demo / tests
_rate_limit_storage = {}
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", 5))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", 60))  # seconds


def _rate_limit_key(ip: str, action: str):
    return f"{action}:{ip}"


def _check_rate_limit(ip: str, action: str) -> bool:
    key = _rate_limit_key(ip, action)
    now = time.time()
    entry = _rate_limit_storage.get(key, [])
    # filter timestamps within window
    entry = [t for t in entry if now - t < RATE_LIMIT_WINDOW]
    if len(entry) >= RATE_LIMIT_MAX:
        _rate_limit_storage[key] = entry
        return False
    entry.append(now)
    _rate_limit_storage[key] = entry
    return True


def make_rate_limit_dep(action: str, times: int = 5, seconds: int = 60):
    # Returns a dependency function for rate limiting — uses Redis if available
    if os.getenv('REDIS_URL'):
        # fastapi-limiter RateLimiter is callable for Depends
        from fastapi_limiter.depends import RateLimiter
        return RateLimiter(times=times, seconds=seconds)

    # Memory fallback
    async def _mem_limit(request: Request):
        ip = request.client.host if request.client else 'unknown'
        if not _check_rate_limit(ip, action):
            raise HTTPException(status_code=429, detail='Too many attempts, try again later.')

    return _mem_limit
# other imports moved to top to satisfy linting


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# This should be the full URL to your backend's callback endpoint
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback") 

# OAuth 2.0 scopes
SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

# Google's authorization endpoint
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"

router = APIRouter()

# Basic server-side localization map (fallback). In production this should
# be replaced with a proper i18n solution or use the frontend localization only.
MESSAGE_LOCALIZATIONS = {
    'ru': {
        'auth.email_registered': 'Пользователь с таким email уже существует',
        'auth.google_account_exists': 'Аккаунт уже зарегистрирован через Google — свяжите учётные записи.',
        'auth.account_pending': 'Аккаунт ожидает одобрения администратора',
        'auth.account_rejected': 'Аккаунт отклонён администрацией',
    }
}


def _format_auth_error(code: str, hint: str, message: str | None = None, message_key: str | None = None, req: Request | None = None) -> dict:
    """Return the error payload for auth endpoints.

    If Accept-Language includes 'ru', return localized `message` when possible.
    Otherwise return `message_key` when available so frontend can localize.
    """
    accept = ''
    if req:
        accept = req.headers.get('accept-language', '') or ''
    prefers_ru = 'ru' in accept.lower()

    if prefers_ru:
        # If server has localization for the key, prefer that
        if message_key and message_key in MESSAGE_LOCALIZATIONS.get('ru', {}):
            return {'code': code, 'message': MESSAGE_LOCALIZATIONS['ru'][message_key], 'hint': hint}
        if message:
            return {'code': code, 'message': message, 'hint': hint}
        # Fallback to key
        if message_key:
            return {'code': code, 'message': message_key, 'hint': hint}
    # Default behaviour: prefer message_key so client-localization can handle it
    if message_key:
        return {'code': code, 'message_key': message_key, 'hint': hint}
    if message:
        return {'code': code, 'message': message, 'hint': hint}
    return {'code': code, 'hint': hint}

@router.get("/google")
async def google_login(request: Request):
    """
    Redirects the user to Google's OAuth 2.0 authorization page.
    """
    if not GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID is not set.")
        raise ValueError("GOOGLE_CLIENT_ID is not set")

    google = OAuth2Session(GOOGLE_CLIENT_ID, scope=SCOPE, redirect_uri=REDIRECT_URI)
    authorization_url, state = google.authorization_url(
        AUTHORIZATION_URL,
        access_type="offline",
        prompt="select_account",
    )

    # Store the state in the user's session to prevent CSRF
    request.session['oauth_state'] = state
    logger.info("Redirecting user to Google for authentication.")
    return RedirectResponse(authorization_url)

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles the callback from Google, creates/retrieves the user,
    generates a JWT, and redirects to the frontend.
    """
    # Check for state mismatch to prevent CSRF
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    if 'oauth_state' not in request.session or request.session['oauth_state'] != request.query_params.get('state'):
        logger.warning("OAuth state mismatch (potential CSRF).")
        return RedirectResponse(url=f'{frontend_url}/login?error=state_mismatch')

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google client credentials are not set.")
        raise ValueError("Google client credentials are not set")

    google = OAuth2Session(GOOGLE_CLIENT_ID, state=request.session.pop('oauth_state', None), redirect_uri=REDIRECT_URI)
    
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    # Allow insecure transport for localhost dev
    if 'localhost' in REDIRECT_URI or '127.0.0.1' in REDIRECT_URI:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    try:
        # fetch token but we don't need to keep it here — login flow will use user info
        google.fetch_token(
            TOKEN_URL,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
        logger.info("Successfully fetched token from Google.")
    except Exception as e:
        logger.error(f"Error fetching token from Google: {e}", exc_info=True)
        return RedirectResponse(url=f'{frontend_url}/login?error=token_fetch_failed')

    user_info_response = google.get("https://www.googleapis.com/oauth2/v1/userinfo")
    if user_info_response.status_code != 200:
        logger.error(f"Error fetching user info from Google. Status: {user_info_response.status_code}")
        return RedirectResponse(url=f'{frontend_url}/login?error=user_info_failed')
    
    user_info = user_info_response.json()
    logger.info(f"Successfully fetched user info for email: {user_info.get('email')}")

    # Get or create user and generate JWT
    try:
        result = auth_service.get_or_create_user(db, user_info=user_info)
        # get_or_create_user now returns (user, created)
        if isinstance(result, tuple):
            user, created = result
        else:
            user, created = result, False

        # If user created just now, mark as pending and do NOT issue JWT yet
        if created or getattr(user, 'status', 'approved') != 'approved':
            # Enqueue admin notification for approval (dev-safe fallback exists)
            try:
                from tasks.notifications import notify_admins_async
                notify_admins_async(user.id)
            except Exception:
                logger.exception('Failed to notify admins for new OAuth user')
            # Redirect frontend to login showing pending message
            return RedirectResponse(url=f"{frontend_url}/login?status=pending")

        jwt_token = auth_service.create_jwt_for_user(user)
        logger.info(f"Successfully processed user and generated JWT for user ID: {user.id}")
    except Exception as e:
        logger.error(f"Error during user processing for email {user_info.get('email')}: {e}")
        return RedirectResponse(url=f'{frontend_url}/login?error=auth_process_failed')

    # Redirect to the frontend callback with the token
    frontend_callback_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    return RedirectResponse(url=frontend_callback_url)

@router.post("/logout")
async def logout():
    """
    A placeholder endpoint for logging out. In a stateless JWT setup,
    the client is responsible for deleting the token. This endpoint
    is here for API completeness and could be extended to support
    token blocklisting in the future.
    """
    logger.info("Logout endpoint called.")
    return {"message": "Logout successful"}


@router.post("/register")
def register_user(request: RegisterRequest, fastapi_request: Request = None, db: Session = Depends(get_db)):
    # prevent registration if Google-only user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        # If user exists and has no hashed_password but google_id is set, prompt linking
        if existing_user.google_id and not existing_user.hashed_password:
            # Indicate client that link action is required — return structured error
            detail = _format_auth_error(
                code='conflict',
                hint='link_account',
                message_key='auth.google_account_exists',
                req=fastapi_request,
            )
            # include additional hint for linking flow for tests/clients
            detail['link_required'] = True
            raise HTTPException(status_code=409, detail=detail)
        detail = _format_auth_error(
            code='conflict',
            hint='email_exists',
            message_key='auth.email_registered',
            req=fastapi_request,
        )
        raise HTTPException(status_code=409, detail=detail)

    hashed = auth_service.hash_password(request.password)
    # New users are created with status='pending' and must be approved by an admin
    new_user = User(google_id=None, email=request.email, hashed_password=hashed, status='pending')
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Do NOT issue JWT for pending users. Notify admins asynchronously.
    try:
        notify_admins_async(new_user.id)
    except Exception:
        # Ensure registration does not fail when notification subsystem is not available in dev
        logger.exception("Failed to enqueue admin notification")
    # Generate verification token and send email (dev-mode returns token)
    verify_token = auth_service.generate_email_verification_token(new_user.email)
    if not os.getenv("SMTP_HOST"):
        # In dev mode return a helpful response for tests (no JWT for pending users)
        return {"status": "pending", "message": "Account created and awaiting administrator approval", "dev_verification_token": verify_token}
    else:
        auth_service.send_email_verification(new_user.email, verify_token)
    return {"status": "pending", "message": "Account created and awaiting administrator approval"}


@router.post("/login")
async def login_user(fastapi_request: Request, db: Session = Depends(get_db), _rl = Depends(make_rate_limit_dep('login'))):
    # rate-limit by IP
    client_host = "unknown"
    if fastapi_request and fastapi_request.client:
        client_host = fastapi_request.client.host
    # rate limit is enforced via the dependency _rl (make_rate_limit_dep)
    # Accept both JSON {email, password} and form-urlencoded OAuth2-style
    # where clients submit `username`+`password` as form-data. Parse accordingly
    # to preserve backward compatibility for older clients.
    content_type = fastapi_request.headers.get('content-type', '')
    parsed = None
    try:
        if 'application/json' in content_type:
            parsed = await fastapi_request.json()
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            form = await fastapi_request.form()
            # form items behave like a MultiDict; map username->email for legacy clients
            parsed = { 'email': form.get('username') or form.get('email'), 'password': form.get('password') }
        else:
            # try json first, fallback to form
            try:
                parsed = await fastapi_request.json()
            except Exception:
                form = await fastapi_request.form()
                parsed = { 'email': form.get('username') or form.get('email'), 'password': form.get('password') }
    except Exception:
        raise HTTPException(status_code=422, detail='Invalid request payload')

    # Validate payload shape using Pydantic model
    try:
        login_data = LoginRequest.parse_obj(parsed)
    except Exception:
        # Let pydantic/fastapi handle shaping errors – return 422
        raise HTTPException(status_code=422, detail='Invalid login payload')

    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Block login if the account is not approved
    if getattr(user, 'status', 'approved') != 'approved':
        status_val = getattr(user, 'status', 'pending')
        if status_val == 'pending':
            detail = _format_auth_error(
                code='pending',
                hint='contact_admin',
                message_key='auth.account_pending',
                req=fastapi_request,
            )
        else:
            # Any other explicit denied status treated as rejected
            detail = _format_auth_error(
                code='rejected',
                hint='contact_admin',
                message_key='auth.account_rejected',
                req=fastapi_request,
            )
        raise HTTPException(status_code=403, detail=detail)
    if not auth_service.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str


@router.post("/password-reset/request")
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db), fastapi_request: Request = None, _rl = Depends(make_rate_limit_dep('password-reset'))):
    client_ip = "unknown"
    if fastapi_request and fastapi_request.client:
        client_ip = fastapi_request.client.host
    if not _check_rate_limit(client_ip, 'password-reset'):
        raise HTTPException(status_code=429, detail="Too many password reset requests, try later.")

    user = db.query(User).filter(User.email == data.email).first()
    # Always return OK to avoid user enumeration
    if not user:
        return {"status": "ok"}

    token = auth_service.generate_password_reset_token(data.email)
    # DEV-mode: return token in response if SMTP not configured
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        return {"status": "ok", "token": token}

    auth_service.send_password_reset_email(data.email, token)
    return {"status": "ok"}


class LinkAccountRequest(BaseModel):
    email: EmailStr


@router.post("/link-account/request")
def link_account_request(body: LinkAccountRequest, db: Session = Depends(get_db)):
    # Do not leak whether the email exists for security — however this endpoint
    # is intended to be called by a user who got 409 on register. Still, be cautious.
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.google_id or user.hashed_password:
        # Always return ok
        return {"status": "ok"}

    token = auth_service.generate_link_account_token(body.email)

    # Dev-mode: return the token in response if SMTP not configured
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        return {"status": "ok", "token": token}

    auth_service.send_account_link_email(body.email, token)
    return {"status": "ok"}


class LinkAccountConfirm(BaseModel):
    token: str
    password: str


@router.post("/link-account/confirm")
def link_account_confirm(body: LinkAccountConfirm, db: Session = Depends(get_db)):
    email = auth_service.verify_link_account_token(body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate password policy
    if not check_password_policy(body.password):
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements")

    if os.getenv("HIBP_ENABLED", "false").lower() == "true" and is_password_pwned(body.password):
        raise HTTPException(status_code=400, detail="Password is found in data leaks (choose another one)")

    user.hashed_password = auth_service.hash_password(body.password)
    db.commit()
    db.refresh(user)

    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token}


class EmailVerifyRequest(BaseModel):
    email: EmailStr


class EmailVerifyConfirm(BaseModel):
    token: str


@router.post("/email-verify/request")
def email_verify_request(body: EmailVerifyRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    # Avoid leaking info
    if not user:
        return {"status": "ok"}
    token = auth_service.generate_email_verification_token(body.email)
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        return {"status": "ok", "token": token}
    auth_service.send_email_verification(body.email, token)
    return {"status": "ok"}


@router.post("/email-verify/confirm")
def email_verify_confirm(body: EmailVerifyConfirm, db: Session = Depends(get_db)):
    email = auth_service.verify_email_verification_token(body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return {"status": "ok"}


@router.post("/password-reset/confirm")
def password_reset_confirm(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    email = auth_service.verify_password_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    # Validate password complexity
    if len(data.password) < 12:
        raise HTTPException(status_code=400, detail="Password does not meet complexity requirements")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = auth_service.hash_password(data.password)
    db.commit()
    db.refresh(user)
    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token}


    

    

    

        

    

    

    