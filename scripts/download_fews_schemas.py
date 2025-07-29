"""
Download FEWS XSD schemas from remote directories.

This module provides functionality to download all XSD files from FEWS schema directories,
including nested directories, and organize them locally for offline use.
"""

from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FEWSSchemaDownloader:
    """
    Downloader for FEWS XSD schemas from remote directories.

    Downloads all XSD files from specified base URLs and their nested directories,
    preserving the directory structure locally.
    """

    def __init__(self, base_download_dir: str = "../data/fews_schemas"):
        """
        Initialize the schema downloader.

        Args:
            base_download_dir: Base directory where schemas will be downloaded
        """
        self.base_download_dir = Path(base_download_dir)
        self.base_download_dir.mkdir(parents=True, exist_ok=True)
        self.downloaded_files: Set[str] = set()
        self.session = requests.Session()
        # Set a reasonable timeout and user agent
        self.session.headers.update({"User-Agent": "FEWS-Schema-Downloader/1.0"})

    def _get_directory_listing(self, url: str) -> List[dict]:
        """
        Get directory listing from a URL.

        Args:
            url: URL to get directory listing from

        Returns:
            List of dictionaries with file/directory information
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = []

            # Look for links in the directory listing
            for link in soup.find_all("a"):
                href = link.get("href")
                if href and href != "../" and href != "./":
                    # Get the text content (filename/directory name)
                    name = link.get_text().strip()
                    if name:
                        # Determine if it's a directory or file
                        is_dir = href.endswith("/")
                        items.append(
                            {
                                "name": name,
                                "href": href,
                                "is_dir": is_dir,
                                "url": urljoin(url, href),
                            }
                        )

            return items

        except Exception as e:
            logger.error(f"Failed to get directory listing from {url}: {e}")
            return []

    def _download_file(self, url: str, local_path: Path) -> bool:
        """
        Download a single file from URL to local path.

        Args:
            url: URL to download from
            local_path: Local path to save the file

        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Create parent directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)

            response = self.session.get(url, timeout=60)
            response.raise_for_status()

            # Write the file
            with open(local_path, "wb") as f:
                f.write(response.content)

            logger.info(f"Downloaded: {local_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {url} to {local_path}: {e}")
            return False

    def _is_xsd_file(self, filename: str) -> bool:
        """
        Check if a filename is an XSD file.

        Args:
            filename: Name of the file to check

        Returns:
            True if it's an XSD file, False otherwise
        """
        return filename.lower().endswith(".xsd")

    def _get_relative_path(self, base_url: str, file_url: str) -> str:
        """
        Get relative path from base URL to file URL.

        Args:
            base_url: Base URL
            file_url: File URL

        Returns:
            Relative path string
        """
        base_parsed = urlparse(base_url)
        file_parsed = urlparse(file_url)

        # Remove the base path from the file path
        base_path = base_parsed.path.rstrip("/")
        file_path = file_parsed.path

        if file_path.startswith(base_path):
            relative_path = file_path[len(base_path) :].lstrip("/")
        else:
            relative_path = file_path.lstrip("/")

        return relative_path

    def download_directory(
        self, url: str, base_url: str, max_depth: int = 5, current_depth: int = 0
    ) -> int:
        """
        Recursively download all XSD files from a directory and its subdirectories.

        Args:
            url: URL of the directory to download from
            base_url: Base URL for calculating relative paths
            max_depth: Maximum recursion depth
            current_depth: Current recursion depth

        Returns:
            Number of files downloaded
        """
        if current_depth >= max_depth:
            logger.warning(f"Reached maximum depth {max_depth} at {url}")
            return 0

        logger.info(f"Scanning directory: {url} (depth {current_depth})")

        # Get directory listing
        items = self._get_directory_listing(url)
        if not items:
            logger.warning(f"No items found in directory: {url}")
            return 0

        downloaded_count = 0

        for item in items:
            item_url = item["url"]
            item_name = item["name"]

            if item["is_dir"]:
                # Recursively download subdirectory
                sub_count = self.download_directory(
                    item_url, base_url, max_depth, current_depth + 1
                )
                downloaded_count += sub_count
            elif self._is_xsd_file(item_name):
                # Download XSD file
                relative_path = self._get_relative_path(base_url, item_url)
                local_path = self.base_download_dir / relative_path

                # Skip if already downloaded
                if str(local_path) in self.downloaded_files:
                    logger.debug(f"Skipping already downloaded: {local_path}")
                    continue

                if self._download_file(item_url, local_path):
                    self.downloaded_files.add(str(local_path))
                    downloaded_count += 1

        return downloaded_count

    def download_fews_schemas(self, base_urls: List[str] = None) -> dict:
        """
        Download all FEWS schemas from the specified base URLs.

        Args:
            base_urls: List of base URLs to download from. If None, uses default FEWS URLs.

        Returns:
            Dictionary with download statistics
        """
        if base_urls is None:
            base_urls = [
                "https://fews.wldelft.nl/schemas/version1.0/",
                "https://fewsdocs.deltares.nl/schemas/version1.0/",
            ]

        total_downloaded = 0
        results = {}

        for base_url in base_urls:
            logger.info(f"Starting download from: {base_url}")

            try:
                # Create a subdirectory for each base URL
                url_parsed = urlparse(base_url)
                subdir_name = url_parsed.netloc.replace(".", "_")
                subdir = self.base_download_dir / subdir_name

                # Store original base directory
                original_base = self.base_download_dir

                # Set the base directory to the subdirectory for this URL
                self.base_download_dir = subdir

                downloaded_count = self.download_directory(base_url, base_url)
                total_downloaded += downloaded_count

                results[base_url] = {
                    "downloaded_count": downloaded_count,
                    "local_directory": str(subdir),
                }

                # Restore original base directory
                self.base_download_dir = original_base

                logger.info(f"Downloaded {downloaded_count} files from {base_url}")

            except Exception as e:
                logger.error(f"Failed to download from {base_url}: {e}")
                results[base_url] = {"downloaded_count": 0, "error": str(e)}

        return {
            "total_downloaded": total_downloaded,
            "base_download_dir": str(self.base_download_dir),
            "results": results,
        }

    def cleanup(self):
        """Clean up resources."""
        self.session.close()


def download_fews_schemas(
    base_urls: List[str] = None,
    download_dir: str = "../data/fews_schemas",
    max_depth: int = 5,
) -> dict:
    """
    Download all FEWS XSD schemas from remote directories.

    Args:
        base_urls: List of base URLs to download from. If None, uses default FEWS URLs.
        download_dir: Directory where schemas will be downloaded
        max_depth: Maximum recursion depth for subdirectories

    Returns:
        Dictionary with download statistics

    Example:
        from talk_with_fews.tools.validator.download_fews_schemas import download_fews_schemas

        # Download all schemas
        results = download_fews_schemas()

        # Download with custom options
        results = download_fews_schemas(
            base_urls=["https://fews.wldelft.nl/schemas/version1.0/"],
            download_dir="data/fews_schemas",
            max_depth=5
        )
    """
    downloader = FEWSSchemaDownloader(download_dir)

    try:
        results = downloader.download_fews_schemas(base_urls)
        logger.info(f"Download completed. Total files: {results['total_downloaded']}")
        return results
    finally:
        downloader.cleanup()


if __name__ == "__main__":
    # Example usage
    results = download_fews_schemas()
    print(f"Download completed: {results}")
