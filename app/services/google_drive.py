"""
Google Drive service for uploading processed videos.
Supports both Service Account and OAuth 2.0 authentication.
"""
import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import pickle

from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from app.config.settings import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']

# Target folder ID for all processed videos
TARGET_FOLDER_ID = "1q3DdrbnGRSAKL6Omiy6t0MghP4ZGtiTn"

def get_google_credentials() -> Optional[Any]:
    """
    Get Google OAuth credentials from file or from Base64 env var.
    Returns:
        google.oauth2.credentials.Credentials if found, else None.
    """
    creds = None

    # Сначала пробуем загрузить из файла
    token_path = "token.pickle"
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                logger.info("Loaded existing OAuth credentials from token.pickle")
        except Exception as e:
            logger.error(f"Failed to load OAuth token: {e}")
            return None

    # Если не получилось — пробуем из переменной окружения
    if not creds:
        token_base64 = os.getenv("GOOGLE_OAUTH_TOKEN_BASE64")
        if token_base64:
            try:
                token_data = base64.b64decode(token_base64)
                creds = pickle.loads(token_data)
                logger.info("Loaded OAuth credentials from Base64 environment variable")
            except Exception as e:
                logger.error(f"Failed to load OAuth token from Base64: {e}")

    # Check if credentials are valid
    if creds and creds.valid:
        return creds

    # Try to refresh if we have refresh token
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed credentials
            if os.path.exists(token_path):
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info("Refreshed OAuth credentials and saved to file")
            else:
                logger.info("Refreshed OAuth credentials (loaded from env var - manual update may be needed)")
            return creds
        except Exception as e:
            logger.error(f"Failed to refresh OAuth token: {e}")
            return None

    logger.info("No valid OAuth credentials found")
    return None

def get_service_account_credentials() -> Optional[service_account.Credentials]:
    """
    Get Service Account credentials from Base64 env var or from a file.
    
    Returns:
        google.oauth2.service_account.Credentials if found, else None.
    """
    creds_json_str = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    
    if creds_json_str:
        try:
            logger.info("Loading Google Service Account credentials from Base64 environment variable.")
            creds_json = base64.b64decode(creds_json_str).decode('utf-8')
            creds_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            return credentials
        except Exception as e:
            logger.error(f"Failed to load service account credentials from Base64 string: {e}")
            return None
    
    # Fallback to file
    creds_path = settings.google_credentials_path
    if os.path.exists(creds_path):
        try:
            logger.info(f"Loading Google Service Account credentials from file: {creds_path}")
            credentials = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
            return credentials
        except Exception as e:
            logger.error(f"Failed to load service account credentials from file {creds_path}: {e}")
            return None
            
    return None

def create_oauth_flow() -> Flow:
    """
    Create OAuth 2.0 flow for user authentication.
    
    Returns:
        Google OAuth Flow object
    """
    # You'll need to set these in environment variables
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set for OAuth authentication")
    
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost:8080/callback"]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES
    )
    flow.redirect_uri = "http://localhost:8080/callback"
    
    return flow

def get_oauth_authorization_url() -> str:
    """
    Get OAuth authorization URL for user authentication.
    
    Returns:
        Authorization URL string
    """
    try:
        flow = create_oauth_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')
        logger.info("Generated OAuth authorization URL")
        return auth_url
    except Exception as e:
        logger.error(f"Failed to create OAuth authorization URL: {e}")
        return ""

def handle_oauth_callback(authorization_code: str) -> bool:
    """
    Handle OAuth callback and save credentials.
    
    Args:
        authorization_code: The authorization code from the callback
        
    Returns:
        True if successful, False otherwise
    """
    try:
        flow = create_oauth_flow()
        flow.fetch_token(code=authorization_code)
        
        creds = flow.credentials
        
        # Save credentials
        with open("token.pickle", 'wb') as token:
            pickle.dump(creds, token)
        
        logger.info("Successfully saved OAuth credentials")
        return True
        
    except Exception as e:
        logger.error(f"Failed to handle OAuth callback: {e}")
        return False

