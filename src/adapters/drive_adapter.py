"""Adapter for uploading meeting minutes and searching docs in Google Drive.

Uses Google Drive API with service account authentication to
upload meeting minutes files and search for project documents.
"""

import asyncio
import os
import time
from datetime import datetime
from io import BytesIO

import structlog
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from src.adapters.base import WriteResult

logger = structlog.get_logger()

# Required scopes for Drive file uploads
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class DriveAdapter:
    """Adapter for uploading meeting minutes to Google Drive.

    Uploads files to a specified folder using Google Drive API.
    Follows the established adapter pattern with lazy service initialization.
    """

    def __init__(self, credentials_path: str | None = None):
        """Initialize with service account credentials.

        Args:
            credentials_path: Path to service account JSON.
                             Falls back to GOOGLE_DRIVE_CREDENTIALS, then
                             GOOGLE_SHEETS_CREDENTIALS env vars.
        """
        self._credentials_path = (
            credentials_path
            or os.environ.get("GOOGLE_DRIVE_CREDENTIALS")
            or os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
        )
        self._service = None

    def _get_service(self):
        """Get or create Drive API service.

        Returns:
            Google Drive API service instance

        Raises:
            ValueError: If no credentials path configured
        """
        if self._service is None:
            if not self._credentials_path:
                raise ValueError(
                    "No credentials. Set GOOGLE_DRIVE_CREDENTIALS env var "
                    "or pass credentials_path to constructor."
                )
            creds = Credentials.from_service_account_file(
                self._credentials_path,
                scopes=DRIVE_SCOPES,
            )
            self._service = build("drive", "v3", credentials=creds)
        return self._service

    async def upload_minutes(
        self,
        content: str,
        filename: str,
        folder_id: str,
        mime_type: str = "text/markdown",
        *,
        dry_run: bool = False,
    ) -> WriteResult:
        """Upload meeting minutes to Google Drive.

        Args:
            content: File content (markdown or HTML)
            filename: Name for the uploaded file
            folder_id: Google Drive folder ID to upload to
            mime_type: MIME type (text/markdown or text/html)
            dry_run: If True, log and return without uploading

        Returns:
            WriteResult with file ID and web view link
        """
        if dry_run:
            logger.info(
                "dry_run: would upload minutes",
                filename=filename,
                folder_id=folder_id,
                mime_type=mime_type,
                content_length=len(content),
            )
            return WriteResult(
                success=True,
                dry_run=True,
                item_count=1,
            )

        # Use asyncio.to_thread for non-blocking I/O
        return await asyncio.to_thread(
            self._upload_sync, content, filename, folder_id, mime_type
        )

    def _upload_sync(
        self,
        content: str,
        filename: str,
        folder_id: str,
        mime_type: str,
    ) -> WriteResult:
        """Synchronous upload implementation.

        Args:
            content: File content
            filename: File name
            folder_id: Destination folder ID
            mime_type: MIME type

        Returns:
            WriteResult with file ID and URL
        """
        start_time = time.monotonic()

        try:
            service = self._get_service()

            # Prepare file metadata
            file_metadata = {
                "name": filename,
                "parents": [folder_id],
            }

            # Create media upload from content
            media = MediaIoBaseUpload(
                BytesIO(content.encode("utf-8")),
                mimetype=mime_type,
                resumable=False,
            )

            # Upload file and get ID + webViewLink
            file = (
                service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id,webViewLink",
                )
                .execute()
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "uploaded minutes to Drive",
                filename=filename,
                folder_id=folder_id,
                file_id=file.get("id"),
                duration_ms=duration_ms,
            )

            return WriteResult(
                success=True,
                dry_run=False,
                item_count=1,
                external_id=file.get("id"),
                url=file.get("webViewLink"),
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(
                "failed to upload minutes",
                filename=filename,
                folder_id=folder_id,
                error=str(e),
                duration_ms=duration_ms,
            )
            return WriteResult(
                success=False,
                dry_run=False,
                item_count=0,
                error_message=str(e),
                duration_ms=duration_ms,
            )

    async def health_check(self) -> bool:
        """Check if adapter is properly configured.

        Returns:
            True if credentials can authenticate, False otherwise
        """
        try:
            self._get_service()
            return True
        except Exception:
            return False

    async def search_project_docs(
        self,
        folder_id: str,
        query_terms: list[str] | None = None,
        max_results: int = 10,
        modified_after: datetime | None = None,
    ) -> list[dict]:
        """Search for project documents in a folder.

        Args:
            folder_id: Google Drive folder ID to search in
            query_terms: Optional search terms for name or content
            max_results: Maximum documents to return (default 10)
            modified_after: Optional filter for recently modified docs

        Returns:
            List of document dicts with id, name, webViewLink,
            modifiedTime, mimeType. Ordered by modifiedTime desc.
        """
        return await asyncio.to_thread(
            self._search_docs_sync,
            folder_id,
            query_terms,
            max_results,
            modified_after,
        )

    def _search_docs_sync(
        self,
        folder_id: str,
        query_terms: list[str] | None,
        max_results: int,
        modified_after: datetime | None,
    ) -> list[dict]:
        """Synchronous document search implementation."""
        try:
            service = self._get_service()

            # Build query: start with folder scope
            query_parts = [f"'{folder_id}' in parents", "trashed = false"]

            # Add search terms if provided
            if query_terms:
                term_conditions = []
                for term in query_terms:
                    escaped_term = term.replace("'", "\\'")
                    term_conditions.append(
                        f"(name contains '{escaped_term}' or "
                        f"fullText contains '{escaped_term}')"
                    )
                if term_conditions:
                    query_parts.append(f"({' or '.join(term_conditions)})")

            # Add modified date filter if provided
            if modified_after:
                iso_date = modified_after.strftime("%Y-%m-%dT%H:%M:%S")
                query_parts.append(f"modifiedTime > '{iso_date}'")

            query = " and ".join(query_parts)

            result = (
                service.files()
                .list(
                    q=query,
                    pageSize=max_results,
                    fields="files(id,name,webViewLink,modifiedTime,mimeType)",
                    orderBy="modifiedTime desc",
                )
                .execute()
            )

            files = result.get("files", [])

            logger.debug(
                "searched project docs",
                folder_id=folder_id,
                query_terms=query_terms,
                found_count=len(files),
            )

            return [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "webViewLink": f.get("webViewLink"),
                    "modifiedTime": f.get("modifiedTime"),
                    "mimeType": f.get("mimeType"),
                }
                for f in files
            ]

        except Exception as e:
            logger.warning(
                "Error searching project docs",
                folder_id=folder_id,
                error=str(e),
            )
            return []
