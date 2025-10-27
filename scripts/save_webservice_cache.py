#!/usr/bin/env python3
"""
Script to save webservice cache databases to disk for debugging and investigation.

This script will:
1. Set up the environment to enable database saving
2. Trigger webservice ingestion for each configured endpoint
3. Save the in-memory DuckDB databases to files

Usage:
    python scripts/save_webservice_cache.py [service_name]

If no service name is provided, it will process all available services.
"""

import os
import sys
from pathlib import Path

# Add src and tests to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "tests"))

from talk_with_fews.routers.setup_connections import get_runtime_ctx  # noqa: E402
from test_config import FEWS_SERVICES  # noqa: E402


def save_cache_for_service(service_name: str):
    """Save cache for a specific service."""
    print(f"\n{'=' * 60}")
    print(f"Processing service: {service_name.upper()}")
    print(f"{'=' * 60}")

    if service_name not in FEWS_SERVICES:
        print(
            f"❌ Error: Service '{service_name}' not found in available services: {list(FEWS_SERVICES.keys())}"
        )
        return False

    # Set environment variables for this run
    os.environ["DEV_SAVE_WEBSERVICE_CACHE"] = "true"
    os.environ["DEV_DISABLE_WEBSERVICE_INGEST"] = "false"  # Ensure ingestion is enabled
    os.environ["DEV_DISABLE_CONFIG_DB"] = (
        "true"  # Skip config database, only need webservice cache
    )

    try:
        service_config = FEWS_SERVICES[service_name]

        # Create user settings (only webservice URL needed for cache saving)
        user_settings = {
            "client_id": f"cache_save_{service_name}",
            "FEWS_DB_PATH": "data/fews_config.db3",  # Dummy path, not used for webservice cache
            "FEWS_WEB_SERVICE_URL": service_config.web_service_url,
        }

        print(f"Service name: {service_config.name}")
        print(f"Webservice URL: {user_settings['FEWS_WEB_SERVICE_URL']}")
        print("Note: Only webservice data will be cached (no config database needed)")

        # Get runtime context (this will trigger ingestion and save cache)
        print("Setting up runtime context and ingesting data...")
        get_runtime_ctx(user_settings)

        print(f"✅ Successfully processed {service_name}")

    except Exception as e:
        print(f"❌ Error processing {service_name}: {e}")
        return False

    return True


def main():
    """Main function to save cache for services."""
    print("🚀 Starting webservice cache saving process")
    print("This will ingest data from FEWS webservices and save to disk")

    available_services = list(FEWS_SERVICES.keys())
    print(f"Available services: {', '.join(available_services)}")

    # Determine which services to process
    if len(sys.argv) > 1:
        service_name = sys.argv[1]
        if service_name not in available_services:
            print(
                f"Error: Service '{service_name}' not found in available services: {available_services}"
            )
            return
        services_to_process = [service_name]
    else:
        services_to_process = available_services
        print(f"Processing all services: {services_to_process}")

    # Process each service
    successful = 0
    failed = 0

    for service in services_to_process:
        if save_cache_for_service(service):
            successful += 1
        else:
            failed += 1

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print("📁 Cache files saved to: data/webservice_cache/")

    if successful > 0:
        print("\nTo investigate the saved databases, run:")
        print("python scripts/investigate_cache.py")


if __name__ == "__main__":
    main()
