#!/usr/bin/env python3
"""
Simple script to query series headers for Kwel parameter
"""

import asyncio
import os
from src.talk_with_fews.tools.webservice.get_series_headers import get_series_headers
from src.talk_with_fews.models.get_series_headers import GetSeriesHeadersInput
from src.talk_with_fews.routers.setup_connections import get_runtime_ctx

async def main():
    # Setup environment
    os.environ['FEWS_WEB_SERVICE_URL'] = 'https://actueelwaterbeeld-api.hkvservices.nl/FewsWebServices'
    os.environ['FEWS_DB_PATH'] = 'data/fews_config.db3'
    
    # Get runtime context
    ctx = get_runtime_ctx()
    
    # Create input for Kwel parameter
    input_data = GetSeriesHeadersInput(parameter_id='Kwel')
    
    # Query series headers
    result = await get_series_headers(ctx, input_data)
    
    # Print results
    print(f"=== Series Headers voor Kwel ===")
    print(f"Aantal series gevonden: {result.count}")
    print(f"Samenvatting: {result.summary}")
    print(f"Voorbeeld IDs: {result.sample_ids}")
    print(f"Beschikbare filters: {result.available_filters}")
    print(f"Vervolg suggesties: {result.follow_up_suggestions}")

if __name__ == "__main__":
    asyncio.run(main()) 