from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import logging
import asyncio
from redis_manager import RedisManager

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str
    sender_id: str = None

connections = {}
redis_manager = RedisManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())[:6]
    connections[connection_id] = websocket
    logger.info(f"WebSocket connection established: {connection_id}")
    await websocket.send_text(f"Your ID: {connection_id}")
    try:
        while True:
            message = await websocket.receive_text()
            logger.info(f"Received message from {connection_id}: {message}")
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed: {connection_id}")
        del connections[connection_id]

async def send_detection_update(client_id: str, status: str, confidence: float, message: str):
    update_data = {
        "type": "detection_update",
        "client_id": client_id,
        "status": status,
        "confidence": confidence,
        "message": message,
        "timestamp": str(uuid.uuid4())[:8]
    }
    
    logger.info(f"Broadcasting detection update to {len(connections)} clients: {client_id} - {status} - {message}")
    for connection_id, connection in connections.items():
        try:
            await connection.send_text(f"DETECTION:{client_id}:{status}:{confidence}:{message}")
        except Exception as e:
            logger.error(f"Failed to send detection update to {connection_id}: {e}")

async def send_page_count_update(client_id: str, total_pages: int):
    logger.info(f"Broadcasting page count to {len(connections)} clients: {client_id} - {total_pages} pages")
    for connection_id, connection in connections.items():
        try:
            await connection.send_text(f"PAGE_COUNT:{client_id}:{total_pages}")
        except Exception as e:
            logger.error(f"Failed to send page count to {connection_id}: {e}")

async def send_page_result_update(client_id: str, page_num: int, result: dict):
    logger.info(f"Broadcasting page result to {len(connections)} clients: {client_id} - Page {page_num}: {result['orientation']}")
    for connection_id, connection in connections.items():
        try:
            result_str = f"PAGE_RESULT:{client_id}:{page_num}:{result['orientation']}:{result['aspect_ratio']}:{result['width']}:{result['height']}"
            await connection.send_text(result_str)
        except Exception as e:
            logger.error(f"Failed to send page result to {connection_id}: {e}")

@app.post("/api/send-message")
async def send_message(request: MessageRequest):
    logger.info(f"Sending message to {len(connections)} WebSocket clients: {request.message}")
    # Send the raw message directly to websocket clients (not chat format)
    for connection_id, connection in connections.items():
        try:
            await connection.send_text(request.message)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {e}")
    return {"status": "sent"}

async def handle_redis_message(data):
    """Handle messages from Redis and broadcast to WebSocket clients"""
    logger.info(f"Received Redis message: {data['type']} for client {data.get('client_id', 'unknown')}")
    
    if data['type'] == 'DETECTION':
        message = f"DETECTION:{data['client_id']}:{data['status']}:{data['confidence']}:{data['message']}"
    elif data['type'] == 'PAGE_COUNT':
        message = f"PAGE_COUNT:{data['client_id']}:{data['total_pages']}"
    elif data['type'] == 'PAGE_RESULT':
        result = data['result']
        message = f"PAGE_RESULT:{data['client_id']}:{data['page_num']}:{result['orientation']}:{result['aspect_ratio']}:{result['width']}:{result['height']}"
    else:
        logger.warning(f"Unknown Redis message type: {data.get('type', 'missing')}")
        return
    
    logger.info(f"Broadcasting Redis message to {len(connections)} WebSocket clients: {message[:100]}...")
    # Broadcast to all connected WebSocket clients
    disconnected_clients = []
    for connection_id, connection in list(connections.items()):
        try:
            await connection.send_text(message)
        except Exception as e:
            logger.error(f"Failed to broadcast to {connection_id}: {e}")
            # Remove disconnected clients
            disconnected_clients.append(connection_id)
            connections.pop(connection_id, None)
    
    if disconnected_clients:
        logger.info(f"Removed {len(disconnected_clients)} disconnected clients: {disconnected_clients}")

@app.on_event("startup")
async def startup():
    logger.info("Starting WebSocket server...")
    await redis_manager.connect()
    logger.info("Connected to Redis")
    # Start Redis listener in background
    asyncio.create_task(redis_manager.listen_for_messages(handle_redis_message))
    logger.info("Redis message listener started")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down WebSocket server...")
    await redis_manager.close()
    logger.info("Redis connection closed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)