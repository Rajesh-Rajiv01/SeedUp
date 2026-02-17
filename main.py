#!/usr/bin/env python3
"""
SeedUp - Smart Torrent Management Tool
Main entry point for torrent downloader with Google Drive upload (Colab-optimized).
"""

import sys
import argparse
import os
from pathlib import Path

from torrent_downloader import download_torrent, get_download_status, clear_session
from config import ConfigManager, TORRENT_DOWNLOAD_PATH, get_logger

logger = get_logger(__name__)


# ==========================================================
# Google Drive Mount Helper (SAFE VERSION)
# ==========================================================
def ensure_drive_mounted():
    """Mount Google Drive if running inside Google Colab."""
    try:
        import google.colab
        from google.colab import drive

        # Only mount if not already mounted
        if not os.path.exists("/content/drive/MyDrive"):
            print("Mounting Google Drive...")
            drive.mount('/content/drive')

    except ImportError:
        # Not running inside Colab
        pass


# ==========================================================
# Dynamic uploader import
# ==========================================================
def get_uploader():
    """Import and return uploader module."""
    try:
        from gdrive_uploader import upload_to_google_drive
        return upload_to_google_drive
    except ImportError as e:
        logger.error(f"Failed to import uploader: {str(e)}")
        print("\n" + "="*60)
        print("ERROR: Failed to import Google Drive uploader")
        print("="*60)
        print("Please install required packages:")
        print("  pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        print("="*60)
        raise


# ==========================================================
# Argument Parsing
# ==========================================================
def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Download torrents and upload to Google Drive (Colab-optimized)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Download
    download_parser = subparsers.add_parser('download', help='Download a torrent')
    download_parser.add_argument('-t', '--torrent', type=str, required=True)
    download_parser.add_argument(
        '-d', '--destination',
        type=str,
        default=TORRENT_DOWNLOAD_PATH
    )
    download_parser.add_argument('--no-resume', action='store_true')
    download_parser.add_argument('--upload', action='store_true')
    download_parser.add_argument('-f', '--folder-id', type=str)
    download_parser.add_argument('--no-skip', action='store_true')

    # Upload
    upload_parser = subparsers.add_parser('upload', help='Upload files to Google Drive')
    upload_parser.add_argument('-p', '--path', type=str, required=True)
    upload_parser.add_argument('-f', '--folder-id', type=str, required=True)
    upload_parser.add_argument('--no-skip', action='store_true')

    # Status
    subparsers.add_parser('status')

    # Clear
    subparsers.add_parser('clear')

    return parser.parse_args()


# ==========================================================
# Download Handler
# ==========================================================
def handle_download(args):
    print("="*60)
    print("TORRENT DOWNLOADER")
    print("="*60)

    # Mount Drive if destination is inside Drive
    if args.destination.startswith("/content/drive"):
        ensure_drive_mounted()

    if args.upload and not args.folder_id:
        logger.error("--folder-id is required when using --upload")
        return 1

    logger.info(f"Starting download: {args.torrent}")

    downloaded_path = download_torrent(
        args.torrent,
        download_path=args.destination,
        auto_resume=not args.no_resume
    )

    if not downloaded_path:
        logger.error("Download failed or cancelled")
        return 1

    logger.info(f"Download completed: {downloaded_path}")

    # Upload if requested
    if args.upload:
        ensure_drive_mounted()

        print("\n" + "="*60)
        print("UPLOADING TO GOOGLE DRIVE")
        print("="*60)

        try:
            upload_to_google_drive = get_uploader()

            results = upload_to_google_drive(
                downloaded_path,
                args.folder_id,
                skip_existing=not args.no_skip
            )

            if results.get('failed'):
                logger.warning(f"Some files failed ({len(results['failed'])})")
                return 1

            logger.info("Upload completed successfully!")

        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return 1

    return 0


# ==========================================================
# Upload Handler
# ==========================================================
def handle_upload(args):
    print("="*60)
    print("GOOGLE DRIVE UPLOADER")
    print("="*60)

    ensure_drive_mounted()

    if not os.path.exists(args.path):
        logger.error(f"Path does not exist: {args.path}")
        return 1

    try:
        upload_to_google_drive = get_uploader()

        results = upload_to_google_drive(
            args.path,
            args.folder_id,
            skip_existing=not args.no_skip
        )

        if results.get('failed'):
            logger.warning(f"Some files failed ({len(results['failed'])})")
            return 1

        logger.info("Upload completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return 1


# ==========================================================
# Status Handler
# ==========================================================
def handle_status(args):
    if get_download_status():
        print("✓ Found paused download session")
    else:
        print("✗ No paused download session found")
    return 0


# ==========================================================
# Clear Handler
# ==========================================================
def handle_clear(args):
    if clear_session():
        print("✓ Download session cleared")
        return 0
    else:
        print("✗ Failed to clear session")
        return 1


# ==========================================================
# Main
# ==========================================================
def main():
    args = parse_arguments()

    if not args.command:
        print("Error: No command specified\n")
        return 1

    try:
        if args.command == 'download':
            return handle_download(args)
        elif args.command == 'upload':
            return handle_upload(args)
        elif args.command == 'status':
            return handle_status(args)
        elif args.command == 'clear':
            return handle_clear(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
