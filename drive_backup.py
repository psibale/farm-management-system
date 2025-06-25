from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os

# Path to your data folder
DATA_FOLDER = "data"

def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # This will open a browser to log in
    return GoogleDrive(gauth)

def backup_files_to_drive():
    drive = authenticate_drive()
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith(".xlsx"):
            file_path = os.path.join(DATA_FOLDER, filename)
            gfile = drive.CreateFile({'title': filename})
            gfile.SetContentFile(file_path)
            gfile.Upload()
            print(f"Uploaded: {filename}")

if __name__ == "__main__":
    backup_files_to_drive()
