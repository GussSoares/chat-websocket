import base64
import binascii
from typing import Optional

from fastapi import Request, WebSocket, status
from fastapi.exceptions import HTTPException
from fastapi.openapi.models import HTTPBearer as HTTPBearerModel
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBase
from fastapi.security.utils import get_authorization_scheme_param

from app.schema.user import UserModel


class HTTWebSocketBearer(HTTPBase):
    def __init__(
        self,
        *,
        bearerFormat: Optional[str] = None,
        scheme_name: Optional[str] = None,
        auto_error: bool = True,
    ):
        self.model = HTTPBearerModel(bearerFormat=bearerFormat)
        self.scheme_name = scheme_name or self.__class__.__name__
        self.auto_error = auto_error

    async def __call__(self, ws: WebSocket) -> WebSocket:
        authorization: str = ws.headers.get("Authorization")
        scheme, credentials = get_authorization_scheme_param(authorization)
        if not (authorization and scheme and credentials):
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
                )
            else:
                return None
        if scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication credentials",
                )
            else:
                return None
        try:
            data = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
            )
        username, separator, password = data.partition(":")
        if not separator:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authenticated"
            )

        ws.scope["user"] = UserModel(username=username, password=password)
        return ws
        # return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


security_bearer_ws = HTTWebSocketBearer()


def check_token(ws: WebSocket):
    return ws
