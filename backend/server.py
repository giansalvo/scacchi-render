# =============================
# === BACKEND: server.py    ===
# =============================
# backend/server.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import psycopg2
import psycopg2.extras
import uvicorn
import json
import os
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import datetime
import asyncio

# Ottieni il percorso assoluto della directory del progetto
BASE_DIR = Path(__file__).parent.parent

app = FastAPI()
app.mount("/static", StaticFiles(directory="./frontend"), name="static")
#app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In produzione sostituisci con l'URL del frontend
    allow_methods=["*"],
    allow_headers=["*"]
)

# Lista globale per gestire le connessioni attive
connections_lock = asyncio.Lock()
active_connections = []

# Configurazione da variabili d'ambiente
SERVER_PORT = int(os.getenv("SERVER_PORT"))

state = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"

# Verifica configurazione obbligatoria
missing_vars = []
for var in ["SERVER_PORT"]:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    raise EnvironmentError(f"Variabili d'ambiente mancanti: {', '.join(missing_vars)}")

print("=== ENVIRONMENT ===")
for key in ["SERVER_PORT"]:
    print(f"{key} = {os.getenv(key)}")


@app.get("/hello")
async def index():
    return "HELLO!!"


@app.get("/")
async def index():
    file_path = BASE_DIR / "frontend" / "index.html"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content)
    except UnicodeDecodeError:
        # Fallback per file non UTF-8
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
        return HTMLResponse(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot read index.html: {str(e)}")

@app.get("/api/state")
async def get_state():
    return {"fen": state}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Aggiunta thread-safe alla lista
    async with connections_lock:
        active_connections.append(websocket)

    client_ip = websocket.client.host if websocket.client else "unknown"
    print(f"[CONNECT] Client connected from {client_ip}. Total: {len(active_connections)}")

    try:
        while True:
            message = await websocket.receive_text()
            print(f"[MESSAGE] From {client_ip}: {message[:100]}...")

            try:
                data = json.loads(message)

                # Broadcast thread-safe
                async with connections_lock:
                    for connection in active_connections.copy():  # Usa una copia
                        try:
                            await connection.send_json({
                                "sender": client_ip,
                                "message": data,
                                "timestamp": datetime.now().isoformat()
                            })
                        except Exception as e:
                            print(f"Broadcast error: {e}")
                            if connection in active_connections:
                                active_connections.remove(connection)

            except json.JSONDecodeError:
                await websocket.send_text("Error: Invalid JSON format")

    except WebSocketDisconnect:
        print(f"[DISCONNECT] Client {client_ip} disconnected")
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
    finally:
        # Rimozione thread-safe
        async with connections_lock:
            if websocket in active_connections:
                active_connections.remove(websocket)
        await websocket.close()
        print(f"[STATUS] Remaining clients: {len(active_connections)}")

@app.post("/api/move")
async def receive_move(request: Request):
    global state
    try:
        print("[DEBUG] Receiving move from client...")
        raw = await request.body()
        print("[DEBUG] Raw body:", raw.decode())

        data = await request.json()
        move = data.get("move")
        fen = data.get("fen")
        print("[DEBUG] Parsed move:", move, "FEN:", fen)
        state = fen
        move = "placeholder"
        print("[DEBUG] Updated state with new move")
        # Invia la mossa a tutti i client WebSocket
        for client in active_connections:
            await client.send_json({"move": move, "fen": state})
            print("[DEBUG] Broadcasted move to client")

        return {"status": "ok"}

    except json.JSONDecodeError as json_error:
        print("[ERROR] JSON decode error:", str(json_error))
        return {"status": "error", "details": "Invalid JSON format"}

    except Exception as e:
        print("[ERROR] Unexpected error:", str(e))
        return {"status": "error", "details": "Internal server error"}


@app.get("/api/health")
async def health_check():
    return {"connection": "ok"}

if __name__ == "__main__":
    print(f"[INFO] Starting FastAPI app on port ${SERVER_PORT}")
    uvicorn.run("server:app", host="0.0.0.0", port=SERVER_PORT, reload=True, log_level="debug")

# =============================
# === CLIENT TCP: putty_sim ===
# =============================
# Simulazione con invio TCP o via curl HTTP POST

# Esempio curl:
# curl -X POST http://localhost:8000/api/move -H "Content-Type: application/json" -d '{"move": "e2e4", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"}'