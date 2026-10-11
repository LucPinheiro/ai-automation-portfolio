from fastapi import APIRouter, BackgroundTasks, Response, status

from app.api.dependencies import (
    AuthServiceDep,
    CurrentUserDep,
    EmailSenderDep,
    RegisteredUserDep,
    SessionTokenDep,
    SettingsDep,
)
from app.api.responses import error_responses
from app.config import Settings
from app.core.exceptions import UsernameAlreadyTakenError
from app.database.types import utc_now
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserRead,
)
from app.services.access import enter_guest_mode, is_reserved_username, sign_in
from app.services.auth_service import IssuedSession
from app.services.email import password_reset_email, send_safely

router = APIRouter(prefix="/auth", tags=["Authentication"])

FORGOT_PASSWORD_MESSAGE = "If an account exists for that email, a password reset link has been sent."


def set_session_cookie(response: Response, settings: Settings, issued: IssuedSession) -> None:
    # HttpOnly: unreadable from JavaScript. SameSite=Lax: not sent on cross-site POST/PUT/DELETE.
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.token,
        # Guests and registered users have different session lifetimes.
        max_age=max(int((issued.expires_at - utc_now()).total_seconds()), 0),
        expires=issued.expires_at,
        path="/",
        httponly=True,
        secure=settings.session_cookie_is_secure,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_is_secure,
        samesite="lax",
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register",
    description=(
        "Creates an account and logs it in (sets the HttpOnly session cookie). "
        "The password is stored only as an Argon2id hash. When called from a guest session, "
        "the guest's generations are moved to the new account."
    ),
    response_description="Account created and logged in",
    responses=error_responses(400, 403, 409, 422, 500),
)
def register(
    data: RegisterRequest, auth: AuthServiceDep, settings: SettingsDep, token: SessionTokenDep, response: Response
) -> UserRead:
    if is_reserved_username(settings, data.username):
        raise UsernameAlreadyTakenError()
    issued = auth.register(
        name=data.name, email=data.email, username=data.username, password=data.password, guest_token=token
    )
    set_session_cookie(response, settings, issued)
    return UserRead.model_validate(issued.user)


@router.post(
    "/login",
    response_model=UserRead,
    summary="Log in",
    description=(
        "Checks the username or email and the password, and sets the HttpOnly session cookie. "
        "Unknown accounts and wrong passwords get the same 401 response. When called from a guest "
        "session, the guest's generations are moved to the account. The public demo credentials "
        "(DEMO_USERNAME / DEMO_PASSWORD) open a guest session instead of an account."
    ),
    response_description="Logged in",
    responses=error_responses(400, 401, 403, 422, 500),
)
def login(
    data: LoginRequest, auth: AuthServiceDep, settings: SettingsDep, token: SessionTokenDep, response: Response
) -> UserRead:
    result = sign_in(auth, settings, identifier=data.identifier, password=data.password, token=token)
    if result.issued is not None:
        set_session_cookie(response, settings, result.issued)
    return UserRead.model_validate(result.user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out",
    description=(
        "Deletes the current session on the server and clears the cookie; the old cookie stops working. "
        "For a guest, the guest and all its generations are permanently deleted."
    ),
    response_description="Logged out",
    responses=error_responses(401, 403, 500),
)
def logout(
    _user: CurrentUserDep, token: SessionTokenDep, auth: AuthServiceDep, settings: SettingsDep
) -> Response:
    auth.logout(token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings)
    return response


@router.get(
    "/me",
    response_model=UserRead,
    summary="Current user",
    description="Returns the authenticated user.",
    response_description="The authenticated user",
    responses=error_responses(401, 500),
)
def read_current_user(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description=(
        "Changes the password after checking the current one. All other sessions are closed "
        "and this client receives a new session cookie. Not available to guests (403)."
    ),
    response_description="Password changed",
    responses=error_responses(400, 401, 403, 422, 500),
)
def change_password(
    data: ChangePasswordRequest, user: RegisteredUserDep, auth: AuthServiceDep, settings: SettingsDep
) -> Response:
    issued = auth.change_password(user, current_password=data.current_password, new_password=data.new_password)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    set_session_cookie(response, settings, issued)
    return response


@router.post(
    "/guest",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Enter as a guest",
    description=(
        "Starts a temporary guest session (HttpOnly cookie, shorter lifetime) without email or password. "
        "Guests can use the generation endpoints for their own data only, with a generation limit. "
        "Logging out deletes the guest and its generations. If the caller is already a guest, "
        "the current guest session is kept."
    ),
    response_description="Guest session started",
    responses=error_responses(403, 500),
)
def start_guest_session(
    token: SessionTokenDep,
    auth: AuthServiceDep,
    settings: SettingsDep,
    response: Response,
) -> UserRead:
    result = enter_guest_mode(auth, settings, token)
    if result.issued is not None:
        set_session_cookie(response, settings, result.issued)
    return UserRead.model_validate(result.user)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request a password reset",
    description=(
        "Emails a single-use reset link that expires. The response is the same whether or not the "
        "email has an account, and the email is sent in the background so timing reveals nothing."
    ),
    response_description="Request accepted",
    responses=error_responses(400, 403, 422, 500),
)
def forgot_password(
    data: ForgotPasswordRequest,
    auth: AuthServiceDep,
    settings: SettingsDep,
    email_sender: EmailSenderDep,
    background_tasks: BackgroundTasks,
) -> MessageResponse:
    issued = auth.request_password_reset(data.email)
    if issued is not None:
        message = password_reset_email(
            to=issued.user.email,
            name=issued.user.name,
            base_url=settings.app_base_url,
            token=issued.token,
            ttl_minutes=settings.password_reset_ttl_minutes,
        )
        background_tasks.add_task(send_safely, email_sender, message)
    return MessageResponse(message=FORGOT_PASSWORD_MESSAGE)


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset the password",
    description=(
        "Sets a new password with the token from the reset link. The token is single-use and "
        "expires; all sessions of the account are closed."
    ),
    response_description="Password reset",
    responses=error_responses(400, 403, 422, 500),
)
def reset_password(data: ResetPasswordRequest, auth: AuthServiceDep) -> Response:
    auth.reset_password(token=data.token, new_password=data.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
