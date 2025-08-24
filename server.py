#!/usr/bin/env python3
"""
Falling Fruit MCP Server using FastMCP

This server provides tools to interact with the Falling Fruit API,
allowing users to discover fruit trees and foraging opportunities.
"""

import os
from datetime import datetime, timedelta
from math import cos, radians, sin, asin, sqrt
from typing import Optional, Dict, List, Any
from urllib.parse import urlencode

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import httpx
from fastmcp import FastMCP
from geopy.geocoders import Nominatim
from pydantic import BaseModel

# Falling Fruit API base URL
API_BASE_URL = "https://fallingfruit.org/api/0.3"

# API key from environment variable
API_KEY = os.getenv("FALLING_FRUIT_API_KEY")
if API_KEY == "":  # Treat empty string as None
    API_KEY = None

# Geocoder for location resolution
geolocator = Nominatim(user_agent="falling-fruit-mcp-server")

# Create FastMCP server
mcp = FastMCP("Falling Fruit MCP Server")

class FruitLocation(BaseModel):
    """Represents a fruit tree location from the API"""
    id: int
    lat: float
    lng: float
    type_ids: list[int] = []
    description: str = ""
    access: int = 0
    season_start: Optional[int] = None
    season_stop: Optional[int] = None

class FruitType(BaseModel):
    """Represents a fruit type from the API"""
    id: int
    name: str
    scientific_name: str = ""
    common_names: List[str] = []
    scientific_names: List[str] = []

