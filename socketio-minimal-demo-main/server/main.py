from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import asyncio
import logging
import os
from pathlib import Path
from detection_model import detect_vertical_simple_pil, extract_pages_from_pdf, analyze_document, get_pdf_page_count
from PIL import Image
from redis_manager import RedisManager

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DetectionResult(BaseModel):
    client_id: str
    status: str
    confidence: float = None
    detection_type: str = None

detection_sessions = {}
redis_manager = RedisManager()

@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...), client_id: str = Form(...)):
    logger.info(f"File upload request received - Client ID: {client_id}, Filename: {file.filename}")
    allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        logger.warning(f"Unsupported file type rejected: {file_extension} from client {client_id}")
        return {
            "error": f"Unsupported file type: {file_extension}",
            "supported_types": list(allowed_extensions)
        }
    
    file_path = uploads_dir / f"{client_id}_{file.filename}"
    content = await file.read()
    file_size = len(content)
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info(f"File saved successfully - Client: {client_id}, Size: {file_size} bytes, Path: {file_path}")
    
    detection_sessions[client_id] = {
        "file_path": str(file_path),
        "filename": file.filename,
        "status": "uploaded"
    }
    
    logger.info(f"Starting background processing for client {client_id}")
    asyncio.create_task(process_document_detection(client_id, str(file_path)))
    
    return {"client_id": client_id, "status": "uploaded", "filename": file.filename}
async def process_document_detection(client_id: str, file_path: str):
    logger.info(f"Starting document processing for client {client_id} - File: {file_path}")
    try:
        if file_path.lower().endswith('.pdf'):
            logger.info(f"Processing PDF document for client {client_id}")
            await asyncio.sleep(0.5)
            total_pages = get_pdf_page_count(file_path)
            logger.info(f"PDF analysis - Client: {client_id}, Total pages: {total_pages}")
            await send_detection_update(client_id, "analyzing", 0.1, f"{total_pages} pages detected")
            await send_page_count_update(client_id, total_pages)
            await asyncio.sleep(1)
            logger.info(f"Extracting pages from PDF for client {client_id}")
            pages = extract_pages_from_pdf(file_path)
            
            for page_num, pil_image in enumerate(pages, 1):
                logger.info(f"Processing page {page_num}/{total_pages} for client {client_id}")
                is_vertical, aspect_ratio, width, height = detect_vertical_simple_pil(pil_image)
                orientation = "Vertical" if is_vertical else "Horizontal"
                logger.info(f"Page {page_num} analysis - Client: {client_id}, Orientation: {orientation}, Aspect Ratio: {aspect_ratio:.2f}")
                await send_detection_update(client_id, "processing", 
                                          (page_num / total_pages) * 0.8, 
                                          f"Page {page_num}/{total_pages}: {orientation}")
                
                result = {
                    "page": page_num,
                    "is_vertical": is_vertical,
                    "aspect_ratio": round(aspect_ratio, 2),
                    "width": width,
                    "height": height,
                    "orientation": orientation
                }
                
                await send_page_result_update(client_id, page_num, result)
                await asyncio.sleep(1)
            
            logger.info(f"PDF processing completed successfully for client {client_id} - {total_pages} pages processed")
            await send_detection_update(client_id, "completed", 1.0, "Detection completed")
        else:
            logger.info(f"Processing single image for client {client_id}")
            await send_detection_update(client_id, "analyzing", 0.1, "1 page detected")
            await send_page_count_update(client_id, 1)
            await asyncio.sleep(1)
            pil_image = Image.open(file_path)
            is_vertical, aspect_ratio, width, height = detect_vertical_simple_pil(pil_image)
            orientation = "Vertical" if is_vertical else "Horizontal"
            logger.info(f"Image analysis - Client: {client_id}, Orientation: {orientation}, Aspect Ratio: {aspect_ratio:.2f}")
            await send_detection_update(client_id, "processing", 0.8, f"Page 1/1: {orientation}")
            
            result = {
                "page": 1,
                "is_vertical": is_vertical,
                "aspect_ratio": round(aspect_ratio, 2),
                "width": width,
                "height": height,
                "orientation": orientation
            }
            
            await send_page_result_update(client_id, 1, result)
            logger.info(f"Image processing completed successfully for client {client_id}")
            await send_detection_update(client_id, "completed", 1.0, "Detection completed")
            
        if client_id in detection_sessions:
            detection_sessions[client_id]["status"] = "completed"
            logger.info(f"Session status updated to completed for client {client_id}")
            
    except Exception as e:
        logger.error(f"Critical error in document detection for client {client_id}: {e}")
        await send_detection_update(client_id, "error", 0.0, f"Error: {str(e)}")

async def send_detection_update(client_id: str, status: str, confidence: float, message: str):
    print(f"{message}")
    logger.info(f"Sending detection update - Client: {client_id}, Status: {status}, Progress: {confidence:.1f}, Message: {message}")
    try:
        await redis_manager.publish_detection_update(client_id, status, confidence, message)
        logger.debug(f"Detection update published to Redis successfully for client {client_id}")
    except Exception as e:
        logger.error(f"Failed to publish detection update to Redis for client {client_id}: {e}")
        # Redis fallback disabled since Redis is running in Docker
        pass

async def send_page_count_update(client_id: str, total_pages: int):
    print(f"{total_pages} pages detected")
    logger.info(f"Sending page count update - Client: {client_id}, Total pages: {total_pages}")
    try:
        await redis_manager.publish_page_count_update(client_id, total_pages)
        logger.debug(f"Page count update published to Redis successfully for client {client_id}")
    except Exception as e:
        logger.error(f"Failed to publish page count update to Redis for client {client_id}: {e}")
        # Redis fallback disabled since Redis is running in Docker  
        pass

async def send_page_result_update(client_id: str, page_num: int, result: dict):
    print(f"Page {page_num}: {result['orientation'].lower()}")
    logger.info(f"Sending page result - Client: {client_id}, Page: {page_num}, Orientation: {result['orientation']}")
    try:
        await redis_manager.publish_page_result_update(client_id, page_num, result)
        logger.debug(f"Page result published to Redis successfully for client {client_id}, page {page_num}")
    except Exception as e:
        logger.error(f"Failed to publish page result to Redis for client {client_id}, page {page_num}: {e}")
        # Redis fallback disabled since Redis is running in Docker
        pass


@app.get("/api/detection-status/{client_id}")
async def get_detection_status(client_id: str):
    logger.info(f"Status request received for client {client_id}")
    if client_id in detection_sessions:
        status = detection_sessions[client_id]
        logger.info(f"Status found for client {client_id}: {status['status']}")
        return status
    logger.warning(f"Status request for unknown client ID: {client_id}")
    return {"error": "Client ID not found"}

@app.on_event("startup")
async def startup():
    logger.info("Starting FastAPI application...")
    await redis_manager.connect()
    logger.info("Redis connection established successfully")

@app.on_event("shutdown") 
async def shutdown():
    logger.info("Shutting down FastAPI application...")
    await redis_manager.close()
    logger.info("Redis connection closed successfully")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting server on 0.0.0.0:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)