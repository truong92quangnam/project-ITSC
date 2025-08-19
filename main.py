import os
import json
import firebase_admin
from firebase_admin import credentials, firestore as admin_firestore
from google.auth.credentials import AnonymousCredentials
from google.cloud import storage as gcs
from fastapi import FastAPI, HTTPException


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


#Chỗ này là để bên FE-gallery lấy dữ liệu ra 
@app.get("/urls/{collection_name}") #collection sẽ là gallery đã được tồn tại trong firestore
async def get_urls_from_collection(collection_name:str):
    try:
        collection_def=tracking.collection(collection_name)
        docs=collection_def.stream()

        urls=[]
        for doc in docs:
            url_data=doc.to_dict()
            url_data['url']
            urls.append(url_data)
        return urls
    
    except Exception as e:
        print("Lỗi: ", e)
#Chỗ này là để export dữ liệu ảnh vào một folder
def export_from_storage():
    local_folder='D:/itsc/images'
    try:
        for blob in bucket.list_blobs():
            if blob.name.startswith('Gallery-FE/'):
                local_path = os.path.join(local_folder, blob.name)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                blob.download_to_filename(local_path)
    except Exception as e:
        print(e)

def export_from_firestore():
    try:
        docs=tracking.collection('gallery-FE').stream()
        data=[]
        for doc in docs:
            data.append({ "id": doc.id, **doc.to_dict() })
            with open('D:/itsc/images/firestore/gallery-FE.json', 'w', encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(e)

#Chỗ này là để import thôi, phòng trường hợp đang chạy thì máy bị crash.
def import_to_firestore():
    try:
        with open("D:/itsc/images/firestore/gallery-FE.json", 'r', encoding="utf-8") as f:
            data=json.load(f)
        for doc in data:
            doc_id=doc.pop("id")
            tracking.collection('gallery-FE').document(doc_id).set(doc)
    except Exception as e:
        print(e)

def import_to_storage():
    try:
        for root,_,files in os.walk('images/Gallery-FE'):
            for file_name in files:
                local_path=root+'/'+file_name
                print(local_path)
                url_file_location=f"Gallery-FE/{file_name}"
                blob=bucket.blob(url_file_location)
                blob.upload_from_filename(local_path)
    except:
        print('haha')
        

#Chỗ này là để bên AI đẩy dữ liệu vào đây
def update_to_firestore_gallery_collection(blob):
    try:
        data={
            'name': blob.name,
            'url':f"http://localhost:9199/v0/b/{blob.bucket.name}/o/{blob.name.replace('/', '%2F')}?alt=media"
        } 
        doc_id=blob.name.replace('/','_').replace('.', '_')
        tracking.collection('gallery-FE').document(doc_id).set(data)
        export_from_firestore()
        export_from_storage()
    except Exception as e:
        print(f"Skibidi: {e}")

def upload_file_gallery(url_file, local_file):
    url_file_location=f"Gallery-FE/{url_file}"
    blob = bucket.blob(url_file_location)
    blob.upload_from_filename(local_file)
    update_to_firestore_gallery_collection(blob)

if __name__=="__main__":
    try:
        folder='Undatabase'
        files=os.listdir(folder)
        if files:
            for root, dirs, files in os.walk(folder):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    upload_file_gallery(file_name, file_path)
                    os.remove(file_path)
    except Exception as e:
        print(e)
