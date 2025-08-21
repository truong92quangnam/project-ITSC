import os
folder='Undatabase'
files=os.listdir(folder)

for root, dirs, files in os.walk(folder):
    for file_name in files:
        file_path = os.path.join(root, file_name)
        print(file_path)
