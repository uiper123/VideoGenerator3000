"""
Google Drive service for uploading processed videos.
"""
import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_google_credentials() -> Optional[service_account.Credentials]:
    """
    Get Google credentials from Base64 env var or from a file.
    
    Tries to load credentials from the GOOGLE_CREDENTIALS_BASE64 
    environment variable first. If not found, falls back to the
    google-credentials.json file.
    
    Returns:
        google.oauth2.service_account.Credentials if found, else None.
    """
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    
    if creds_json_str:
        try:
            logger.info("Loading Google credentials from Base64 environment variable.")
            creds_json = base64.b64decode(creds_json_str).decode('utf-8')
            creds_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            return credentials
        except Exception as e:
            logger.error(f"Failed to load credentials from Base64 string: {e}")
            return None
    
    # Fallback to file
    creds_path = settings.google_credentials_path
    if os.path.exists(creds_path):
        try:
            logger.info(f"Loading Google credentials from file: {creds_path}")
            credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
            return credentials
        except Exception as e:
            logger.error(f"Failed to load credentials from file {creds_path}: {e}")
            return None
            
    return None

class GoogleDriveService:
    """Service for uploading files to Google Drive."""
    
    def __init__(self):
        """Initialize Google Drive service."""
        self.credentials = get_google_credentials()
        
        if self.credentials:
            try:
                self.service = build('drive', 'v3', credentials=self.credentials)
                logger.info("Google Drive service initialized successfully.")
            except HttpError as e:
                logger.error(f"Failed to build Google Drive service: {e}")
        else:
            logger.warning("Google Drive credentials not found, using mock service")
    
    def _execute_request(self, request):
        """Execute a Google API request with error handling."""
        if not self.service:
            logger.warning("Attempted to execute request with mock service.")
            return None
        try:
            return request.execute()
        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return None
    
    def create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a folder in Google Drive."""
        if not self.service:
            logger.info(f"Mock folder creation: {folder_name}")
            return {"id": "mock_folder_id", "name": folder_name}

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        # Check if folder already exists
        existing_folder = self.find_folder(folder_name, parent_id)
        if existing_folder:
            logger.info(f"Folder '{folder_name}' already exists with ID: {existing_folder['id']}")
            return existing_folder

        request = self.service.files().create(body=file_metadata, fields='id, name')
        folder = self._execute_request(request)
        
        if folder:
            logger.info(f"Folder '{folder.get('name')}' created with ID: {folder.get('id')}")
            
            # Share the folder with the user
            user_email = os.getenv('USER_EMAIL')  # You can set this in Railway
            if user_email:
                self.share_folder_with_user(folder.get('id'), user_email)
        
        return folder

    def share_folder_with_user(self, folder_id: str, user_email: str):
        """Share a folder with a specific user email."""
        if not self.service:
            logger.info(f"Mock sharing folder {folder_id} with {user_email}")
            return

        try:
            permission = {
                'type': 'user',
                'role': 'writer',  # Full edit access
                'emailAddress': user_email
            }
            
            request = self.service.permissions().create(
                fileId=folder_id,
                body=permission,
                fields='id'
            )
            result = self._execute_request(request)
            
            if result:
                logger.info(f"Successfully shared folder {folder_id} with {user_email}")
            else:
                logger.warning(f"Failed to share folder {folder_id} with {user_email}")
                
        except Exception as e:
            logger.error(f"Error sharing folder {folder_id} with {user_email}: {e}")

    def find_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find a folder by name within an optional parent folder."""
        if not self.service:
            return None
            
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        request = self.service.files().list(q=query, fields="files(id, name)")
        response = self._execute_request(request)
        
        if response and response.get('files'):
            return response['files'][0]
        return None
    
    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload a single file to Google Drive."""
        if not self.service:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            logger.info(f"Mock upload: {os.path.basename(file_path)} ({file_size} bytes) to folder {folder_id or 'root'}")
            return {
                "id": f"mock_file_id_{os.path.basename(file_path)}",
                "name": os.path.basename(file_path),
                "webViewLink": "https://mock.drive.url/file/view",
                "size": file_size
            }

        file_metadata = {
            'name': os.path.basename(file_path)
        }
        if folder_id:
            file_metadata['parents'] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, size'
        )
        
        file = self._execute_request(request)
        if file:
            logger.info(f"File '{file.get('name')}' uploaded with ID: {file.get('id')}")
        return file
    
    def upload_multiple_files(self, file_paths: List[str], folder_name: str) -> List[Dict[str, Any]]:
        """Upload multiple files to a specific folder, creating it if it doesn't exist."""
        if not self.service:
            results = []
            for file_path in file_paths:
                 results.append(self.upload_file(file_path, folder_name))
            return results

        folder = self.create_folder(folder_name)
        if not folder:
            logger.error(f"Failed to create or find folder '{folder_name}'. Aborting upload.")
            return []

        upload_results = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"File not found, skipping upload: {file_path}")
                continue
            
            result = self.upload_file(file_path, folder['id'])
            if result:
                upload_results.append({
                    "success": True,
                    "file_path": file_path,
                    "file_name": result.get('name'),
                    "file_id": result.get('id'),
                    "file_url": result.get('webViewLink'),
                    "size_bytes": int(result.get('size', 0))
                })
            else:
                upload_results.append({
                    "success": False,
                    "file_path": file_path,
                    "error": "Upload failed"
                })

        return upload_results 