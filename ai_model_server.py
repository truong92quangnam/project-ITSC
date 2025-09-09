import os
import time
import asyncio
import requests
from pathlib import Path
from PIL import Image
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

print("🚀 AI Model Server Starting...")

# Firebase setup
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["STORAGE_EMULATOR_HOST"] = "http://localhost:9199"

try:
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccount.json")
        firebase_admin.initialize_app(cred, {"projectId": "itsc"})
    
    db = admin_firestore.client()
    print("✅ Firebase initialized")
except Exception as e:
    print(f"⚠️  Firebase init error: {e}")
    db = None

class ImageProcessor:
    def __init__(self):
        self.processing_queue = []
        
    def simulate_anime_generation(self, input_path: str, output_path: str):
        """Simulate AI anime generation - Tạm thời copy + thêm effect đơn giản"""
        try:
            print(f"🎨 Processing: {input_path} → {output_path}")
            
            # Mở ảnh gốc
            image = Image.open(input_path)
            
            # Resize if too large
            if image.width > 1024 or image.height > 1024:
                image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Simulate processing time
            print("⏳ AI processing...")
            time.sleep(2)  # Giả lập AI processing
            
            # Save processed image
            image.save(output_path, 'PNG', quality=95)
            print(f"✅ Generated anime version: {os.path.basename(output_path)}")
            return True
            
        except Exception as e:
            print(f"❌ Error processing {input_path}: {e}")
            return False
    
    def process_new_image(self, original_path: str, filename: str):
        """Process new image from Original to AIService - Synchronous version"""
        try:
            # Create output path
            output_dir = Path("images/AIService")
            output_dir.mkdir(exist_ok=True)
            
            # Generate AI filename
            timestamp = int(time.time() * 1000)
            name_without_ext = Path(filename).stem
            ai_filename = f"ai-processed-{timestamp}.png"
            output_path = output_dir / ai_filename
            
            print(f"🤖 Processing {filename} → {ai_filename}...")
            
            # Simulate AI generation
            success = self.simulate_anime_generation(original_path, str(output_path))
            
            if success and db:
                # Add to Firestore AIService collection
                doc_data = {
                    "filename": ai_filename,
                    "originalName": filename,
                    "originalPath": original_path,
                    "generatedTime": admin_firestore.SERVER_TIMESTAMP,
                    "style": "anime",
                    "status": "completed",
                    "path": f"images/AIService/{ai_filename}",
                    "url": f"http://localhost:8000/static/AIService/{ai_filename}"
                }
                
                try:
                    doc_ref = db.collection("AIService").document()
                    doc_ref.set(doc_data)
                    print(f"📄 Added to Firestore: {doc_ref.id}")
                    
                    # Send WebSocket notification
                    import requests
                    import json
                    websocket_data = {
                        "type": "image_generated",
                        "collection": "AIService", 
                        "filename": ai_filename,
                        "originalName": filename,
                        "image_url": f"http://localhost:8000/static/AIService/{ai_filename}",
                        "firestore_id": doc_ref.id
                    }
                    
                    # Broadcast to WebSocket clients
                    try:
                        requests.post("http://localhost:8000/api/broadcast", 
                                    json=websocket_data, timeout=1)
                        print(f"📡 WebSocket notification sent")
                    except Exception as ws_error:
                        print(f"⚠️  WebSocket notification failed: {ws_error}")
                        
                except Exception as e:
                    print(f"⚠️  Firestore error: {e}")
                
                return True
        
        except Exception as e:
            print(f"❌ Error in AI processing: {e}")
            return False

class OriginalFolderWatcher(FileSystemEventHandler):
    def __init__(self, processor: ImageProcessor):
        self.processor = processor
        self.processed_files = set()  # Track processed files to avoid duplicates
    
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = event.src_path
        filename = os.path.basename(file_path)
        
        # Only process image files
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return
            
        # Avoid duplicate processing
        if file_path in self.processed_files:
            return
            
        self.processed_files.add(file_path)
        
        print(f"🔍 New image detected: {filename}")
        
        # Wait a moment for file to be fully written
        time.sleep(1)
        
        # Process synchronously
        self.processor.process_new_image(file_path, filename)

def start_watching():
    """Start watching Original folder for new images"""
    processor = ImageProcessor()
    event_handler = OriginalFolderWatcher(processor)
    observer = Observer()
    
    # Watch Original folder
    watch_path = "images/Original"
    if not os.path.exists(watch_path):
        os.makedirs(watch_path, exist_ok=True)
        print(f"📁 Created watch directory: {watch_path}")
    
    observer.schedule(event_handler, watch_path, recursive=False)
    observer.start()
    
    print("🤖 AI Model Server Started!")
    print(f"👀 Watching: {watch_path}")
    print(f"🎨 Auto-generating anime style images...")
    print(f"📁 Output: images/AIService/")
    print(f"🔥 Firestore: AIService collection")
    print("=" * 50)
    print("💡 Upload an image to images/Original/ to test!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n🛑 AI Model Server stopped")
    
    observer.join()

if __name__ == "__main__":
    print("🚀 Starting AI Model Server...")
    
    # Check if Firebase emulators are running
    try:
        print("🔍 Checking Firebase emulators...")
        response = requests.get("http://localhost:8080", timeout=2)
        print("✅ Firebase emulators detected")
    except Exception as e:
        print(f"⚠️  Firebase emulators check: {e}")
        print("🔧 Make sure Firebase emulators are running")
    
    try:
        start_watching()
    except Exception as e:
        print(f"💥 Error starting AI server: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
