#!/usr/bin/env python3
"""
Enhanced Debug script for Falling Fruit API

Tests the improved MCP server functionality including:
- Proper fruit type parsing with common_names/scientific_names
- Client-side filtering since API doesn't filter by query
- 24-hour caching for performance  
- Actual fruit type ID mapping for location filtering
- Real apple type detection and location search

Run: uv run python debug_api.py
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_falling_fruit_api():
    """Test the Falling Fruit API with direct HTTP calls"""
    
    api_key = os.getenv("FALLING_FRUIT_API_KEY")
    if not api_key:
        print("❌ No FALLING_FRUIT_API_KEY found in environment")
        print("Please set your API key:")
        print("export FALLING_FRUIT_API_KEY='your_key_here'")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    # Test URL from your query
    test_url = "https://fallingfruit.org/api/0.3/locations"
    params = {
        "center": "48.4283182,-123.364953",
        "limit": 50,
        "photo": 0
    }
    
    headers = {
        "X-API-KEY": api_key,
        "User-Agent": "falling-fruit-mcp-server"
    }
    
    print(f"\n🔍 Testing API call:")
    print(f"URL: {test_url}")
    print(f"Params: {params}")
    print(f"Headers: {dict(headers)}")
    
    try:
        async with httpx.AsyncClient() as client:
            print(f"\n📡 Making request...")
            response = await client.get(test_url, params=params, headers=headers, timeout=30.0)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ Success!")
                data = response.json()
                print(f"Response type: {type(data)}")
                print(f"Number of results: {len(data) if isinstance(data, list) else 'Not a list'}")
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"\nFirst result sample:")
                    print(f"{data[0]}")
                elif isinstance(data, dict):
                    print(f"\nResponse data (dict):")
                    for key, value in data.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"\nRaw response: {data}")
                    
            else:
                print(f"❌ Request failed!")
                print(f"Response body: {response.text}")
                
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except httpx.RequestError as e:
        print(f"❌ Request Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")





async def test_find_actual_apples():
    """Search through all types to find actual apple types"""
    
    api_key = os.getenv("FALLING_FRUIT_API_KEY")
    if not api_key:
        print("❌ No API key for apple search test")
        return
    
    print(f"\n🍎 Searching for Actual Apple Types in Database")
    print("=" * 50)
    
    headers = {
        "X-API-KEY": api_key,
        "User-Agent": "falling-fruit-mcp-server"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Get all types
            response = await client.get(
                "https://fallingfruit.org/api/0.3/types", 
                headers=headers, 
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"❌ Failed to get types: {response.status_code}")
                return
                
            all_types = response.json()
            print(f"✅ Got {len(all_types)} total types, searching for apples...")
            
            # Search for apple-related types
            apple_types = []
            search_terms = ['apple', 'malus', 'crab apple', 'crabapple']
            
            for fruit_type in all_types:
                if not isinstance(fruit_type, dict):
                    continue
                    
                # Extract names for searching
                common_names = []
                scientific_names = []
                
                if 'common_names' in fruit_type and isinstance(fruit_type['common_names'], dict):
                    for lang, names in fruit_type['common_names'].items():
                        if isinstance(names, list):
                            common_names.extend(names)
                            
                if 'scientific_names' in fruit_type and isinstance(fruit_type['scientific_names'], list):
                    scientific_names.extend(fruit_type['scientific_names'])
                
                # Check if any names contain apple-related terms
                all_names = common_names + scientific_names
                for name in all_names:
                    if isinstance(name, str):
                        name_lower = name.lower()
                        for term in search_terms:
                            if term in name_lower:
                                apple_types.append({
                                    'id': fruit_type.get('id'),
                                    'common_names': common_names,
                                    'scientific_names': scientific_names,
                                    'matched_name': name,
                                    'matched_term': term
                                })
                                break
                        if any(term in name_lower for term in search_terms):
                            break
            
            print(f"🍎 Found {len(apple_types)} apple-related types:")
            
            for i, apple_type in enumerate(apple_types[:10]):  # Show first 10
                print(f"  {i+1}. ID:{apple_type['id']} - {apple_type['matched_name']}")
                if apple_type['common_names']:
                    print(f"     Common names: {apple_type['common_names'][:3]}")
                if apple_type['scientific_names']:
                    print(f"     Scientific: {apple_type['scientific_names'][:2]}")
                print()
            
            if len(apple_types) > 10:
                print(f"     ... and {len(apple_types) - 10} more apple types")
                
            # Test with a specific apple type ID
            if apple_types:
                test_apple = apple_types[0]
                print(f"\n🔍 Testing location search with apple type ID {test_apple['id']}:")
                
                location_params = {
                    "center": "49.2772896,-123.1206219",  # 1001 Homer St
                    "types": str(test_apple['id']),
                    "limit": 10,
                    "photo": 0
                }
                
                loc_response = await client.get(
                    "https://fallingfruit.org/api/0.3/locations",
                    params=location_params,
                    headers=headers,
                    timeout=30.0
                )
                
                if loc_response.status_code == 200:
                    apple_locations = loc_response.json()
                    print(f"  ✅ Found {len(apple_locations)} locations for {test_apple['matched_name']}")
                    if apple_locations:
                        print(f"  First location: {apple_locations[0]}")
                else:
                    print(f"  ❌ Location search failed: {loc_response.status_code}")
                    
        except Exception as e:
            print(f"❌ Apple search error: {e}")



async def test_without_auth():
    """Test without authentication to see what happens"""
    
    test_url = "https://fallingfruit.org/api/0.3/locations"
    params = {
        "center": "48.4283182,-123.364953",
        "limit": 5,
        "photo": 0
    }
    
    print(f"\n🔍 Testing without authentication:")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(test_url, params=params, timeout=30.0)
            print(f"Status Code (no auth): {response.status_code}")
            print(f"Response (no auth): {response.text[:200]}...")
                
    except Exception as e:
        print(f"❌ No auth test error: {e}")

async def test_enhanced_api_client():
    """Test our enhanced API client with caching and proper parsing"""
    print(f"\n🚀 Testing Enhanced API Client")
    print("=" * 50)
    
    # Import our enhanced client
    import sys
    sys.path.append('.')
    from server import FallingFruitAPI
    
    try:
        client = FallingFruitAPI()
        
        print("🔍 Testing get_all_types with caching...")
        start_time = asyncio.get_event_loop().time()
        all_types = await client.get_all_types()
        first_call_time = asyncio.get_event_loop().time() - start_time
        
        print(f"  ✅ First call: {len(all_types)} types in {first_call_time:.2f}s")
        
        # Test caching
        start_time = asyncio.get_event_loop().time()
        cached_types = await client.get_all_types()
        cached_call_time = asyncio.get_event_loop().time() - start_time
        
        print(f"  ✅ Cached call: {len(cached_types)} types in {cached_call_time:.3f}s")
        print(f"  🚀 Cache speedup: {first_call_time/cached_call_time:.1f}x faster")
        
        # Show some actual parsed types
        apple_types = [t for t in all_types if any('apple' in name.lower() for name in t.common_names + t.scientific_names)]
        print(f"\n🍎 Found {len(apple_types)} apple types with proper parsing:")
        
        for i, apple_type in enumerate(apple_types[:5]):
            print(f"  {i+1}. ID:{apple_type.id} - {apple_type.name}")
            print(f"     Common names: {apple_type.common_names[:3]}")
            print(f"     Scientific: {apple_type.scientific_names[:2]}")
            print()
            
        # Test client-side filtering
        print("🔍 Testing client-side filtering...")
        apple_search = await client.get_types("apple")
        print(f"  ✅ Apple search: {len(apple_search)} results")
        
        cherry_search = await client.get_types("cherry")
        print(f"  ✅ Cherry search: {len(cherry_search)} results")
        
        # Test exact name lookup
        print("\n🎯 Testing find_fruit_type_by_name...")
        apple_type = await client.find_fruit_type_by_name("apple")
        if apple_type:
            print(f"  ✅ Found apple: ID:{apple_type.id} - {apple_type.name}")
        else:
            print(f"  ❌ No apple type found")
            
        crabapple_type = await client.find_fruit_type_by_name("crabapple")
        if crabapple_type:
            print(f"  ✅ Found crabapple: ID:{crabapple_type.id} - {crabapple_type.name}")
        else:
            print(f"  ❌ No crabapple type found")
            
    except Exception as e:
        print(f"❌ Enhanced API client test error: {e}")

async def test_location_filtering():
    """Test if location search actually filters by type ID"""
    print(f"\n🎯 Testing Location Filtering with Real Type IDs")
    print("=" * 50)
    
    import sys
    sys.path.append('.')
    from server import FallingFruitAPI
    
    try:
        client = FallingFruitAPI()
        
        # Get some actual apple types
        apple_types = await client.get_types("apple")
        if not apple_types:
            print("❌ No apple types found to test with")
            return
            
        test_apple = apple_types[0]
        print(f"🍎 Testing with apple type: ID:{test_apple.id} - {test_apple.name}")
        
        # Test location search without type filter
        print(f"\n🔍 Location search WITHOUT type filter:")
        all_locations = await client.get_locations(49.2772896, -123.1206219, radius_km=2, limit=10)
        print(f"  ✅ Found {len(all_locations)} total locations")
        
        # Test location search WITH type filter
        print(f"\n🔍 Location search WITH apple type filter (ID:{test_apple.id}):")
        apple_locations = await client.get_locations(49.2772896, -123.1206219, radius_km=2, type_id=test_apple.id, limit=10)
        print(f"  ✅ Found {len(apple_locations)} apple locations")
        
        if len(apple_locations) < len(all_locations):
            print(f"  🎉 Filtering works! {len(all_locations) - len(apple_locations)} locations filtered out")
        elif len(apple_locations) == len(all_locations):
            print(f"  ⚠️  Same number of results - filtering may not be working")
        
        # Show type IDs in results
        if apple_locations:
            print(f"\n📊 Type IDs in filtered results:")
            for i, loc in enumerate(apple_locations[:3]):
                print(f"  Location {i+1}: type_ids = {loc.type_ids}")
                if test_apple.id in loc.type_ids:
                    print(f"    ✅ Contains our apple type ID {test_apple.id}")
                else:
                    print(f"    ❌ Missing our apple type ID {test_apple.id}")
                    
    except Exception as e:
        print(f"❌ Location filtering test error: {e}")

if __name__ == "__main__":
    print("🚀 Falling Fruit API Debug Script - Enhanced Version")
    print("=" * 60)
    
    # Test basic API connectivity
    asyncio.run(test_falling_fruit_api())
    
    # Test our enhanced functionality  
    asyncio.run(test_find_actual_apples())
    asyncio.run(test_enhanced_api_client())
    asyncio.run(test_location_filtering())
    
    # Test edge cases
    asyncio.run(test_without_auth())
