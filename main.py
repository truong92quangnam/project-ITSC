import os
import json
import datetime
import time
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage as gcs
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse

#Cài đặt môi trường
os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
os.environ["STORAGE_EMULATOR_HOST"] = "http://localhost:9199"
app=FastAPI(title="Get URL from firebase", version="1.0.0")

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

#Chỗ này là để bên FE-gallery lấy dữ liệu ra 
@app.get("/urls/{collection_name}")
async def get_urls_from_collection(collection_name: str):
    try:
        collection_ref = tracking.collection(collection_name)
        query=collection_ref.order_by('time', direction=admin_firestore.Query.DESCENDING )
        docs=query.stream()
        result=[]
        for doc in docs:
            doc_data=doc.to_dict()
            result.append(doc_data['url'])
        JSONResponse(content={'url':result})
        
        return result
    except Exception as e:
        print("Lỗi: ", e)
        return JSONResponse(content={"error": str(e)}, status_code=500)
#Chỗ này là để export dữ liệu ảnh vào một folder
def export_from_storage(filename):
    local_folder=f'D:/itsc/images/{filename}'
    try:
        for blob in bucket.list_blobs():
            if blob.name.startswith(f'{filename}/'):
                local_path = os.path.join(local_folder, blob.name)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                blob.download_to_filename(local_path)
    except Exception as e:
        print(e)

def export_from_firestore(filename):
    try:
        docs=tracking.collection(f'{filename}').stream()
        data=[]
        for doc in docs:
            data.append({ "id": doc.id, **doc.to_dict() })
            with open(f'D:/itsc/images/firestore/{filename}.json', 'w', encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=FirestoreJSONEncoder)
    except Exception as e:
        print(e)

#Chỗ này là để import thôi, phòng trường hợp đang chạy thì máy bị crash.
def import_to_firestore():
    try:
        with open("D:/itsc/images/firestore/Original.json", 'r', encoding="utf-8") as f:
            data=json.load(f)
        for doc in data:
            doc_id=doc.pop("id")
            tracking.collection('Original').document(doc_id).set(doc)

        with open("D:/itsc/images/firestore/AIService.json", 'r', encoding="utf-8") as f:
            data=json.load(f)
        for doc in data:
            doc_id=doc.pop("id")
            tracking.collection('AIService').document(doc_id).set(doc)

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
        

#Chỗ này là để bên AI đẩy dữ liệu vào đây
def update_to_firestore_gallery_collection(blob, folder):
    try:
        now = datetime.datetime.now()
        data={
            'name': blob.name,
            'url':f"http://localhost:9199/v0/b/{blob.bucket.name}/o/{blob.name.replace('/', '%2F')}?alt=media",
            'time': now
        } 
        doc_id=blob.name.replace('/','_').replace('.', '_')
        if folder.find('Undatabase/Original'):
            tracking.collection('Original').document(doc_id).set(data)
            export_from_storage('Original')
            export_from_firestore('Original')
        else:
            tracking.collection('AIService').document(doc_id).set(data)
            export_from_firestore('AIService')
            export_from_storage('AIService')
        
        #export_from_storage()
    except Exception as e:
        print(f"Skibidi: {e}")

def upload_file_to_storage(file_name, folder):
    if folder.find('Undatabase/Original'):
        url_file_location="Original"+'/'+file_name
    else:
        url_file_location="AIService"+'/'+file_name

    blob = bucket.blob(url_file_location)
    blob.upload_from_filename(folder+'/'+file_name)
    update_to_firestore_gallery_collection(blob, folder)


if __name__=="__main__":
    while True:
        try:
            folder='Undatabase/Original'
            files=os.listdir(folder)
            if files:
                for root, __, files in os.walk(folder):
                    for file_name in files:
                        file_path = root+'/'+file_name
                        print(file_path)
                        upload_file_to_storage(file_name, folder)
                        os.remove(file_path)
            
            folder='Undatabase/AIService'
            files=os.listdir(folder)
            if files:
                for root, __, files in os.walk(folder):
                    for file_name in files:
                        file_path = root+'/'+file_name
                        print(file_path)
                        upload_file_to_storage(file_name, folder)
                        os.remove(file_path)
            time.sleep(5)
        except Exception as e:
            print(e)