class FallingFruitAPI:
    """Client for interacting with the Falling Fruit API"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.api_key = API_KEY
        self._types_cache = None
        self._cache_timestamp = None
        self._cache_duration = timedelta(hours=24)  # Cache for 24 hours
        
    async def get_locations(self, lat: float, lng: float, radius_km: int = 10, type_id: Optional[int] = None, limit: int = 100) -> list[FruitLocation]:
        """Get fruit locations near a given coordinate"""
        if not self.api_key:
            raise ValueError("Falling Fruit API key is not set. Please set the FALLING_FRUIT_API_KEY environment variable.")
            
        params = {
            "center": f"{lat},{lng}",
            "limit": limit,
            "photo": 0
        }
        
        if type_id:
            params["types"] = type_id
            
        headers = {"X-API-KEY": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/locations", params=params, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            locations = []
            for item in data:
                try:
                    location = FruitLocation(**item)
                    # Filter by distance if specified
                    if radius_km and self._calculate_distance(lat, lng, location.lat, location.lng) <= radius_km:
                        locations.append(location)
                except Exception as e:
                    continue
                    
            return locations[:limit]
    

    
    async def get_all_types(self) -> list[FruitType]:
        """Get all fruit types with caching"""
        if not self.api_key:
            raise ValueError("Falling Fruit API key is not set. Please set the FALLING_FRUIT_API_KEY environment variable.")
            
        # Check cache
        now = datetime.now()
        if (self._types_cache is not None and 
            self._cache_timestamp is not None and 
            now - self._cache_timestamp < self._cache_duration):
            return self._types_cache
            
        headers = {"X-API-KEY": self.api_key}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/types", headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            
            types = []
            for item in data:
                try:
                    # Parse the complex structure from the API
                    common_names = []
                    scientific_names = []
                    
                    if 'common_names' in item and isinstance(item['common_names'], dict):
                        for lang, names in item['common_names'].items():
                            if isinstance(names, list):
                                common_names.extend(names)
                                
                    if 'scientific_names' in item and isinstance(item['scientific_names'], list):
                        scientific_names.extend(item['scientific_names'])
                    
                    # Use first common name as primary name, fallback to scientific
                    primary_name = common_names[0] if common_names else (scientific_names[0] if scientific_names else "Unknown")
                    primary_scientific = scientific_names[0] if scientific_names else ""
                    
                    fruit_type = FruitType(
                        id=item['id'],
                        name=primary_name,
                        scientific_name=primary_scientific,
                        common_names=common_names,
                        scientific_names=scientific_names
                    )
                    types.append(fruit_type)
                except Exception as e:
                    continue
                    
            # Cache the results
            self._types_cache = types
            self._cache_timestamp = now
            return types

    async def get_types(self, query: Optional[str] = None) -> list[FruitType]:
        """Get fruit types, filtered by query (client-side filtering)"""
        all_types = await self.get_all_types()
        
        if not query:
            return all_types
            
        query_lower = query.lower()
        filtered_types = []
        
        for fruit_type in all_types:
            # Check if query matches any name
            all_names = fruit_type.common_names + fruit_type.scientific_names
            for name in all_names:
                if query_lower in name.lower():
                    filtered_types.append(fruit_type)
                    break
                    
        return filtered_types

    async def find_fruit_type_by_name(self, name: str) -> Optional[FruitType]:
        """Find a fruit type by exact or partial name match"""
        all_types = await self.get_all_types()
        name_lower = name.lower()
        
        # First try exact matches
        for fruit_type in all_types:
            all_names = fruit_type.common_names + fruit_type.scientific_names
            for type_name in all_names:
                if type_name.lower() == name_lower:
                    return fruit_type
        
        # Then try partial matches
        for fruit_type in all_types:
            all_names = fruit_type.common_names + fruit_type.scientific_names
            for type_name in all_names:
                if name_lower in type_name.lower():
                    return fruit_type
                    
        return None
    

    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = (
            sin(dlat / 2) ** 2 +
            cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
        )
        c = 2 * asin(sqrt(a))
        
        return R * c

class LocationHelper:
    """Helper for geocoding and location operations"""
    
    @staticmethod
    async def geocode_location(location: str) -> Optional[tuple[float, float]]:
        """Convert location string to lat/lng coordinates"""
        try:
            geo_result = geolocator.geocode(location, timeout=10)
            if geo_result:
                return (geo_result.latitude, geo_result.longitude)
        except Exception as e:
            print(f"Geocoding error: {e}")
        return None

class MapsHelper:
    """Helper for generating Google Maps links"""
    
    @staticmethod
    def generate_maps_link(lat: float, lng: float, label: Optional[str] = None) -> str:
        """Generate a Google Maps link for the given coordinates with a pin marker"""
        # Always use coordinates directly with pin to avoid search confusion
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    
    @staticmethod
    def generate_directions_link(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> str:
        """Generate a Google Maps directions link from origin to destination"""
        return f"https://www.google.com/maps/dir/{origin_lat},{origin_lng}/{dest_lat},{dest_lng}"

class SeasonHelper:
    """Helper for season-related operations"""
    
    @staticmethod
    def is_in_season(season_start: Optional[int], season_stop: Optional[int]) -> bool:
        """Check if current month is within the fruit season"""
        if season_start is None or season_stop is None:
            return True  # If no season info, assume always available
        
        current_month = datetime.now().month
        
        if season_start <= season_stop:
            return season_start <= current_month <= season_stop
        else:
            # Season spans across year boundary (e.g., Dec-Feb)
            return current_month >= season_start or current_month <= season_stop
    
    @staticmethod
    def format_season(season_start: Optional[int], season_stop: Optional[int]) -> str:
        """Format season months as human-readable string"""
        if season_start is None or season_stop is None:
            return "Season unknown"
        
        months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
        
        if season_start == season_stop:
            return f"{months[season_start - 1]}"
        elif season_start < season_stop:
            return f"{months[season_start - 1]} - {months[season_stop - 1]}"
        else:
            return f"{months[season_start - 1]} - {months[season_stop - 1]} (next year)"

# Initialize API client
api_client = FallingFruitAPI()

@mcp.tool
async def search_fruit_locations(location: str, fruit_type: Optional[str] = None, radius_km: int = 10) -> Dict[str, Any]:
    """
    Search for fruit tree locations in a specific area.
    
    Args:
        location: Location to search (e.g., 'Vancouver BC', 'Yaletown Vancouver', 'Downtown Toronto')
        fruit_type: Optional type of fruit to search for (e.g., 'apple', 'blackberry', 'cherry')
        radius_km: Search radius in kilometers (default: 10)
    """
    # Geocode the location
    geo_result = await LocationHelper.geocode_location(location)
    if not geo_result:
        return {
            "success": False,
            "error": f"Could not find location: {location}",
            "location": location
        }
    
    lat, lng = geo_result
    
    # Get fruit type ID if specified
    type_id = None
    fruit_type_info = None
    if fruit_type:
        types = await api_client.get_types(fruit_type)
        if types:
            type_id = types[0].id
            fruit_type_info = {
                "id": types[0].id,
                "name": types[0].name,
                "scientific_name": types[0].scientific_name
            }
    
    # Get locations
    locations = await api_client.get_locations(lat, lng, radius_km, type_id, limit=50)
    
    if not locations:
        return {
            "success": True,
            "location": location,
            "search_center": {"lat": lat, "lng": lng},
            "fruit_type": fruit_type_info,
            "radius_km": radius_km,
            "total_found": 0,
            "locations": []
        }
    
    # Format results
    access_levels = {0: "unknown", 1: "public", 2: "permission_needed", 3: "private"}
    
    result_locations = []
    for loc in locations:
        distance = api_client._calculate_distance(lat, lng, loc.lat, loc.lng)
        season = SeasonHelper.format_season(loc.season_start, loc.season_stop)
        access = access_levels.get(loc.access, "unknown")
        in_season = SeasonHelper.is_in_season(loc.season_start, loc.season_stop)
        
        maps_link = MapsHelper.generate_maps_link(loc.lat, loc.lng)
        
        result_locations.append({
            "id": loc.id,
            "coordinates": {"lat": loc.lat, "lng": loc.lng},
            "distance_km": round(distance, 1),
            "type_ids": loc.type_ids,
            "description": loc.description,
            "access": access,
            "season": {
                "formatted": season,
                "start_month": loc.season_start,
                "stop_month": loc.season_stop,
                "in_season": in_season
            },
            "maps_link": maps_link
        })
    
    return {
        "success": True,
        "location": location,
        "search_center": {"lat": lat, "lng": lng},
        "fruit_type": fruit_type_info,
        "radius_km": radius_km,
        "total_found": len(locations),
        "locations": result_locations
    }

@mcp.tool
async def get_seasonal_fruits(location: str, radius_km: int = 10) -> Dict[str, Any]:
    """
    Find fruits that are currently in season near a location.
    
    Args:
        location: Location to search (e.g., 'Vancouver BC', 'Downtown Seattle')
        radius_km: Search radius in kilometers (default: 10)
    """
    # Geocode the location
    geo_result = await LocationHelper.geocode_location(location)
    if not geo_result:
        return {
            "success": False,
            "error": f"Could not find location: {location}",
            "location": location
        }
    
    lat, lng = geo_result
    
    # Get all locations
    locations = await api_client.get_locations(lat, lng, radius_km, limit=100)
    
    # Filter to only in-season fruits
    seasonal_locations = [
        loc for loc in locations 
        if SeasonHelper.is_in_season(loc.season_start, loc.season_stop)
    ]
    
    if not seasonal_locations:
        return {
            "success": True,
            "location": location,
            "search_center": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "current_month": datetime.now().month,
            "current_month_name": datetime.now().strftime("%B"),
            "total_seasonal_locations": 0,
            "fruit_types": []
        }
    
    # Get type information
    all_types = await api_client.get_types()
    type_names = {t.id: t.name for t in all_types}
    type_scientific = {t.id: t.scientific_name for t in all_types}
    
    # Group locations by type
    by_type = {}
    for loc in seasonal_locations:
        for type_id in loc.type_ids:
            if type_id not in by_type:
                by_type[type_id] = []
            by_type[type_id].append(loc)
    
    # Format fruit types with their locations
    fruit_types = []
    for type_id, locs in by_type.items():
        type_name = type_names.get(type_id, f"Type {type_id}")
        scientific_name = type_scientific.get(type_id, "")
        
        # Get location details for this fruit type
        type_locations = []
        for loc in locs:
            distance = api_client._calculate_distance(lat, lng, loc.lat, loc.lng)
            maps_link = MapsHelper.generate_maps_link(loc.lat, loc.lng)
            
            type_locations.append({
                "id": loc.id,
                "coordinates": {"lat": loc.lat, "lng": loc.lng},
                "distance_km": round(distance, 1),
                "description": loc.description,
                "maps_link": maps_link
            })
        
        # Sort by distance
        type_locations.sort(key=lambda x: x["distance_km"])
        
        fruit_types.append({
            "type_id": type_id,
            "name": type_name,
            "scientific_name": scientific_name,
            "location_count": len(locs),
            "closest_distance_km": round(min(loc["distance_km"] for loc in type_locations), 1),
            "locations": type_locations
        })
    
    # Sort fruit types by closest distance
    fruit_types.sort(key=lambda x: x["closest_distance_km"])
    
    return {
        "success": True,
        "location": location,
        "search_center": {"lat": lat, "lng": lng},
        "radius_km": radius_km,
        "current_month": datetime.now().month,
        "current_month_name": datetime.now().strftime("%B"),
        "total_seasonal_locations": len(seasonal_locations),
        "fruit_types": fruit_types
    }

@mcp.tool
async def get_id_for_fruit(fruit_name: str) -> Dict[str, Any]:
    """
    Get the ID and details for a specific fruit type by name.
    
    Args:
        fruit_name: Name of the fruit (e.g., 'apple', 'cherry', 'blackberry')
    """
    fruit_type = await api_client.find_fruit_type_by_name(fruit_name)
    
    if not fruit_type:
        # Try to find similar fruits
        all_types = await api_client.get_all_types()
        suggestions = []
        
        # Find fruits that contain the search term
        for ft in all_types:
            all_names = ft.common_names + ft.scientific_names
            for name in all_names:
                if fruit_name.lower() in name.lower():
                    suggestions.append({
                        "id": ft.id,
                        "name": name,
                        "scientific_name": ft.scientific_name
                    })
                    if len(suggestions) >= 5:  # Limit suggestions
                        break
            if len(suggestions) >= 5:
                break
        
        return {
            "success": False,
            "query": fruit_name,
            "message": f"No exact match found for '{fruit_name}'",
            "suggestions": suggestions[:5] if suggestions else [],
            "tip": "Try searching with more specific terms like 'red apple' or 'sweet cherry'"
        }
    
    return {
        "success": True,
        "query": fruit_name,
        "fruit_type": {
            "id": fruit_type.id,
            "name": fruit_type.name,
            "scientific_name": fruit_type.scientific_name,
            "common_names": fruit_type.common_names[:10],  # Limit for readability
            "scientific_names": fruit_type.scientific_names[:3]
        },
        "usage_tip": f"Use ID {fruit_type.id} in other tools to search for {fruit_type.name} locations"
    }

@mcp.tool
async def find_fruit_types(query: str) -> Dict[str, Any]:
    """
    Search for fruit types by name or scientific name.
    
    Args:
        query: Search term for fruit types (e.g., 'apple', 'cherry', 'citrus')
    """
    types = await api_client.get_types(query)
    
    if not types:
        return {
            "success": True,
            "query": query,
            "total_found": 0,
            "fruit_types": []
        }
    
    fruit_types = []
    for fruit_type in types:
        fruit_types.append({
            "id": fruit_type.id,
            "name": fruit_type.name,
            "scientific_name": fruit_type.scientific_name
        })
    
    return {
        "success": True,
        "query": query,
        "total_found": len(types),
        "fruit_types": fruit_types
    }

@mcp.tool
async def get_location_details(location: str, fruit_type: Optional[str] = None, radius_km: int = 5) -> Dict[str, Any]:
    """
    Get detailed information about fruit locations in an area.
    
    Args:
        location: Location to search around (e.g., 'Central Park NYC', 'Golden Gate Park SF')
        fruit_type: Optional specific fruit type to focus on
        radius_km: Search radius in kilometers (default: 5)
    """
    # Geocode the location
    geo_result = await LocationHelper.geocode_location(location)
    if not geo_result:
        return {
            "success": False,
            "error": f"Could not find location: {location}",
            "location": location
        }
    
    lat, lng = geo_result
    
    # Get fruit type ID if specified
    type_id = None
    fruit_type_info = None
    if fruit_type:
        types = await api_client.get_types(fruit_type)
        if types:
            type_id = types[0].id
            fruit_type_info = {
                "id": types[0].id,
                "name": types[0].name,
                "scientific_name": types[0].scientific_name
            }
    
    # Get locations
    locations = await api_client.get_locations(lat, lng, radius_km, type_id, limit=20)
    
    if not locations:
        return {
            "success": True,
            "location": location,
            "search_center": {"lat": lat, "lng": lng},
            "fruit_type": fruit_type_info,
            "radius_km": radius_km,
            "total_found": 0,
            "locations": []
        }
    
    # Get type information for display
    all_types = await api_client.get_types()
    type_names = {t.id: t.name for t in all_types}
    type_scientific = {t.id: t.scientific_name for t in all_types}
    
    access_levels = {0: "unknown", 1: "public", 2: "permission_needed", 3: "private"}
    
    detailed_locations = []
    for loc in locations:
        distance = api_client._calculate_distance(lat, lng, loc.lat, loc.lng)
        season = SeasonHelper.format_season(loc.season_start, loc.season_stop)
        access = access_levels.get(loc.access, "unknown")
        in_season = SeasonHelper.is_in_season(loc.season_start, loc.season_stop)
        
        # Get fruit types for this location
        fruits = []
        for tid in loc.type_ids:
            fruits.append({
                "id": tid,
                "name": type_names.get(tid, f"Type {tid}"),
                "scientific_name": type_scientific.get(tid, "")
            })
        
        maps_link = MapsHelper.generate_maps_link(loc.lat, loc.lng)
        directions_link = MapsHelper.generate_directions_link(lat, lng, loc.lat, loc.lng)
        
        detailed_locations.append({
            "id": loc.id,
            "coordinates": {"lat": loc.lat, "lng": loc.lng},
            "distance_km": round(distance, 1),
            "fruits": fruits,
            "description": loc.description,
            "access": access,
            "season": {
                "formatted": season,
                "start_month": loc.season_start,
                "stop_month": loc.season_stop,
                "in_season": in_season
            },
            "maps_link": maps_link,
            "directions_link": directions_link
        })
    
    # Sort by distance
    detailed_locations.sort(key=lambda x: x["distance_km"])
    
    return {
        "success": True,
        "location": location,
        "search_center": {"lat": lat, "lng": lng},
        "fruit_type": fruit_type_info,
        "radius_km": radius_km,
        "total_found": len(locations),
        "locations": detailed_locations
    }

@mcp.tool
async def generate_maps_link(lat: float, lng: float, label: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a Google Maps link for given coordinates.
    
    Args:
        lat: Latitude coordinate
        lng: Longitude coordinate  
        label: Optional label for the location (e.g., 'Blackberry Bushes')
    """
    maps_link = MapsHelper.generate_maps_link(lat, lng, label)
    
    return {
        "success": True,
        "coordinates": {"lat": lat, "lng": lng},
        "label": label,
        "maps_link": maps_link
    }

