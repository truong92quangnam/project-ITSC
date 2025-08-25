# api_server.py
import os
import json
import datetime
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage as gcs
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
import asyncio
from typing import List

# Cài đặt môi trường
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["STORAGE_EMULATOR_HOST"] = "http://localhost:9199"

app = FastAPI(title="Firebase Gallery API", version="1.0.0")

# Initialize Firebase
cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred, {"projectId": "itsc"})

# Firestore client
tracking = admin_firestore.client()

class FirestoreJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
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
        """Broadcast to specific collection listeners"""
        if collection_name in self.collection_connections:
            for connection in self.collection_connections[collection_name].copy():
                try:
                    await connection.send_text(message)
                except:
                    self.collection_connections[collection_name].remove(connection)
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def broadcast_all(self, message: str):
        """Broadcast to all connections"""
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
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, collection_name)



@app.get("/api/collections/{collection_name}")
async def get_collection_data(collection_name: str, limit: int = None):
    """Lấy tất cả documents từ collection"""
    try:
        if limit:
            from google.cloud.firestore import Query
            docs = tracking.collection(collection_name).order_by("time", direction=Query.DESCENDING).limit(limit).stream()
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
#"Lấy những hình ảnh mới nhất"
@app.get("/api/collections/{collection_name}/latest")
async def get_latest_images(collection_name: str, limit: int = 10):
   
    try:
        from google.cloud.firestore import Query
        
        docs = tracking.collection(collection_name).order_by("time", direction=Query.DESCENDING).limit(limit).stream()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)