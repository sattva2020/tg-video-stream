"""
SAML 2.0 аутентификация для SSO.
"""
import os
import logging

from fastapi import APIRouter, Request, Depends, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import get_db
from services.auth_service import auth_service
from services.activity_service import ActivityService
from services.saml_service import saml_service, SAMLService
from src.models.saml_config import SAMLConfig

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env'))

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saml", tags=["SAML"])

# SAML config from environment
SAML_CONFIG_ID = os.getenv("SAML_CONFIG_ID")

frontend_url = os.getenv("FRONTEND_URL", os.getenv("FRONTEND_BASE_URL", "http://localhost:3000"))


def get_saml_config(db: Session) -> SAMLConfig:
    """
    Получает активную конфигурацию SAML.

    Args:
        db: Сессия базы данных

    Returns:
        SAMLConfig объект

    Raises:
        HTTPException: Если конфигурация не найдена или не активна
    """
    # Если указан ID конфигурации в .env, используем его
    if SAML_CONFIG_ID:
        config = db.query(SAMLConfig).filter(SAMLConfig.id == SAML_CONFIG_ID).first()
    else:
        # Иначе берем первую активную конфигурацию
        config = db.query(SAMLConfig).filter(SAMLConfig.enabled == True).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SAML is not configured. Please contact your administrator."
        )

    if not config.is_active():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML authentication is currently disabled."
        )

    return config


def prepare_request_data(request: Request) -> dict:
    """
    Подготавливает данные запроса для SAML библиотеки.

    Args:
        request: FastAPI Request объект

    Returns:
        Словарь с данными запроса в формате ожидаемом python3-saml
    """
    # Получаем данные из запроса
    https = "https" == request.url.scheme
    server_port = request.url.port or (443 if https else 80)

    return {
        'http_host': request.url.hostname,
        'script_name': request.url.path,
        'server_port': server_port,
        'get_data': dict(request.query_params),
        'post_data': await request.form() if request.method == "POST" else {},
        'https': 'on' if https else 'off',
        'request_uri': request.url.path,
        'query_string': str(request.url.query) if request.url.query else '',
    }


@router.get("/login")
async def saml_login(request: Request, db: Session = Depends(get_db)):
    """
    Инициирует SAML SSO - перенаправляет пользователя на IdP для аутентификации.

    Query Parameters:
        return_to: (опционально) URL для возврата после успешной аутентификации

    Returns:
        RedirectResponse на страницу входа Identity Provider
    """
    if not saml_service:
        logger.error("SAML service is not available. python3-saml may not be installed.")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SAML is not available. Please contact your administrator."
        )

    try:
        config = get_saml_config(db)
        request_data = prepare_request_data(request)

        # Получаем return_to из query параметров
        return_to = request.query_params.get('return_to')

        # Инициируем SAML login
        redirect_url = saml_service.initiate_login(config, request_data, return_to)

        logger.info(f"SAML login initiated for config '{config.name}', redirecting to IdP")

        return RedirectResponse(redirect_url)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error initiating SAML login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate SAML login: {str(e)}"
        )


@router.post("/acs")
async def saml_acs(request: Request, db: Session = Depends(get_db)):
    """
    Assertion Consumer Service (ACS) - обрабатывает SAML Response от IdP.

    Это callback endpoint, куда Identity Provider отправляет пользователя
    после успешной аутентификации с SAML assertion.

    Returns:
        RedirectResponse на фронтенд с JWT токеном
    """
    if not saml_service:
        logger.error("SAML service is not available")
        return RedirectResponse(url=f'{frontend_url}/login?error=saml_not_available')

    try:
        config = get_saml_config(db)

        # Для POST запроса от SAML нужно получить данные формы
        form_data = await request.form()
        request_data = {
            'http_host': request.url.hostname,
            'script_name': request.url.path,
            'server_port': request.url.port or (443 if request.url.scheme == "https" else 80),
            'get_data': dict(request.query_params),
            'post_data': dict(form_data),
            'https': 'on' if request.url.scheme == "https" else 'off',
            'request_uri': request.url.path,
            'query_string': str(request.url.query) if request.url.query else '',
        }

        # Обрабатываем SAML Response
        saml_data = saml_service.process_response(config, request_data)

        logger.info(f"SAML authentication successful for NameID: {saml_data['name_id']}")

        # Создаём или получаем пользователя
        result = saml_service.get_or_create_user(db, saml_data, config)
        if isinstance(result, tuple):
            user, created = result
        else:
            user, created = result, False

        # Логируем регистрацию нового пользователя через SAML
        if created:
            activity_service = ActivityService(db)
            activity_service.log_event(
                event_type="user_registered",
                message=f"Новый пользователь зарегистрирован через SAML: {user.email}",
                user_id=user.id,
                user_email=user.email,
                details={"method": "saml_sso", "saml_config_id": str(config.id)}
            )

        # Проверяем статус пользователя
        user_status = getattr(user, 'status', 'active')
        if created or user_status not in ('active', 'approved'):
            # Новый пользователь - ожидает подтверждения
            temp_token = auth_service.create_jwt_for_user(user)
            logger.info(f"New SAML user {user.email} created with status '{user_status}'")
            return RedirectResponse(
                url=f"{frontend_url}/auth/callback?token={temp_token}&status=pending"
            )

        # Обновляем время последнего входа
        try:
            if hasattr(user, 'update_last_login'):
                user.update_last_login()
                db.add(user)
                db.commit()
        except Exception:
            logger.exception('Failed to update last_login for SAML user')

        # Генерируем JWT токен
        jwt_token = auth_service.create_jwt_for_user(user)
        logger.info(f"Successfully processed SAML user and generated JWT for user ID: {user.id}")

        # Редирект на фронтенд с токеном
        frontend_callback_url = f"{frontend_url}/auth/callback?token={jwt_token}"
        return RedirectResponse(url=frontend_callback_url)

    except HTTPException as e:
        logger.error(f"SAML ACS HTTP error: {e.detail}")
        error_param = e.detail.replace(' ', '_').lower()
        return RedirectResponse(url=f'{frontend_url}/login?error=saml_{error_param}')
    except Exception as e:
        logger.exception(f"Error processing SAML response: {e}")
        return RedirectResponse(url=f'{frontend_url}/login?error=saml_failed&details={str(e)}')


