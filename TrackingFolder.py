import time
import os
import json
import datetime
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage as gcs 
#Cài đặt môi trường
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["STORAGE_EMULATOR_HOST"] = "http://localhost:9199"

# Cấp quyền vào đâu
cred = credentials.Certificate("serviceAccount.json")
firebase_admin.initialize_app(cred, {"projectId": "itsc"})

# Mở cổng lấy xô
storage_client = gcs.Client(project="itsc", credentials=AnonymousCredentials())
bucket = storage_client.bucket("itsc.appspot.com")

# Firestore để mà lưu mấy con url lấy hình ảnh ra để làm việc
tracking= admin_firestore.client()


class FirestoreJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)


#Chỗ này là để export dữ liệu ảnh vào một folder
#Xuất và đẩy dữ liệu đã xong.
def export_from_storage(blob, filename):
    local_folder=f'images\{filename}'
    if filename=='Original':
        local_path = os.path.join(local_folder, blob.name.replace('Original/',''))
    elif filename=='AIService':
        local_path = os.path.join(local_folder, blob.name.replace('AIService/',''))
    else:
        local_path = os.path.join(local_folder, blob.name.replace('Photobooth/',''))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    blob.download_to_filename(local_path)

def export_from_firestore(filename):
    try:
        docs=tracking.collection(f'{filename}').stream()
        data=[]
        for doc in docs:
            data.append({ "id": doc.id, **doc.to_dict() })
            with open(f'images/firestore/{filename}.json', 'w', encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=FirestoreJSONEncoder)
    except Exception as e:
        print(e)

def import_to_storage():
    try:
        for root,_,files in os.walk('images/Original'):
            for file_name in files:
                local_path=root+'/'+file_name
                url_file_location=f"Original/{file_name}"
                blob=bucket.blob(url_file_location)
                blob.upload_from_filename(local_path)
        
        for root,_,files in os.walk('images/AIService'):
            for file_name in files:
                local_path=root+'/'+file_name
                url_file_location=f"AIService/{file_name}"
                blob=bucket.blob(url_file_location)
                blob.upload_from_filename(local_path)

    except:
        print('haha')
        

#-----------------------------------------------Chỗ này là để bên AI đẩy dữ liệu vào đây---------------------------------------------------
def update_to_firestore_gallery_collection(blob, folder):
    try:
        now = datetime.datetime.now()
        data={
            'name': blob.name,
            'url':f"https://localhost:9199/v0/b/{blob.bucket.name}/o/{blob.name.replace('/', '%2F')}?alt=media",
            'time': now
        } 
        doc_id=blob.name.replace('/','_').replace('.', '_')
        if folder=="Original":
            tracking.collection('Original').document(doc_id).set(data)
        elif folder=="AIService":
            tracking.collection('AIService').document(doc_id).set(data)
        else:
            tracking.collection('Photobooth').document(doc_id).set(data)

        #export_from_storage()
    except Exception as e:
        print(f"Skibidi: {e}")

def upload_file_to_storage(file_name, folder):
    if folder=='Original':
        url_file_location="Original"+'/'+file_name
        blob = bucket.blob(url_file_location)
        blob.upload_from_filename('Undatabase/Original'+'/'+file_name)
        export_from_storage(blob, 'Original')
        update_to_firestore_gallery_collection(blob, folder)

    elif folder=='AIService':
        url_file_location="AIService"+'/'+file_name
        blob = bucket.blob(url_file_location)
        blob.upload_from_filename('Undatabase/AIService'+'/'+file_name)
        export_from_storage(blob, 'AIService')
        update_to_firestore_gallery_collection(blob, folder)
    else:
        url_file_location="Photobooth"+'/'+file_name
        blob = bucket.blob(url_file_location)
        blob.upload_from_filename('Undatabase/Photobooth'+'/'+file_name)
        export_from_storage(blob, 'Photobooth')
        update_to_firestore_gallery_collection(blob, folder)

#-------------------------------------------------------------------------------------------------------------------------------------------#

def sync_images_folders_to_storage():
    """Monitor images/ folders and sync new files to Firebase Storage"""
    folders_to_check = [
        ('images/Original', 'Original'),
        ('images/AIService', 'AIService'), 
        ('images/Photobooth', 'Photobooth')
    ]
    
    for local_folder, storage_folder in folders_to_check:
        if os.path.exists(local_folder):
            try:
                # Get list of files in Firebase Storage for this folder
                blobs = list(bucket.list_blobs(prefix=f"{storage_folder}/"))
                storage_files = {blob.name.replace(f"{storage_folder}/", "") for blob in blobs}
                
                # Get list of files in local folder
                local_files = [f for f in os.listdir(local_folder) if os.path.isfile(os.path.join(local_folder, f))]
                
                # Find files that are in local but not in storage
                new_files = [f for f in local_files if f not in storage_files]
                
                if new_files:
                    print(f"🆕 Found {len(new_files)} new files in {local_folder}")
                    for file_name in new_files:
                        try:
                            local_path = os.path.join(local_folder, file_name)
                            url_file_location = f"{storage_folder}/{file_name}"
                            blob = bucket.blob(url_file_location)
                            blob.upload_from_filename(local_path)
                            update_to_firestore_gallery_collection(blob, storage_folder)
                            print(f"✅ Auto-synced {storage_folder}: {file_name}")
                        except Exception as e:
                            print(f"❌ Error auto-syncing {storage_folder}/{file_name}: {e}")
                else:
                    print(f"✅ {local_folder} - All files synced")
                    
            except Exception as e:
                print(f"❌ Error checking {local_folder}: {e}")

