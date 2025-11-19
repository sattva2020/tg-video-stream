import os
import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from fastapi import Depends

from services.auth_service import auth_service
from database import get_db
from pydantic import BaseModel, EmailStr
from models.user import User
from fastapi import HTTPException
from auth.jwt import create_access_token
from sqlalchemy.orm import Session


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
REDIRECT_URI = "http://localhost:8000/api/auth/google/callback" 

# OAuth 2.0 scopes
SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
]

# Google's authorization endpoint
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"

router = APIRouter()

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
    if 'oauth_state' not in request.session or request.session['oauth_state'] != request.query_params.get('state'):
        logger.warning("OAuth state mismatch (potential CSRF).")
        return RedirectResponse(url='/login?error=state_mismatch')

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google client credentials are not set.")
        raise ValueError("Google client credentials are not set")

    google = OAuth2Session(GOOGLE_CLIENT_ID, state=request.session.pop('oauth_state', None), redirect_uri=REDIRECT_URI)
    
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    try:
        token = google.fetch_token(
            TOKEN_URL,
            client_secret=GOOGLE_CLIENT_SECRET,
            authorization_response=str(request.url)
        )
        logger.info("Successfully fetched token from Google.")
    except Exception as e:
        logger.error(f"Error fetching token from Google: {e}")
        return RedirectResponse(url='/login?error=token_fetch_failed')

    user_info_response = google.get("https://www.googleapis.com/oauth2/v1/userinfo")
    if user_info_response.status_code != 200:
        logger.error(f"Error fetching user info from Google. Status: {user_info_response.status_code}")
        return RedirectResponse(url='/login?error=user_info_failed')
    
    user_info = user_info_response.json()
    logger.info(f"Successfully fetched user info for email: {user_info.get('email')}")

    # Get or create user and generate JWT
    try:
        user = auth_service.get_or_create_user(db, user_info=user_info)
        jwt_token = auth_service.create_jwt_for_user(user)
        logger.info(f"Successfully processed user and generated JWT for user ID: {user.id}")
    except Exception as e:
        logger.error(f"Error during user processing for email {user_info.get('email')}: {e}")
        return RedirectResponse(url='/login?error=auth_process_failed')

    # Redirect to the frontend callback with the token
    # Using a URL fragment is common for this pattern
    frontend_callback_url = f"/auth/google/callback#token={jwt_token}"
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
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    # prevent registration if Google-only user exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        # If user exists and has no hashed_password but google_id is set, prompt linking
        if existing_user.google_id and not existing_user.hashed_password:
            raise HTTPException(status_code=409, detail="Account exists via Google; please sign in with Google or link accounts.")
        raise HTTPException(status_code=409, detail="User with this email already exists")

    hashed = auth_service.hash_password(request.password)
    new_user = User(google_id=None, email=request.email, hashed_password=hashed)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    token = auth_service.create_jwt_for_user(new_user)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login")
def login_user(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not auth_service.verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_jwt_for_user(user)
    return {"access_token": token, "token_type": "bearer"}


    

    

    

        

    

    

    