@router.get("/metadata")
async def saml_metadata(request: Request, db: Session = Depends(get_db)):
    """
    Генерирует и возвращает SP (Service Provider) метаданные в XML формате.

    Этот endpoint используется Identity Provider для получения информации
    о нашем Service Provider (ACS URL, Entity ID, сертификаты и т.д.).

    Returns:
        XML с SP метаданными для регистрации в IdP
    """
    if not saml_service:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SAML is not available. Please contact your administrator."
        )

    try:
        config = get_saml_config(db)

        # Генерируем метаданные
        metadata_xml = saml_service.get_metadata(config)

        logger.info(f"SAML metadata generated for config '{config.name}'")

        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": 'attachment; filename="saml-metadata.xml"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating SAML metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate metadata: {str(e)}"
        )


@router.get("/logout")
async def saml_logout(request: Request, db: Session = Depends(get_db)):
    """
    Инициирует SAML Single Logout (SLO).

    Query Parameters:
        name_id: (опционально) Идентификатор пользователя в SAML
        session_index: (опционально) Индекс сессии для logout

    Returns:
        RedirectResponse на IdP для logout или на фронтенд если SLO не настроен
    """
    if not saml_service:
        logger.warning("SAML logout requested but SAML service is not available")
        return RedirectResponse(url=f'{frontend_url}/login')

    try:
        config = get_saml_config(db)
        request_data = prepare_request_data(request)

        name_id = request.query_params.get('name_id')
        session_index = request.query_params.get('session_index')

        # Инициируем logout
        logout_url = saml_service.initiate_logout(config, request_data, name_id, session_index)

        if logout_url:
            logger.info(f"SAML logout initiated, redirecting to IdP")
            return RedirectResponse(logout_url)
        else:
            # SLO не настроен - просто редирект на фронтенд
            logger.info(f"SAML SLO not configured, redirecting to frontend")
            return RedirectResponse(url=f'{frontend_url}/login')

    except Exception as e:
        logger.exception(f"Error initiating SAML logout: {e}")
        # Даже при ошибке редиректим на фронтенд
        return RedirectResponse(url=f'{frontend_url}/login')


@router.get("/slo")
async def saml_slo_callback(request: Request, db: Session = Depends(get_db)):
    """
    Single Logout callback - обрабатывает logout response от IdP.

    Returns:
        RedirectResponse на фронтенд после завершения logout
    """
    if not saml_service:
        return RedirectResponse(url=f'{frontend_url}/login')

    try:
        config = get_saml_config(db)
        request_data = prepare_request_data(request)

        # Обрабатываем logout response
        saml_service.process_logout_response(config, request_data)

        logger.info(f"SAML logout completed successfully")

        return RedirectResponse(url=f'{frontend_url}/login?logged_out=true')

    except HTTPException as e:
        logger.error(f"SAML SLO error: {e.detail}")
        return RedirectResponse(url=f'{frontend_url}/login?error=logout_failed')
    except Exception as e:
        logger.exception(f"Error processing SAML logout: {e}")
        return RedirectResponse(url=f'{frontend_url}/login?error=logout_failed')