class GoogleDriveService:
    """Service for uploading files to Google Drive."""
    
    def __init__(self):
        """Initialize Google Drive service."""
        self.credentials = get_google_credentials()
        self.auth_type = "none"
        
        if self.credentials:
            # Determine authentication type
            if isinstance(self.credentials, service_account.Credentials):
                self.auth_type = "service_account"
                logger.info("Using Service Account authentication")
            else:
                self.auth_type = "oauth"
                logger.info("Using OAuth 2.0 authentication")
            
            try:
                self.service = build('drive', 'v3', credentials=self.credentials)
                logger.info("Google Drive service initialized successfully.")
            except HttpError as e:
                logger.error(f"Failed to build Google Drive service: {e}")
                self.service = None
        else:
            logger.warning("Google Drive credentials not found, using mock service")
            self.service = None
    
    def is_oauth_authenticated(self) -> bool:
        """Check if OAuth authentication is active."""
        return self.auth_type == "oauth"
    
    def is_service_account_authenticated(self) -> bool:
        """Check if Service Account authentication is active."""
        return self.auth_type == "service_account"
    
    def get_authentication_info(self) -> Dict[str, Any]:
        """Get information about current authentication."""
        return {
            "authenticated": self.service is not None,
            "auth_type": self.auth_type,
            "oauth_url": get_oauth_authorization_url() if self.auth_type == "none" else None
        }
    
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
    
    def make_file_public(self, file_id: str) -> Dict[str, Any]:
        """Make a file publicly accessible and return direct download link."""
        if not self.service:
            logger.info(f"Mock making file public: {file_id}")
            return {
                "public": True,
                "direct_link": f"https://mock.direct.link/{file_id}",
                "view_link": f"https://mock.view.link/{file_id}"
            }
        
        try:
            # Create public permission
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            request = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id'
            )
            result = self._execute_request(request)
            
            if result:
                # Get file metadata to construct direct download link
                file_metadata = self.service.files().get(fileId=file_id, fields='id,name,webViewLink').execute()
                
                # Create direct download link
                direct_link = f"https://drive.google.com/uc?id={file_id}&export=download"
                view_link = file_metadata.get('webViewLink', '')
                
                logger.info(f"File {file_id} made public. Direct link: {direct_link}")
                return {
                    "public": True,
                    "direct_link": direct_link,
                    "view_link": view_link,
                    "file_name": file_metadata.get('name', '')
                }
            else:
                logger.error(f"Failed to make file {file_id} public")
                return {"public": False, "error": "Permission creation failed"}
                
        except Exception as e:
            logger.error(f"Error making file {file_id} public: {e}")
            return {"public": False, "error": str(e)}
    
    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload a single file to Google Drive and make it publicly accessible."""
        if not self.service:
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            logger.info(f"Mock upload: {os.path.basename(file_path)} ({file_size} bytes) to folder {folder_id or 'root'}")
            return {
                "id": f"mock_file_id_{os.path.basename(file_path)}",
                "name": os.path.basename(file_path),
                "webViewLink": "https://mock.drive.url/file/view",
                "directLink": f"https://mock.direct.link/{os.path.basename(file_path)}",
                "size": file_size,
                "public": True
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
            file_id = file.get('id')
            logger.info(f"File '{file.get('name')}' uploaded with ID: {file_id}")
            
            # Make file publicly accessible
            public_result = self.make_file_public(file_id)
            if public_result.get('public'):
                file['directLink'] = public_result.get('direct_link')
                file['public'] = True
                logger.info(f"File {file_id} made public with direct link: {public_result.get('direct_link')}")
            else:
                file['public'] = False
                logger.warning(f"Failed to make file {file_id} public: {public_result.get('error')}")
        
        return file
    
    def make_multiple_files_public(self, file_ids: List[str]) -> List[Dict[str, Any]]:
        """Make multiple files publicly accessible and return direct download links."""
        if not self.service:
            logger.info(f"Mock making {len(file_ids)} files public")
            results = []
            for file_id in file_ids:
                results.append({
                    "file_id": file_id,
                    "public": True,
                    "direct_link": f"https://mock.direct.link/{file_id}",
                    "view_link": f"https://mock.view.link/{file_id}"
                })
            return results
        
        results = []
        for file_id in file_ids:
            try:
                result = self.make_file_public(file_id)
                result["file_id"] = file_id
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to make file {file_id} public: {e}")
                results.append({
                    "file_id": file_id,
                    "public": False,
                    "error": str(e)
                })
        
        successful = [r for r in results if r.get("public")]
        failed = [r for r in results if not r.get("public")]
        
        logger.info(f"Made {len(successful)}/{len(file_ids)} files public. {len(failed)} failed.")
        return results
    
    def test_public_access(self, file_id: str) -> Dict[str, Any]:
        """Test if a file is publicly accessible."""
        import requests
        
        direct_link = f"https://drive.google.com/uc?id={file_id}&export=download"
        
        try:
            # Test with HEAD request to avoid downloading
            response = requests.head(direct_link, timeout=10, allow_redirects=True)
            
            is_accessible = response.status_code == 200
            
            return {
                "file_id": file_id,
                "accessible": is_accessible,
                "status_code": response.status_code,
                "direct_link": direct_link,
                "content_type": response.headers.get('content-type', ''),
                "content_length": response.headers.get('content-length', '0')
            }
            
        except Exception as e:
            logger.warning(f"Failed to test access for file {file_id}: {e}")
            return {
                "file_id": file_id,
                "accessible": False,
                "error": str(e),
                "direct_link": direct_link
            }
    
    def verify_target_folder_access(self) -> Dict[str, Any]:
        """Verify that the service account has access to the target folder."""
        if not self.service:
            logger.info(f"Mock verifying access to target folder: {TARGET_FOLDER_ID}")
            return {
                "accessible": True,
                "folder_id": TARGET_FOLDER_ID,
                "folder_name": "Mock Target Folder"
            }
        
        try:
            # Try to get folder metadata
            folder_metadata = self.service.files().get(
                fileId=TARGET_FOLDER_ID, 
                fields='id,name,mimeType,permissions'
            ).execute()
            
            folder_name = folder_metadata.get('name', 'Unknown')
            mime_type = folder_metadata.get('mimeType', '')
            
            is_folder = mime_type == 'application/vnd.google-apps.folder'
            
            logger.info(f"Target folder access verified: {folder_name} (ID: {TARGET_FOLDER_ID})")
            
            return {
                "accessible": True,
                "folder_id": TARGET_FOLDER_ID,
                "folder_name": folder_name,
                "is_folder": is_folder
            }
            
        except HttpError as e:
            error_code = e.resp.status
            error_message = str(e)
            
            logger.error(f"Cannot access target folder {TARGET_FOLDER_ID}: {error_message}")
            
            return {
                "accessible": False,
                "folder_id": TARGET_FOLDER_ID,
                "error_code": error_code,
                "error": error_message
            }
        except Exception as e:
            logger.error(f"Unexpected error verifying target folder access: {e}")
            return {
                "accessible": False,
                "folder_id": TARGET_FOLDER_ID,
                "error": str(e)
            }
    
    def upload_multiple_files(self, file_paths: List[str], task_id: str = None) -> List[Dict[str, Any]]:
        """Upload multiple files to the target folder (or user's Drive root for OAuth)."""
        if not self.service:
            results = []
            for file_path in file_paths:
                result = self.upload_file(file_path, TARGET_FOLDER_ID)
                results.append({
                    "success": True,
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "file_id": result.get('id'),
                    "file_url": result.get('webViewLink'),
                    "direct_url": result.get('directLink'),
                    "size_bytes": result.get('size', 0),
                    "public": True
                })
            return results

        # For OAuth, create a folder in user's Drive; for Service Account, use target folder
        if self.is_oauth_authenticated():
            # Create a folder for this task in user's Drive
            folder_name = f"VideoSlicerBot_{task_id or 'unknown'}"
            folder = self.create_folder(folder_name)
            target_folder_id = folder.get('id') if folder else None
            folder_name_display = folder.get('name', 'User Drive Root')
            logger.info(f"Created folder '{folder_name_display}' in user's Drive for task {task_id or 'unknown'}")
        else:
            # Service Account: verify access to target folder
            folder_access = self.verify_target_folder_access()
            if not folder_access.get('accessible'):
                error_msg = f"Cannot access target folder {TARGET_FOLDER_ID}: {folder_access.get('error', 'Unknown error')}"
                logger.error(error_msg)
                return [{
                    "success": False,
                    "file_path": file_path,
                    "error": error_msg
                } for file_path in file_paths]
            
            target_folder_id = TARGET_FOLDER_ID
            folder_name_display = folder_access.get('folder_name', 'Target Folder')

        logger.info(f"Uploading {len(file_paths)} files to '{folder_name_display}' (ID: {target_folder_id}) for task {task_id or 'unknown'}")

        upload_results = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                logger.warning(f"File not found, skipping upload: {file_path}")
                upload_results.append({
                    "success": False,
                    "file_path": file_path,
                    "error": "File not found"
                })
                continue
            
            result = self.upload_file(file_path, target_folder_id)
            if result and result.get('id'):
                upload_results.append({
                    "success": True,
                    "file_path": file_path,
                    "file_name": result.get('name'),
                    "file_id": result.get('id'),
                    "file_url": result.get('webViewLink'),
                    "direct_url": result.get('directLink'),
                    "size_bytes": int(result.get('size', 0)),
                    "public": result.get('public', False)
                })
                logger.info(f"Successfully uploaded and made public: {os.path.basename(file_path)}")
            else:
                upload_results.append({
                    "success": False,
                    "file_path": file_path,
                    "error": "Upload failed"
                })
                logger.error(f"Failed to upload: {file_path}")

        # Log summary
        successful_uploads = [r for r in upload_results if r.get("success")]
        failed_uploads = [r for r in upload_results if not r.get("success")]
        
        auth_info = " (OAuth - User's Drive)" if self.is_oauth_authenticated() else " (Service Account)"
        logger.info(f"Upload summary to '{folder_name_display}'{auth_info}: {len(successful_uploads)} successful, {len(failed_uploads)} failed")

        return upload_results 