"""
Deduplication Service for detecting duplicate content during import.

Supports duplicate detection across different platforms:
- YouTube videos (by URL and video ID)
- Vimeo videos (by URL and video ID)
- Local files (by file path and metadata)
- Fuzzy matching by title for similar content
"""
import re
from typing import List, Dict, Optional, Set, Tuple
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from src.models.playlist import PlaylistItem
from src.core.config import settings


class DeduplicationService:
    """Service for detecting duplicate content during import operations."""

    def __init__(self):
        """Initialize deduplication service."""
        # Platform-specific URL patterns
        self.youtube_patterns = [
            r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
            r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
            r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        ]
        self.vimeo_patterns = [
            r'https?://vimeo\.com/(\d+)',
            r'https?://player\.vimeo\.com/video/(\d+)',
        ]

    def extract_video_id(self, url: str, platform: str) -> Optional[str]:
        """Extract video ID from URL based on platform."""
        if not url:
            return None

        patterns = []
        if platform == 'youtube':
            patterns = self.youtube_patterns
        elif platform == 'vimeo':
            patterns = self.vimeo_patterns
        else:
            # For local files or other platforms, use the full path as ID
            return url

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def is_duplicate_url(
        self,
        db: Session,
        url: str,
        channel_id: Optional[str] = None,
        stream_id: Optional[str] = None,
        exclude_ids: Optional[Set[str]] = None
    ) -> bool:
        """
        Check if a URL already exists in the database.

        Args:
            db: Database session
            url: URL to check
            channel_id: Optional channel ID to scope the check
            stream_id: Optional stream ID to scope the check
            exclude_ids: Set of IDs to exclude from check (useful for updates)

        Returns:
            True if URL exists, False otherwise
        """
        try:
            query = db.query(PlaylistItem).filter(PlaylistItem.url == url)

            # Apply scope filters
            if channel_id:
                query = query.filter(PlaylistItem.channel_id == channel_id)
            if stream_id:
                query = query.filter(PlaylistItem.stream_id == stream_id)
            if exclude_ids:
                query = query.filter(PlaylistItem.id.notin_(exclude_ids))

            return query.first() is not None
        except Exception as e:
            # Log error but don't fail - treat as not duplicate
            print(f"Error checking duplicate URL: {e}")
            return False

    def is_duplicate_by_content_id(
        self,
        db: Session,
        content_id: str,
        platform: str,
        channel_id: Optional[str] = None,
        stream_id: Optional[str] = None,
        exclude_ids: Optional[Set[str]] = None
    ) -> bool:
        """
        Check if content with the same video ID exists (for YouTube/Vimeo).

        Args:
            db: Database session
            content_id: Platform-specific video ID
            platform: Platform type (youtube, vimeo, local)
            channel_id: Optional channel ID to scope the check
            stream_id: Optional stream ID to scope the check
            exclude_ids: Set of IDs to exclude from check

        Returns:
            True if content ID exists, False otherwise
        """
        if not content_id or platform == 'local':
            return False

        try:
            # Get all URLs and check if any contain the same content ID
            query = db.query(PlaylistItem).filter(
                PlaylistItem.type == platform
            )

            # Apply scope filters
            if channel_id:
                query = query.filter(PlaylistItem.channel_id == channel_id)
            if stream_id:
                query = query.filter(PlaylistItem.stream_id == stream_id)
            if exclude_ids:
                query = query.filter(PlaylistItem.id.notin_(exclude_ids))

            items = query.all()

            # Check if any URL contains the same content ID
            for item in items:
                item_content_id = self.extract_video_id(item.url, platform)
                if item_content_id == content_id:
                    return True

            return False
        except Exception as e:
            print(f"Error checking duplicate content ID: {e}")
            return False

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity ratio between two strings using SequenceMatcher.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        if not str1 or not str2:
            return 0.0

        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def find_similar_titles(
        self,
        db: Session,
        title: str,
        threshold: float = 0.85,
        channel_id: Optional[str] = None,
        stream_id: Optional[str] = None,
        exclude_ids: Optional[Set[str]] = None
    ) -> List[PlaylistItem]:
        """
        Find items with similar titles (fuzzy matching).

        Args:
            db: Database session
            title: Title to search for
            threshold: Minimum similarity ratio (0.0 to 1.0)
            channel_id: Optional channel ID to scope the search
            stream_id: Optional stream ID to scope the search
            exclude_ids: Set of IDs to exclude from search

        Returns:
            List of similar PlaylistItems
        """
        if not title:
            return []

        try:
            query = db.query(PlaylistItem).filter(
                PlaylistItem.title.isnot(None),
                PlaylistItem.title != ''
            )

            # Apply scope filters
            if channel_id:
                query = query.filter(PlaylistItem.channel_id == channel_id)
            if stream_id:
                query = query.filter(PlaylistItem.stream_id == stream_id)
            if exclude_ids:
                query = query.filter(PlaylistItem.id.notin_(exclude_ids))

            items = query.all()

            # Filter by similarity threshold
            similar_items = []
            for item in items:
                similarity = self.calculate_similarity(title, item.title)
                if similarity >= threshold:
                    similar_items.append(item)

            return similar_items
        except Exception as e:
            print(f"Error finding similar titles: {e}")
            return []

    def check_duplicates_batch(
        self,
        db: Session,
        items: List[Dict[str, any]],
        channel_id: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, any]], List[Dict[str, any]], Dict[str, any]]:
        """
        Check a batch of items for duplicates.

        Args:
            db: Database session
            items: List of items to check (each should have 'url', 'title', 'type')
            channel_id: Optional channel ID to scope the check
            stream_id: Optional stream ID to scope the check

        Returns:
            Tuple of (unique_items, duplicate_items, summary)
            - unique_items: Items that are not duplicates
            - duplicate_items: Items that are duplicates (with duplicate info)
            - summary: Statistics about duplicates found
        """
        unique_items = []
        duplicate_items = []
        seen_urls: Set[str] = set()

        # Track duplicate statistics
        summary = {
            'total': len(items),
            'unique': 0,
            'duplicates': 0,
            'by_url': 0,
            'by_content_id': 0,
            'by_title': 0
        }

        for item in items:
            url = item.get('url')
            title = item.get('title')
            item_type = item.get('type', 'youtube')

            if not url:
                continue

            # Skip if we've already seen this URL in the batch
            if url in seen_urls:
                duplicate_items.append({
                    **item,
                    'duplicate_reason': 'duplicate_in_batch',
                    'duplicate_details': 'Same URL appears multiple times in import list'
                })
                summary['duplicates'] += 1
                continue

            seen_urls.add(url)

            # Check for duplicate URL in database
            is_duplicate = False
            duplicate_info = {}

            if self.is_duplicate_url(db, url, channel_id, stream_id):
                is_duplicate = True
                duplicate_info = {
                    'duplicate_reason': 'duplicate_url',
                    'duplicate_details': f'URL already exists in database'
                }
                summary['by_url'] += 1
            else:
                # Check for duplicate content ID (for YouTube/Vimeo)
                content_id = self.extract_video_id(url, item_type)
                if content_id and self.is_duplicate_by_content_id(
                    db, content_id, item_type, channel_id, stream_id
                ):
                    is_duplicate = True
                    duplicate_info = {
                        'duplicate_reason': 'duplicate_content_id',
                        'duplicate_details': f'Same {item_type} video ID already exists'
                    }
                    summary['by_content_id'] += 1
                # Check for similar titles (only if title exists)
                elif title:
                    similar = self.find_similar_titles(
                        db, title, threshold=0.9, channel_id=channel_id, stream_id=stream_id
                    )
                    if similar:
                        is_duplicate = True
                        duplicate_info = {
                            'duplicate_reason': 'similar_title',
                            'duplicate_details': f'Similar title exists: {similar[0].title}',
                            'similar_items': [item.id for item in similar]
                        }
                        summary['by_title'] += 1

            if is_duplicate:
                duplicate_items.append({**item, **duplicate_info})
                summary['duplicates'] += 1
            else:
                unique_items.append(item)
                summary['unique'] += 1

        return unique_items, duplicate_items, summary

    def get_duplicate_stats(
        self,
        db: Session,
        channel_id: Optional[str] = None,
        stream_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get statistics about potential duplicates in a channel/stream.

        Args:
            db: Database session
            channel_id: Optional channel ID
            stream_id: Optional stream ID

        Returns:
            Dictionary with duplicate statistics
        """
        try:
            query = db.query(PlaylistItem)

            if channel_id:
                query = query.filter(PlaylistItem.channel_id == channel_id)
            if stream_id:
                query = query.filter(PlaylistItem.stream_id == stream_id)

            all_items = query.all()

            # Group URLs to find duplicates
            url_counts: Dict[str, int] = {}
            for item in all_items:
                url_counts[item.url] = url_counts.get(item.url, 0) + 1

            duplicate_urls = sum(1 for count in url_counts.values() if count > 1)
            total_duplicates = sum(count - 1 for count in url_counts.values() if count > 1)

            return {
                'total_items': len(all_items),
                'unique_items': len(url_counts),
                'duplicate_urls': duplicate_urls,
                'total_duplicates': total_duplicates
            }
        except Exception as e:
            print(f"Error getting duplicate stats: {e}")
            return {
                'total_items': 0,
                'unique_items': 0,
                'duplicate_urls': 0,
                'total_duplicates': 0
            }


# Singleton instance
deduplication_service = DeduplicationService()
