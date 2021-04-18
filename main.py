import json
from typing import List, Optional

from fastapi import (Cookie, Depends, FastAPI, Query, WebSocket,
                     WebSocketDisconnect, status)
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Dar um jeito de projetar chat privado.
# Talvez salvar no manager um objeto com um identificador do usuario
# e o websocket associado. Assim, quando solicitar o acesso a conversa,
# será usado o id do usuario apra saber qual socket deve ser usado.


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections.append({"websocket": websocket, "client": client_id})

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    def get_websocket_by_client_id(self, client_id: str):
        for elem in self.active_connections:
            if elem.get("client") == client_id:
                return elem.get("websocket")

    def get_online_users(self):
        return [x.get("client") for x in self.active_connections]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.get("websocket").send_json({"message": message})

    async def broadcast_json(self, data: dict):
        for connection in self.active_connections:
            await connection.get("websocket").send_json(data)


manager = ConnectionManager()
template = Jinja2Templates(directory="templates")


@app.get("/")
async def get(request: Request):
    return template.TemplateResponse(name="chat.html", context={"request": request})


# async def get_cookie_or_token(
#     websocket: WebSocket,
#     session: Optional[str] = Cookie(None),
#     token: Optional[str] = Query(None),
# ):
#     if session is None and token is None:
#         await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
#     return session or token


@app.websocket("/ws/client/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast_json({"users": manager.get_online_users()})
            # await manager.broadcast(f"{client_id}: {data}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"{client_id} saiu")


# import json
# @app.websocket('/ws/get-users-online')
# async def websocket_get_online(websocket: WebSocket):
#     await manager.connect(websocket)
#     try:
#         while True:
#             data = await websocket.receive()
#             await manager.broadcast_json({'users': manager.get_online_users()})
#             # await manager.broadcast('fulano entrou')
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#     except Exception as exc:
#         print(exc)
