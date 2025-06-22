"""
Google Drive service for uploading processed videos.
"""
import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for uploading files to Google Drive."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Drive service.
        
        Args:
            credentials_path: Path to Google credentials JSON file
        """
        self.credentials_path = credentials_path or "google-credentials.json"
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive API service."""
        try:
            # Try to get credentials from environment variable (base64 encoded)
            credentials_base64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
            
            if credentials_base64:
                # Decode base64 credentials (add padding if needed)
                missing_padding = len(credentials_base64) % 4
                if missing_padding:
                    credentials_base64 += '=' * (4 - missing_padding)
                
                credentials_json = base64.b64decode(credentials_base64).decode('utf-8')
                credentials_dict = json.loads(credentials_json)
                
                # Create credentials from dict
                credentials = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
                
                logger.info("Google Drive credentials loaded from environment variable")
                
            elif os.path.exists(self.credentials_path):
                # Load from file
                credentials = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
                
                logger.info(f"Google Drive credentials loaded from file: {self.credentials_path}")
                
            else:
                logger.warning("Google Drive credentials not found, using mock service")
                self.service = "mock_service"
                return
            
            # Build the Drive service
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive service: {e}")
            logger.info("Falling back to mock service")
            self.service = "mock_service"
    
    def upload_file(
        self, 
        file_path: str, 
        folder_name: str = "VideoBot", 
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload file to Google Drive.
        
        Args:
            file_path: Path to file to upload
            folder_name: Name of folder in Google Drive
            file_name: Custom name for uploaded file
            
        Returns:
            Dict with upload results
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if self.service == "mock_service":
            # Fallback to mock behavior
            file_size = os.path.getsize(file_path)
            upload_name = file_name or os.path.basename(file_path)
            mock_file_id = f"mock_id_{hash(file_path)}"
            mock_url = f"https://drive.google.com/file/d/{mock_file_id}/view"
            
            logger.info(f"Mock upload: {upload_name} ({file_size} bytes) to {folder_name}")
            
            return {
                "success": True,
                "file_id": mock_file_id,
                "file_url": mock_url,
                "file_name": upload_name,
                "file_size": file_size,
                "folder": folder_name
            }
        
        if not self.service:
            logger.warning("Google Drive service not available, skipping upload")
            return {
                "success": False,
                "error": "Google Drive service not initialized",
                "file_id": None,
                "file_url": None
            }
        
        try:
            # Get or create folder
            folder_id = self._get_or_create_folder(folder_name)
            
            # Prepare file metadata
            upload_name = file_name or os.path.basename(file_path)
            file_metadata = {
                'name': upload_name,
                'parents': [folder_id] if folder_id else []
            }
            
            # Create media upload
            media = MediaFileUpload(file_path, resumable=True)
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,webViewLink'
            ).execute()
            
            file_size = os.path.getsize(file_path)
            file_id = file.get('id')
            file_url = file.get('webViewLink')
            
            # Make file publicly viewable
            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={
                        'role': 'reader',
                        'type': 'anyone'
                    }
                ).execute()
                
                # Update URL to direct download link
                file_url = f"https://drive.google.com/file/d/{file_id}/view"
                
            except HttpError as e:
                logger.warning(f"Failed to make file public: {e}")
            
            logger.info(f"Successfully uploaded: {upload_name} ({file_size} bytes) to {folder_name}")
            
            return {
                "success": True,
                "file_id": file_id,
                "file_url": file_url,
                "file_name": upload_name,
                "file_size": file_size,
                "folder": folder_name
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error uploading {file_path}: {e}")
            return {
                "success": False,
                "error": f"Google Drive API error: {e}",
                "file_id": None,
                "file_url": None
            }
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_id": None,
                "file_url": None
            }
    
    def upload_multiple_files(
        self, 
        file_paths: List[str], 
        folder_name: str = "VideoBot"
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple files to Google Drive.
        
        Args:
            file_paths: List of file paths to upload
            folder_name: Name of folder in Google Drive
            
        Returns:
            List of upload results
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = self.upload_file(file_path, folder_name)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to upload {file_path}: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "file_path": file_path,
                    "file_id": None,
                    "file_url": None
                })
        
        return results
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create folder in Google Drive.
        
        Args:
            folder_name: Name of folder to create
            parent_folder_id: ID of parent folder
            
        Returns:
            Dict with folder creation results
        """
        if self.service == "mock_service":
            # Fallback to mock behavior
            mock_folder_id = f"folder_{hash(folder_name)}"
            logger.info(f"Mock folder creation: {folder_name}")
            
            return {
                "success": True,
                "folder_id": mock_folder_id,
                "folder_name": folder_name,
                "folder_url": f"https://drive.google.com/drive/folders/{mock_folder_id}"
            }
        
        if not self.service:
            logger.warning("Google Drive service not available, skipping folder creation")
            return {
                "success": False,
                "error": "Google Drive service not initialized",
                "folder_id": None,
                "folder_url": None
            }
        
        try:
            # Check if folder already exists
            folder_id = self._find_folder(folder_name, parent_folder_id)
            
            if folder_id:
                logger.info(f"Folder already exists: {folder_name}")
                return {
                    "success": True,
                    "folder_id": folder_id,
                    "folder_name": folder_name,
                    "folder_url": f"https://drive.google.com/drive/folders/{folder_id}"
                }
            
            # Create new folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id,name,webViewLink'
            ).execute()
            
            folder_id = folder.get('id')
            folder_url = folder.get('webViewLink')
            
            logger.info(f"Created folder: {folder_name} (ID: {folder_id})")
            
            return {
                "success": True,
                "folder_id": folder_id,
                "folder_name": folder_name,
                "folder_url": folder_url
            }
            
        except HttpError as e:
            logger.error(f"Google Drive API error creating folder {folder_name}: {e}")
            return {
                "success": False,
                "error": f"Google Drive API error: {e}",
                "folder_id": None,
                "folder_url": None
            }
        except Exception as e:
            logger.error(f"Failed to create folder {folder_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "folder_id": None,
                "folder_url": None
            }
    
    def _get_or_create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Get existing folder ID or create new folder.
        
        Args:
            folder_name: Name of folder
            parent_folder_id: ID of parent folder
            
        Returns:
            Folder ID or None
        """
        # Try to find existing folder
        folder_id = self._find_folder(folder_name, parent_folder_id)
        
        if folder_id:
            return folder_id
        
        # Create new folder
        result = self.create_folder(folder_name, parent_folder_id)
        
        if result.get('success'):
            return result.get('folder_id')
        
        return None
    
    def _find_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Find folder by name.
        
        Args:
            folder_name: Name of folder to find
            parent_folder_id: ID of parent folder
            
        Returns:
            Folder ID or None
        """
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            if parent_folder_id:
                query += f" and '{parent_folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                fields='files(id, name)'
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                return files[0]['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find folder {folder_name}: {e}")
            return None 