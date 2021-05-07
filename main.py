import json
from datetime import datetime
from typing import List, Optional

import uvicorn
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates

from database.mongo import db

app = FastAPI()

# Dar um jeito de projetar chat privado.
# Talvez salvar no manager um objeto com um identificador do usuario
# e o websocket associado. Assim, quando solicitar o acesso a conversa,
# será usado o id do usuario apra saber qual socket deve ser usado.


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections.keys():
            self.active_connections.pop(client_id)

    def get_websocket_by_client_id(self, client_id: str):
        return self.active_connections[client_id]

    def get_online_users(self):
        return list(self.active_connections.keys())

    async def send_personal_message(self, data: dict, websocket: WebSocket):
        assert ('message' or 'from') in data, '"message" and "from" keys required in data'
        await websocket.send_json(data)

    async def broadcast(self, message: str):
        for client_id, ws in self.active_connections.items():
            await ws.send_json({"message": message})

    async def broadcast_json(self, data: dict):
        for client_id, ws in self.active_connections.items():
            await ws.send_json(data)

    async def propagate_online_users(self):
        for client_id, ws in self.active_connections.items():
            await ws.send_json({"online": self.get_online_users()})


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


@app.websocket("/ws/{access_token}")
async def websocket_endpoint(
    websocket: WebSocket,
    access_token: str,
):
    if access_token not in manager.get_online_users():
        await manager.connect(websocket, access_token)
        await websocket.send_json({"type": "websocket.connected"})

    try:
        while True:

            data = await websocket.receive()
            if data.get("type") == "websocket.connect":
                await manager.propagate_online_users()

            if data.get("type") == "websocket.receive":
                try:
                    parsed = json.loads(data.get("text"))

                    to = manager.get_websocket_by_client_id(parsed.get("to"))

                    await manager.send_personal_message({
                        'from': access_token,
                        'message': parsed.get("message"),
                    }, to)

                    db.database.messages.insert_one({
                        'timestamp': datetime.now(),
                        'to': parsed.get('to'),
                        'from': access_token,
                        'message': parsed.get('message')
                    })
                except Exception as exc:
                    parsed = data.get("text")
                await manager.propagate_online_users()

    except WebSocketDisconnect:
        manager.disconnect(access_token)
        await manager.propagate_online_users()
    except Exception as exc:
        manager.disconnect(access_token)
        await manager.propagate_online_users()
        # await manager.broadcast(f"{access_token} saiu")


@app.post("/get-token")
async def get_token(request: Request):
    body = json.loads(await request.body())
    username = body.get("username")
    # return {"access_token": base64.b64encode(f"{body.get('username')}:{body.get('password')}".encode('utf-8')).decode('utf-8')}
    return {"access_token": username}


@app.post("/get-chat")
async def get_chat(request: Request):
    body = json.loads(await request.body())
    _to = body.get("to")
    _from = body.get("from")
    result = await db.database.messages.find({
        '$or': [
        {'to': _to, 'from': _from},
        {'to': _from, 'from': _to}
        ]
    }, {'_id': False}).sort('timestamp', 1).to_list(length=100)

    return {"messages": result}


@app.on_event('startup')
async def startup():
    client = db.startup(database='teste')
    buildinfo = await client.command('buildinfo')
    print(f'MongoDB version {buildinfo.get("version")}')


@app.on_event('shutdown')
def shutdown():
    print('desligando...')
    db.shutdown()

if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
