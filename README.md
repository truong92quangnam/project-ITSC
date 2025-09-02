### Report of API testing.
https://github.com/truong92quangnam/itsc/blob/main/routes/README.md
Checking all of my report for testing about API. That all is Vietnamese.
### Folder Structure
```
itsc/
├── images/
│   ├── AIService/  #  This folder is used to back up data from the database AI service.
│   ├── firestore/ 
│       ├── AIService.json #This 2 files json is used to save url of each collection in firestore
│       ├── Original.json
│       ├── Photobooth.json  
│   ├── Original/   #  This folder is used to back up data from the database Original.
│   ├── Photobooth/ #  This folder is used to back up data form the database Photobooth.
├── routes/
│   └── APIcalling    # Fetch data to Front-end 
├── Undatabase/     #   The first gate let data go to database
│   ├── AIService/
│   ├── Original/ 
│   ├── Photobooth/
└── TrackingFolder.py  # Tracking data in folder Undatabase, update database, export to 1 of 2 in images  
```
### SETUP ENVIRONMENT
1. Install Firebase CLI:
    ```cmd
    npm install -g firebase-tools
    ```
2. Login Firebase:
    ```cmd
    firebase login
    ```
3. Create init
    Before,Go to your folder you want to set up and open cmd in this folder:
    ```cmd
    firebase init
    ```
    
    You wil see:
    ```cmd
    ✔ Are you ready to proceed? Yes
    ? Which Firebase features do you want to set up for this   
    directory? Press Space to select features, then Enter to   
    confirm your choices. (Press <space> to select, <a> to     
    toggle all, <i> to invert selection, and <enter> to        
    proceed)
    ❯◯ Data Connect: Set up a Firebase Data Connect service    
    ◯ Firestore: Configure security rules and indexes files   
    for Firestore
    ◯ Genkit: Setup a new Genkit project with Firebase        
    ◯ Functions: Configure a Cloud Functions directory and its
    files
    ◯ App Hosting: Enable web app deployments with App Hosting
    (Use arrow keys to reveal more choices)

    and more
    ```
4. You will choose Emulators. After, u can choose anything.
5. Choose emulators set up:
    ```cmd
    === Emulators Setup
    ? Which Firebase emulators do you want to set up? Press    
    Space to select emulators, then Enter to confirm your      
    choices. (Press <space> to select, <a> to toggle all, <i>  
    to invert selection, and <enter> to proceed)
    ◯ Data Connect Emulator
    ◯ Cloud Tasks Emulator
    ❯◯ App Hosting Emulator
    ◯ Authentication Emulator
    ◯ Functions Emulator
    ◯ Firestore Emulator
    ◯ Database Emulator
    ```

    You will choose Firestore, Storage

6. Set up port with port is suggest in in cmd

7. Create firestore.rules:
    ```
    rules_version = '2';
    service cloud.firestore {
    match /databases/{database}/documents {
        match /{document=**} {
        allow read, write: if true;
        }
    }
    }
    ```
8. Create storage.rules:
    ```
    rules_version = '2';
    service firebase.storage {
    match /b/{bucket}/o {
        match /{allPaths=**} {
        allow read, write: if true;
        }
    }
    }
    ```
9. Create firebase.json
    ```
    {
    "emulators": {
        "storage": {
        "port": 9199
        },
        "ui": {
        "enabled": true,
        "port": 4000
        },
        "firestore": {
        "port": 8080
        },
        "singleProjectMode": true
    },
    "storage": {
        "rules": "storage.rules"
    }
    }
    ```

10.When need to run:
    ### If you have some project in cloud
    ```
    firebase emulators:start
    ```
    ### Create a new project dont have in cloud
    ```
    firebase emulators:start --project '<you-need-to-set>'
    ```

    ### Run just only firestore and storage
    ```
    firebase emulators:start --project itsc --only firestore,storage
    ```