#-------------------------------------------------------------------------------------------------------------------------------------------#

def sync_existing_files_to_storage():
    """Sync all existing files in images/ folders to Firebase Storage"""
    print("🔄 Syncing existing files to Firebase Storage...")
    
    # Sync Original folder
    original_path = 'images/Original'
    if os.path.exists(original_path):
        files = [f for f in os.listdir(original_path) if os.path.isfile(os.path.join(original_path, f))]
        print(f"📂 Found {len(files)} files in {original_path}")
        for file_name in files:
            try:
                local_path = os.path.join(original_path, file_name)
                url_file_location = f"Original/{file_name}"
                blob = bucket.blob(url_file_location)
                blob.upload_from_filename(local_path)
                update_to_firestore_gallery_collection(blob, 'Original')
                print(f"✅ Synced Original: {file_name}")
            except Exception as e:
                print(f"❌ Error syncing Original/{file_name}: {e}")
    
    # Sync AIService folder  
    aiservice_path = 'images/AIService'
    if os.path.exists(aiservice_path):
        files = [f for f in os.listdir(aiservice_path) if os.path.isfile(os.path.join(aiservice_path, f))]
        print(f"📂 Found {len(files)} files in {aiservice_path}")
        for file_name in files:
            try:
                local_path = os.path.join(aiservice_path, file_name)
                url_file_location = f"AIService/{file_name}"
                blob = bucket.blob(url_file_location)
                blob.upload_from_filename(local_path)
                update_to_firestore_gallery_collection(blob, 'AIService')
                print(f"✅ Synced AIService: {file_name}")
            except Exception as e:
                print(f"❌ Error syncing AIService/{file_name}: {e}")
    
    # Sync Photobooth folder
    photobooth_path = 'images/Photobooth'
    if os.path.exists(photobooth_path):
        files = [f for f in os.listdir(photobooth_path) if os.path.isfile(os.path.join(photobooth_path, f))]
        print(f"📂 Found {len(files)} files in {photobooth_path}")
        for file_name in files:
            try:
                local_path = os.path.join(photobooth_path, file_name)
                url_file_location = f"Photobooth/{file_name}"
                blob = bucket.blob(url_file_location)
                blob.upload_from_filename(local_path)
                update_to_firestore_gallery_collection(blob, 'Photobooth')
                print(f"✅ Synced Photobooth: {file_name}")
            except Exception as e:
                print(f"❌ Error syncing Photobooth/{file_name}: {e}")
    
    print("🎉 Sync completed!")

if __name__=="__main__":
    print("🚀 TrackingFolder Started!")
    print("👀 Monitoring Undatabase folders...")
    print("📁 Original: Undatabase/Original → images/Original → Firebase Storage")  
    print("🤖 AIService: Undatabase/AIService → images/AIService → Firebase Storage")
    print("📸 Photobooth: Undatabase/Photobooth → images/Photobooth → Firebase Storage")
    print("=" * 50)
    
    # First, sync all existing files to Firebase Storage
    sync_existing_files_to_storage()
    print("=" * 50)
    print("👀 Starting continuous monitoring...")
    
    while True:
        try:
            print("🔍 Checking Undatabase folders...")
            
            # Check Original folder
            folder='Undatabase/Original'
            if os.path.exists(folder):
                files=os.listdir(folder)
                if files:
                    print(f"📂 Processing {len(files)} files in {folder}")
                    for root, __, files in os.walk(folder):
                        for file_name in files:
                            file_path = root+'/'+file_name
                            print(f"📤 Uploading: {file_path}")
                            upload_file_to_storage(file_name, 'Original')
                            os.remove(file_path)
                            print(f"✅ Processed: {file_name}")
                else:
                    print(f"📂 {folder} is empty")
            else:
                print(f"📂 Creating {folder}...")
                os.makedirs(folder, exist_ok=True)
            
            # Check AIService folder
            folder='Undatabase/AIService'
            if os.path.exists(folder):
                files=os.listdir(folder)
                if files:
                    print(f"📂 Processing {len(files)} files in {folder}")
                    for root, __, files in os.walk(folder):
                        for file_name in files:
                            file_path = root+'/'+file_name
                            print(f"📤 Uploading: {file_path}")
                            upload_file_to_storage(file_name, 'AIService')
                            os.remove(file_path)
                            print(f"✅ Processed: {file_name}")
                else:
                    print(f"📂 {folder} is empty")
            else:
                print(f"📂 Creating {folder}...")
                os.makedirs(folder, exist_ok=True)
            
            # Check Photobooth folder
            folder='Undatabase/Photobooth'
            if os.path.exists(folder):
                files=os.listdir(folder)
                if files:
                    print(f"📂 Processing {len(files)} files in {folder}")
                    for root, __, files in os.walk(folder):
                        for file_name in files:
                            file_path=root+'/'+file_name
                            print(f"📤 Uploading: {file_path}")
                            upload_file_to_storage(file_name, 'Photobooth')
                            os.remove(file_path)
                            print(f"✅ Processed: {file_name}")
                else:
                    print(f"📂 {folder} is empty")
            else:
                print(f"📂 Creating {folder}...")
                os.makedirs(folder, exist_ok=True)

            print("🔍 Checking images/ folders for new files...")
            # Also check images/ folders for new files
            sync_images_folders_to_storage()

            print("💤 Sleeping for 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5)