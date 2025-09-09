import os
import json
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore, storage
from fastapi import FastAPI, HTTPException, WebSocket, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from google.cloud.firestore import Query
import threading
import asyncio
import time
from pathlib import Path

os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["STORAGE_EMULATOR_HOST"] = "http://localhost:9199"

app = FastAPI(title="Firebase Gallery API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred, {
    "projectId": "itsc",
    "storageBucket": "itsc.appspot.com"
})

tracking = admin_firestore.client()
bucket = storage.bucket()

class FirestoreJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle datetime objects
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        # Handle Firebase sentinel objects (SERVER_TIMESTAMP, DELETE_FIELD, etc.)
        if hasattr(obj, '__class__') and 'Sentinel' in str(type(obj)):
            return None  # or return a string representation
        # Handle other Firebase admin objects
        if str(type(obj)).startswith("<class 'google.cloud.firestore"):
            return str(obj)
        return super().default(obj)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.collection_connections = {}

    async def connect(self, websocket: WebSocket, collection_name: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if collection_name:
            if collection_name not in self.collection_connections:
                self.collection_connections[collection_name] = []
            self.collection_connections[collection_name].append(websocket)
        print(f"New connection to {collection_name}. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, collection_name: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if collection_name and collection_name in self.collection_connections:
            if websocket in self.collection_connections[collection_name]:
                self.collection_connections[collection_name].remove(websocket)

    async def broadcast_to_collection(self, message: str, collection_name: str):
        if collection_name in self.collection_connections:
            for connection in self.collection_connections[collection_name].copy():
                try:
                    await connection.send_text(message)
                except:
                    self.collection_connections[collection_name].remove(connection)
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def broadcast_all(self, message: str):
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except:
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws/{collection_name}")
async def websocket_endpoint(websocket: WebSocket, collection_name: str):
    await manager.connect(websocket, collection_name)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, collection_name)

@app.get("/api/collections/{collection_name}")
async def get_collection_data(collection_name: str, limit: int = None):
    try:
        if limit:
            docs = tracking.collection(collection_name).order_by("time", direction=Query.ASCENDING).limit(limit).stream()
        else:
            docs = tracking.collection(collection_name).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            data.append(doc_data)
        return JSONResponse(
            content=json.loads(json.dumps(data, cls=FirestoreJSONEncoder))
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------Phần tử dưới này là để theo dõi các hoạt động thay đổi của dữ liệu-----------------------

def listen_to_firestore(collection_name):
    def on_snapshot(col_snapshot, changes, read_time):
        docs = tracking.collection(collection_name).order_by("time", direction=Query.ASCENDING).limit(100).stream()
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            data.append(doc_data)
        # Broadcast đến WebSocket
        asyncio.run(manager.broadcast_to_collection(json.dumps(data, cls=FirestoreJSONEncoder), collection_name))

    # Bắt đầu lắng nghe nào tình yêu của anh.
    tracking.collection(collection_name).on_snapshot(on_snapshot)

def start_firestore_listener_thread(collection_name):
    listener_thread = threading.Thread(target=listen_to_firestore, args=(collection_name,), daemon=True)
    listener_thread.start()

@app.on_event("startup")
async def startup_event():
    # Lúc bắt đầu nó chạy ở phần này đầu tiên để nhảy vào các phần tử ở trên.
    start_firestore_listener_thread("Original")  
    start_firestore_listener_thread("AIService")
    start_firestore_listener_thread("Photobooth")

#Khi server FastAPI chạy, nó sẽ tạo một thread riêng để lắng nghe thay đổi của Firestore collection "Original".
#Mỗi lần có thay đổi, dữ liệu mới nhất sẽ được lấy ra, chuyển thành JSON, và broadcast tới các client WebSocket đang lắng nghe.

@app.post("/upload/{collection}")
async def upload_image(collection: str, image: UploadFile = File(...)):
    try:
        # Ensure collection is valid
        if collection not in ["Original", "AIService", "Photobooth"]:
            raise HTTPException(status_code=400, detail="Invalid collection name")
        
        # Create directory if not exists - use ../images from routes folder  
        upload_dir = Path(f"../images/{collection}")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(time.time() * 1000)
        file_extension = image.filename.split('.')[-1] if '.' in image.filename else 'png'
        filename = f"{collection.lower()}-{timestamp}.{file_extension}"
        file_path = upload_dir / filename
        
        # Save file locally
        content = await image.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # For Firebase emulator, we'll store files locally and serve via static endpoint
        # Skip Firebase Storage upload to avoid auth issues with emulator
        storage_url = f"http://localhost:8000/static/{collection}/{filename}"
        
        # Create Firestore document
        doc_data = {
            "name": filename,
            "originalName": image.filename,
            "size": len(content),
            "contentType": image.content_type,
            "time": admin_firestore.SERVER_TIMESTAMP,
            "url": storage_url,
            "storagePath": f"{collection}/{filename}",
            "localPath": str(file_path)
        }
        
        # Add to Firestore
        doc_ref = tracking.collection(collection).document()
        doc_ref.set(doc_data)
        
        # Notify WebSocket clients
        broadcast_data = {
            "type": "document_added",
            "collection": collection,
            "data": {
                "id": doc_ref.id,
                "name": filename,
                "originalName": image.filename,
                "size": len(content),
                "contentType": image.content_type,
                "time": int(time.time() * 1000),  # Use actual timestamp instead of SERVER_TIMESTAMP
                "url": storage_url,
                "storagePath": f"{collection}/{filename}",
                "localPath": str(file_path),
                "uploadTime": time.time()
            }
        }
        await manager.broadcast_to_collection(json.dumps(broadcast_data, cls=FirestoreJSONEncoder), collection)
        
        return JSONResponse({
            "success": True,
            "message": f"Image uploaded to {collection}",
            "filename": filename,
            "id": doc_ref.id,
            "url": storage_url,
            "localPath": str(file_path)
        })
    
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/static/{collection}/{filename}")
async def serve_static_file(collection: str, filename: str):
    try:
        # Ensure collection is valid
        if collection not in ["Original", "AIService", "Photobooth"]:
            raise HTTPException(status_code=400, detail="Invalid collection name")
        
        # Build file path - use ../images from routes folder
        file_path = Path(f"../images/{collection}/{filename}")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file
        return FileResponse(str(file_path))
        
    except Exception as e:
        print(f"Static file error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    try:
        # Test Firestore connection
        collections = ["Original", "AIService", "Photobooth"]
        status = {}
        
        for collection in collections:
            try:
                docs = tracking.collection(collection).limit(1).stream()
                count = len(list(docs))
                status[collection] = {"status": "connected", "test_query": "success"}
            except Exception as e:
                status[collection] = {"status": "error", "error": str(e)}
        
        return JSONResponse({
            "status": "healthy",
            "firebase": "connected",
            "firestore_emulator": "localhost:8080",
            "storage_emulator": "localhost:9199",
            "collections": status,
            "websocket_connections": len(manager.active_connections)
        })
    
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "error": str(e)
        }, status_code=500)

@app.post("/api/broadcast")
async def broadcast_message(message: dict):
    """Endpoint for AI model server to send WebSocket broadcasts"""
    try:
        if "collection" in message:
            await manager.broadcast_to_collection(json.dumps(message), message["collection"])
        else:
            await manager.broadcast_all(json.dumps(message))
        return {"success": True, "message": "Broadcast sent"}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)