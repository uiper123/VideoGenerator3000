"""
Google Sheets service for logging processed videos data.
"""
import os
import json
import base64
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for logging data to Google Sheets."""
    
    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        """
        Initialize Google Sheets service.
        
        Args:
            credentials_path: Path to Google credentials JSON file
            spreadsheet_id: ID of the Google Spreadsheet
        """
        self.credentials_path = credentials_path or "google-credentials.json"
        self.spreadsheet_id = spreadsheet_id or os.getenv('GOOGLE_SHEETS_ID')
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets API service."""
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
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                
                logger.info("Google Sheets credentials loaded from environment variable")
                
            elif os.path.exists(self.credentials_path):
                # Load from file
                credentials = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                
                logger.info(f"Google Sheets credentials loaded from file: {self.credentials_path}")
                
            else:
                logger.warning("Google Sheets credentials not found, using mock service")
                self.service = "mock_service"
                return
            
            # Build the Sheets service
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            logger.info("Falling back to mock service")
            self.service = "mock_service"
    
    def log_video_processing(
        self,
        task_id: str,
        user_id: int,
        video_title: str,
        source_url: str,
        fragments_count: int,
        total_duration: float,
        settings: Dict[str, Any],
        drive_links: List[str]
    ) -> Dict[str, Any]:
        """
        Log video processing data to Google Sheets.
        
        Args:
            task_id: Task ID
            user_id: User ID
            video_title: Original video title
            source_url: Source URL
            fragments_count: Number of fragments created
            total_duration: Total duration in seconds
            settings: Processing settings
            drive_links: List of Google Drive links
            
        Returns:
            Dict with logging results
        """
        # Prepare data row
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duration_minutes = round(total_duration / 60, 2)
        
        # Create clickable hyperlinks for video files
        video_links = []
        max_links = 10  # Максимум 10 ссылок на видео
        
        for i in range(max_links):
            if i < len(drive_links) and drive_links[i]:
                # Экранируем кавычки в ссылках для безопасности
                safe_link = drive_links[i].replace('"', '""')
                fragment_name = f"Фрагмент {i+1}"
                hyperlink_formula = f'=HYPERLINK("{safe_link}","{fragment_name}")'
                video_links.append(hyperlink_formula)
            else:
                video_links.append("")  # Пустая ячейка для неиспользуемых столбцов
        
        # Prepare source URL hyperlink
        safe_source_url = source_url.replace('"', '""') if source_url else ""
        source_hyperlink = f'=HYPERLINK("{safe_source_url}","🔗 Исходное видео")'
        
        row_data = [
            timestamp,                                    # A: Дата/время
            task_id,                                     # B: ID задачи
            user_id,                                     # C: ID пользователя
            video_title,                                 # D: Название видео
            source_hyperlink,                            # E: Исходная ссылка (кликабельная)
            fragments_count,                             # F: Количество фрагментов
            duration_minutes,                            # G: Длительность (мин)
            settings.get('quality', '1080p'),            # H: Качество
            settings.get('fragment_duration', 30),       # I: Длительность фрагмента (сек)
            settings.get('title', ''),                   # J: Заголовок
            'Да' if settings.get('enable_subtitles', True) else 'Нет',  # K: Субтитры
            # L-U: Кликабельные ссылки на фрагменты видео (10 столбцов)
        ] + video_links
        
        if self.service == "mock_service":
            # Fallback to mock behavior
            logger.info(f"Mock Google Sheets log: {row_data}")
            
            return {
                "success": True,
                "row_data": row_data,
                "spreadsheet_id": self.spreadsheet_id,
                "range": f"Sheet1!A:U"  # Обновленный диапазон для 21 столбца
            }
        
        if not self.service:
            logger.warning("Google Sheets service not available, skipping logging")
            return {
                "success": False,
                "error": "Google Sheets service not initialized"
            }
        
        if not self.spreadsheet_id:
            logger.warning("Google Sheets ID not provided, skipping logging")
            return {
                "success": False,
                "error": "Google Sheets ID not provided"
            }
        
        try:
            # Ensure headers exist
            self._ensure_headers()
            
            # Append the row
            range_name = 'Sheet1!A:U'  # Обновленный диапазон для 21 столбца
            
            body = {
                'values': [row_data]
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # Позволяет использовать формулы HYPERLINK
                body=body
            ).execute()
            
            logger.info(f"Successfully logged to Google Sheets: {task_id}")
            
            return {
                "success": True,
                "row_data": row_data,
                "spreadsheet_id": self.spreadsheet_id,
                "range": range_name,
                "updated_rows": result.get('updates', {}).get('updatedRows', 0)
            }
            
        except HttpError as e:
            logger.error(f"Google Sheets API error: {e}")
            return {
                "success": False,
                "error": f"Google Sheets API error: {e}"
            }
        except Exception as e:
            logger.error(f"Failed to log to Google Sheets: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create_headers(self) -> Dict[str, Any]:
        """
        Create headers row in Google Sheets.
        
        Returns:
            Dict with operation results
        """
        # Основные заголовки
        main_headers = [
            "📅 Дата/время",
            "🔷 ID задачи", 
            "👤 ID пользователя",
            "🎬 Название видео",
            "🔗 Исходная ссылка",
            "📊 Количество фрагментов",
            "⏱️ Длительность (мин)",
            "🎯 Качество",
            "⏰ Длительность фрагмента (сек)",
            "📝 Заголовок",
            "💬 Субтитры"
        ]
        
        # Заголовки для ссылок на фрагменты видео
        video_headers = [f"📺 Фрагмент {i+1}" for i in range(10)]
        
        # Объединяем все заголовки
        headers = main_headers + video_headers
        
        if self.service == "mock_service":
            # Fallback to mock behavior
            logger.info(f"Mock headers creation: {headers}")
            
            return {
                "success": True,
                "headers": headers
            }
        
        if not self.service:
            logger.warning("Google Sheets service not available, skipping header creation")
            return {
                "success": False,
                "error": "Google Sheets service not initialized"
            }
        
        if not self.spreadsheet_id:
            logger.warning("Google Sheets ID not provided, skipping header creation")
            return {
                "success": False,
                "error": "Google Sheets ID not provided"
            }
        
        try:
            # Check if headers already exist
            range_name = 'Sheet1!A1:U1'  # Обновленный диапазон для 21 столбца
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if values and len(values[0]) >= len(headers):
                logger.info("Headers already exist in Google Sheets")
                return {
                    "success": True,
                    "headers": headers,
                    "already_exists": True
                }
            
            # Create headers
            body = {
                'values': [headers]
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',  # Позволяет использовать формулы и эмодзи
                body=body
            ).execute()
            
            logger.info("Headers created in Google Sheets")
            
            # Apply formatting to headers
            self._format_headers()
            
            return {
                "success": True,
                "headers": headers,
                "updated_cells": result.get('updatedCells', 0)
            }
            
        except HttpError as e:
            logger.error(f"Google Sheets API error creating headers: {e}")
            return {
                "success": False,
                "error": f"Google Sheets API error: {e}"
            }
        except Exception as e:
            logger.error(f"Failed to create headers: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_processing_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get processing statistics from Google Sheets.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with statistics
        """
        if self.service == "mock_service":
            # Fallback to mock behavior
            mock_stats = {
                "total_videos": 0,
                "total_fragments": 0,
                "total_duration_hours": 0,
                "average_fragments_per_video": 0,
                "most_popular_quality": "1080p",
                "users_count": 0
            }
            
            logger.info(f"Mock stats retrieval for {days} days: {mock_stats}")
            
            return {
                "success": True,
                "stats": mock_stats,
                "period_days": days
            }
        
        if not self.service:
            logger.warning("Google Sheets service not available, skipping stats")
            return {
                "success": False,
                "error": "Google Sheets service not initialized"
            }
        
        if not self.spreadsheet_id:
            logger.warning("Google Sheets ID not provided, skipping stats")
            return {
                "success": False,
                "error": "Google Sheets ID not provided"
            }
        
        try:
            # Get all data from the sheet
            range_name = 'Sheet1!A:U'  # Обновленный диапазон для 21 столбца
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values or len(values) <= 1:  # Only headers or empty
                return {
                    "success": True,
                    "stats": {
                        "total_videos": 0,
                        "total_fragments": 0,
                        "total_duration_hours": 0,
                        "average_fragments_per_video": 0,
                        "most_popular_quality": "1080p",
                        "users_count": 0
                    },
                    "period_days": days
                }
            
            # Calculate statistics
            data_rows = values[1:]  # Skip headers
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            
            total_videos = 0
            total_fragments = 0
            total_duration = 0
            quality_counts = {}
            unique_users = set()
            
            for row in data_rows:
                if len(row) < 6:  # Not enough data
                    continue
                
                try:
                    # Parse date
                    date_str = row[0]
                    row_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    
                    if row_date.timestamp() < cutoff_date:
                        continue  # Too old
                    
                    # Count videos and fragments
                    total_videos += 1
                    fragments = int(row[5]) if len(row) > 5 and row[5].isdigit() else 0
                    total_fragments += fragments
                    
                    # Duration
                    duration = float(row[6]) if len(row) > 6 and row[6].replace('.', '').isdigit() else 0
                    total_duration += duration
                    
                    # Quality
                    quality = row[7] if len(row) > 7 else "1080p"
                    quality_counts[quality] = quality_counts.get(quality, 0) + 1
                    
                    # Users
                    user_id = row[2] if len(row) > 2 else ""
                    if user_id.isdigit():
                        unique_users.add(int(user_id))
                
                except (ValueError, IndexError) as e:
                    logger.warning(f"Error parsing row: {row}, error: {e}")
                    continue
            
            # Calculate averages
            avg_fragments = total_fragments / total_videos if total_videos > 0 else 0
            most_popular_quality = max(quality_counts, key=quality_counts.get) if quality_counts else "1080p"
            
            stats = {
                "total_videos": total_videos,
                "total_fragments": total_fragments,
                "total_duration_hours": round(total_duration / 60, 2),
                "average_fragments_per_video": round(avg_fragments, 1),
                "most_popular_quality": most_popular_quality,
                "users_count": len(unique_users)
            }
            
            logger.info(f"Statistics calculated for {days} days: {stats}")
            
            return {
                "success": True,
                "stats": stats,
                "period_days": days
            }
            
        except HttpError as e:
            logger.error(f"Google Sheets API error getting stats: {e}")
            return {
                "success": False,
                "error": f"Google Sheets API error: {e}"
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _ensure_headers(self):
        """Ensure headers exist in the spreadsheet."""
        try:
            # Check if headers exist
            range_name = 'Sheet1!A1:U1'  # Обновленный диапазон для 21 столбца
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values or len(values[0]) < 21:
                # Headers don't exist or incomplete, create them
                self.create_headers()
                
        except Exception as e:
            logger.warning(f"Failed to ensure headers: {e}")
            # Try to create headers anyway
            self.create_headers()
    
    def _format_headers(self):
        """Apply beautiful formatting to headers."""
        if self.service == "mock_service" or not self.service or not self.spreadsheet_id:
            return
        
        try:
            # Freeze first row
            freeze_request = {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "gridProperties": {
                            "frozenRowCount": 1
                        }
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            }
            
            # Format headers (bold, colored background, center alignment)
            format_request = {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 21  # 21 столбца A-U
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.2,
                                "green": 0.6,
                                "blue": 0.9
                            },
                            "textFormat": {
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0
                                },
                                "fontSize": 11,
                                "bold": True
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE"
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)"
                }
            }
            
            # Auto-resize columns
            auto_resize_request = {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": 0,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": 21  # 21 столбца
                    }
                }
            }
            
            # Execute all formatting requests
            requests = [freeze_request, format_request, auto_resize_request]
            
            body = {
                "requests": requests
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body=body
            ).execute()
            
            logger.info("Headers formatted successfully")
            
        except Exception as e:
            logger.warning(f"Failed to format headers: {e}") 