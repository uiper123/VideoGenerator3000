#!/usr/bin/env python3
"""
Google Drive Token Checker - проверяет работоспособность токена Google Drive
"""
import os
import pickle
import logging
from pathlib import Path
from datetime import datetime

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

logger = logging.getLogger(__name__)

class GoogleDriveChecker:
    """Класс для проверки Google Drive токена и подключения"""
    
    def __init__(self, token_path: str = "token.pickle", credentials_path: str = "google-credentials.json"):
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.scopes = ['https://www.googleapis.com/auth/drive']
        
    def check_libraries(self) -> dict:
        """Проверяет наличие необходимых библиотек"""
        result = {
            'status': 'success' if GOOGLE_LIBS_AVAILABLE else 'error',
            'message': 'Google libraries available' if GOOGLE_LIBS_AVAILABLE else 'Google libraries not installed',
            'libraries': GOOGLE_LIBS_AVAILABLE
        }
        
        if not GOOGLE_LIBS_AVAILABLE:
            result['fix'] = 'pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'
        
        return result
    
    def check_credentials_file(self) -> dict:
        """Проверяет наличие файла credentials"""
        if not os.path.exists(self.credentials_path):
            return {
                'status': 'error',
                'message': f'Credentials file not found: {self.credentials_path}',
                'fix': 'Download credentials.json from Google Cloud Console'
            }
        
        try:
            with open(self.credentials_path, 'r') as f:
                import json
                creds_data = json.load(f)
                
            if 'installed' in creds_data or 'web' in creds_data:
                return {
                    'status': 'success',
                    'message': f'Credentials file found and valid: {self.credentials_path}',
                    'type': 'installed' if 'installed' in creds_data else 'web'
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Invalid credentials file format',
                    'fix': 'Re-download credentials.json from Google Cloud Console'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error reading credentials file: {e}',
                'fix': 'Check credentials.json file format'
            }
    
    def check_token_file(self) -> dict:
        """Проверяет наличие и валидность токена"""
        if not os.path.exists(self.token_path):
            return {
                'status': 'warning',
                'message': f'Token file not found: {self.token_path}',
                'fix': 'Run OAuth flow to generate token'
            }
        
        try:
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
            
            # Проверяем базовые свойства токена
            token_info = {
                'status': 'success',
                'message': f'Token file found: {self.token_path}',
                'valid': creds.valid if hasattr(creds, 'valid') else False,
                'expired': creds.expired if hasattr(creds, 'expired') else True,
                'token_uri': getattr(creds, 'token_uri', 'N/A'),
                'scopes': getattr(creds, 'scopes', [])
            }
            
            if hasattr(creds, 'expiry') and creds.expiry:
                token_info['expiry'] = creds.expiry.isoformat()
                token_info['expires_in_hours'] = (creds.expiry - datetime.utcnow()).total_seconds() / 3600
            
            return token_info
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error reading token file: {e}',
                'fix': 'Delete token.pickle and re-run OAuth flow'
            }
    
    def test_drive_connection(self) -> dict:
        """Тестирует подключение к Google Drive"""
        if not GOOGLE_LIBS_AVAILABLE:
            return {
                'status': 'error',
                'message': 'Google libraries not available',
                'fix': 'Install required libraries first'
            }
        
        try:
            # Загружаем токен
            creds = None
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # Если токена нет или он недействителен, пытаемся обновить
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                else:
                    return {
                        'status': 'error',
                        'message': 'No valid credentials available',
                        'fix': 'Run OAuth flow to get new token'
                    }
            
            # Тестируем подключение
            service = build('drive', 'v3', credentials=creds)
            
            # Простой запрос для проверки подключения
            results = service.files().list(pageSize=1, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            # Получаем информацию о пользователе
            about = service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            
            return {
                'status': 'success',
                'message': 'Google Drive connection successful',
                'user_email': user_info.get('emailAddress', 'N/A'),
                'user_name': user_info.get('displayName', 'N/A'),
                'files_accessible': len(files) > 0,
                'test_time': datetime.now().isoformat()
            }
            
        except HttpError as e:
            return {
                'status': 'error',
                'message': f'Google Drive API error: {e}',
                'error_code': getattr(e, 'resp', {}).get('status', 'unknown'),
                'fix': 'Check API permissions and quotas'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Connection test failed: {e}',
                'fix': 'Check credentials and network connection'
            }
    
    def full_check(self) -> dict:
        """Выполняет полную проверку Google Drive интеграции"""
        logger.info("🔍 Starting full Google Drive check...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'libraries': self.check_libraries(),
            'credentials_file': self.check_credentials_file(),
            'token_file': self.check_token_file(),
            'drive_connection': None,
            'overall_status': 'unknown'
        }
        
        # Тестируем подключение только если предыдущие проверки прошли
        if (results['libraries']['status'] == 'success' and 
            results['credentials_file']['status'] == 'success'):
            results['drive_connection'] = self.test_drive_connection()
        else:
            results['drive_connection'] = {
                'status': 'skipped',
                'message': 'Skipped due to previous errors'
            }
        
        # Определяем общий статус
        if results['drive_connection']['status'] == 'success':
            results['overall_status'] = 'success'
        elif any(r['status'] == 'error' for r in results.values() if isinstance(r, dict)):
            results['overall_status'] = 'error'
        else:
            results['overall_status'] = 'warning'
        
        return results
    
    def format_check_results(self, results: dict) -> str:
        """Форматирует результаты проверки для вывода"""
        output = []
        output.append("🔍 Google Drive Integration Check")
        output.append("=" * 40)
        
        # Библиотеки
        lib_status = "✅" if results['libraries']['status'] == 'success' else "❌"
        output.append(f"{lib_status} Libraries: {results['libraries']['message']}")
        if 'fix' in results['libraries']:
            output.append(f"   Fix: {results['libraries']['fix']}")
        
        # Файл credentials
        cred_status = "✅" if results['credentials_file']['status'] == 'success' else "❌"
        output.append(f"{cred_status} Credentials: {results['credentials_file']['message']}")
        if 'fix' in results['credentials_file']:
            output.append(f"   Fix: {results['credentials_file']['fix']}")
        
        # Токен
        token_status = "✅" if results['token_file']['status'] == 'success' else ("⚠️" if results['token_file']['status'] == 'warning' else "❌")
        output.append(f"{token_status} Token: {results['token_file']['message']}")
        if 'valid' in results['token_file']:
            output.append(f"   Valid: {results['token_file']['valid']}")
            output.append(f"   Expired: {results['token_file']['expired']}")
        if 'expires_in_hours' in results['token_file']:
            hours = results['token_file']['expires_in_hours']
            if hours > 0:
                output.append(f"   Expires in: {hours:.1f} hours")
            else:
                output.append(f"   Expired {abs(hours):.1f} hours ago")
        
        # Подключение к Drive
        if results['drive_connection']['status'] != 'skipped':
            drive_status = "✅" if results['drive_connection']['status'] == 'success' else "❌"
            output.append(f"{drive_status} Drive Connection: {results['drive_connection']['message']}")
            if 'user_email' in results['drive_connection']:
                output.append(f"   User: {results['drive_connection']['user_email']}")
            if 'fix' in results['drive_connection']:
                output.append(f"   Fix: {results['drive_connection']['fix']}")
        
        # Общий статус
        overall_emoji = {"success": "✅", "warning": "⚠️", "error": "❌"}.get(results['overall_status'], "❓")
        output.append(f"\n{overall_emoji} Overall Status: {results['overall_status'].upper()}")
        
        return "\n".join(output)

def main():
    """Основная функция для тестирования"""
    checker = GoogleDriveChecker()
    results = checker.full_check()
    print(checker.format_check_results(results))
    
    return results['overall_status'] == 'success'

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)