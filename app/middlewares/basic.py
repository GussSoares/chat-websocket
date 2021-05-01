import base64
import binascii
from typing import Optional

from fastapi import Depends, WebSocket, status
from fastapi.exceptions import HTTPException
from fastapi.openapi.models import HTTPBase as HTTPBaseModel
from fastapi.security import HTTPBasicCredentials, HTTPBearer
from fastapi.security.http import HTTPBase
from fastapi.security.utils import get_authorization_scheme_param
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    AuthenticationError,
    SimpleUser,
)

from app.schema.user import UserModel


class BasicAuthBackend(AuthenticationBackend):
    async def authenticate(self, request):
        if "Authorization" not in request.headers:
            return

        auth = request.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "basic":
                return
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise AuthenticationError("Invalid basic auth credentials")

        username, _, password = decoded.partition(":")
        # TODO: You'd want to verify the username and password here.
        return AuthCredentials(["authenticated"]), SimpleUser(username)


class WebSocketBasic(HTTPBase):
    def __init__(
        self,
        *,
        scheme_name: Optional[str] = None,
        realm: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model = HTTPBaseModel(scheme="basic")
        self.scheme_name = scheme_name or self.__class__.__name__
        self.realm = realm
        self.auto_error = auto_error

    async def __call__(self, websocket: WebSocket) -> WebSocket:  # type: ignore
        authorization: str = websocket.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)
        if self.realm:
            unauthorized_headers = {"WWW-Authenticate": f'Basic realm="{self.realm}"'}
        else:
            unauthorized_headers = {"WWW-Authenticate": "Basic"}
        invalid_user_credentials_exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers=unauthorized_headers,
        )
        if not authorization or scheme.lower() != "basic":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers=unauthorized_headers,
                )
            else:
                return None
        try:
            data = base64.b64decode(param).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            raise invalid_user_credentials_exc
        username, separator, password = data.partition(":")
        if not separator:
            raise invalid_user_credentials_exc

        websocket.scope["user"] = UserModel(username=username, password=password)
        return websocket


security = HTTPBearer()
security_websocket = WebSocketBasic()


def check_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    pass
