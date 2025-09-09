from flask import Flask, request, jsonify
import os
from CommuAI import PC

app=Flask(__name__)

#Thư mục lưu trữ ảnh được đẩy lên
UPLOAD_FOLDER='Undatabase/AIService'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400  
    file = request.files['file']
    IP=request.files['IP']
    PC[IP]=True
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filepath=os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        return jsonify({"message": "File uploaded successfully", "filename": file.filename}), 200

if __name__=='__main__':
    app.run(host='0.0.0.0', port=5000)