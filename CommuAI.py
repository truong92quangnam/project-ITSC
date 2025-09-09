import requests
import time
import datetime
import os
#Địa chi của API của khác có nhiệm vụ đẩy ảnh
api_url_post='http://127.0.0.1:8188/image/post' #Tiêu chuẩn của đường link sẽ thế này

PC={
        "129.323.421.313": True
    ,
        "129.323.21.324": True
}
#Hàm đẩy ảnh vào API vào máy khác
def Post_image_to_AI(filename, API):
    api_url_post=f'http://{API}/image/post'
    with open(filename, 'rb') as f:
        response = requests.post(api_url_post, files={'file': f})
    
    if response.status_code == 200:
        print("Ảnh đã được đẩy lên server thành công!")
        print("Phản hồi từ server:", response.json())
    else:
        print(f"Không thể đẩy ảnh. Mã lỗi: {response.status_code}")
        print("Phản hồi từ server:", response.text)
    return

if __name__=="__main__":
    folder='Undatabase\AIrequest'
    while True:
        time.sleep(5)
        for unit in PC:
            if PC[unit]== True:
                files=os.listdir(folder)
                if not files:
                    print('Thư mục trống. Vui lòng chờ 5s nữa')
                    continue
                file=files[0]
                filename=os.path.join(folder, file)
                Post_image_to_AI(filename, unit)
                PC[unit]=False