@mcp.tool  
async def get_directions_to_fruit(location: str, fruit_location_lat: float, fruit_location_lng: float, label: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate directions from a starting location to fruit tree coordinates.
    
    Args:
        location: Starting location (e.g., 'Yaletown Vancouver BC', 'Downtown Seattle')
        fruit_location_lat: Latitude of the fruit tree location
        fruit_location_lng: Longitude of the fruit tree location
        label: Optional label for the destination (e.g., 'Apple Tree', 'Blackberry Patch')
    """
    # Geocode the starting location
    geo_result = await LocationHelper.geocode_location(location)
    if not geo_result:
        return {
            "success": False,
            "error": f"Could not find starting location: {location}",
            "origin_location": location
        }
    
    origin_lat, origin_lng = geo_result
    
    # Generate directions link
    directions_link = MapsHelper.generate_directions_link(origin_lat, origin_lng, fruit_location_lat, fruit_location_lng)
    
    return {
        "success": True,
        "origin": {
            "location": location,
            "coordinates": {"lat": origin_lat, "lng": origin_lng}
        },
        "destination": {
            "label": label or "Fruit Location",
            "coordinates": {"lat": fruit_location_lat, "lng": fruit_location_lng}
        },
        "directions_link": directions_link
    }

def main():
    """Main entry point for the server"""
    print(f"Starting Falling Fruit MCP Server...")
    if not API_KEY:
        print("⚠️  No API key found - API calls will fail with errors")
    else:
        print("✅ API key found")
    
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()