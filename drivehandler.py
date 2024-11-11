from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Important for automation!!!
# https://stackoverflow.com/questions/24419188/automating-pydrive-verification-process

gauth = GoogleAuth()
gauth.LocalWebserverAuth()

drive = GoogleDrive(gauth)

def download_file(drive, file_id):
    gfile = drive.CreateFile({'id': '13FKnsbF8RDoQZJ6DCQtirMvfuX4AUerR'})
    return gfile

gfile = drive.CreateFile({'id': '13FKnsbF8RDoQZJ6DCQtirMvfuX4AUerR'})
