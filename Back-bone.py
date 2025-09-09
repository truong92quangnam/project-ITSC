import os
import requests 
import fastapi
import json
import time
PC=[
    {
        "IP":"129.323.421.313",
        "status": True
    },
    {
        "IP":"129.323.21.324",
        "status": True
    }
]
def send_the_image(file_local=None):
    for unit in PC:
        if unit['status']==True:
            #Đẩy dữ liệu vào máy AI
            print(f'Unit {unit['IP']} is running succesfully')
            unit["status"]=False
            #Dùng os để xóa link file_local đấy.
            return True
    return False

def receive_the_image(response_from_AI=None):
    for unit in PC:
        if response_from_AI['PC']==unit['PC']:
            folder_under_data=response_from_AI['Image']
            #Từ đây push dữ liệu vào undatabase
            #<<<



            #>>>>
            unit['status']= True


if __name__=="__main__":
    #Dùng OS để tracking vào trong folder nếu nó tồn tại và có file thì mình sẽ lấy file local bằng filename
    while True:
        folder='Undatabase\AIrequest'
        files =os.listdir(folder)
        if len(files):
            for file in files:
                filename=os.path.join(folder, file)
                print(filename)
        else:   
            print('Chưa có file')

        time.sleep(5)
    

    
