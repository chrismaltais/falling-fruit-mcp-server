# Falling Fruit MCP Server 🍎

A Model Context Protocol (MCP) server that connects to the [Falling Fruit API](https://github.com/falling-fruit/falling-fruit-api) to help you find edible plants and trees near you! Ask natural language questions about foraging opportunities in your area.

## Features

- 🔍 **Search fruit locations** by area and fruit type
- 🍂 **Find seasonal fruits** currently available in your location  
- 🌱 **Discover fruit types** and get detailed information
- 📍 **Get location details** for specific foraging spots
- 🗺️ **Generate map links** and get directions to fruit trees
- 🧭 **Navigation support** with turn-by-turn directions
- 🌍 **Geocoding support** - search by city, neighborhood, or coordinates

## Example Queries

- "What fruits are in season near Vancouver BC?"
- "Where can I find blackberries in Yaletown?"
- "Show me apple trees within 5km of downtown Seattle"
- "What's available to forage in Central Park NYC?"
- "Get directions to the nearest apple orchard from downtown Portland"
- "Find all types of cherries available in the database"
- "Give me detailed information about fruit trees in Golden Gate Park"
- "Generate a map link for these berry coordinates"

## Installation

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- A Falling Fruit API key (optional, uses mock data as fallback)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/chrismaltais/falling-fruit-mcp-server.git
   cd falling-fruit-mcp-server
   ```

2. **Get a Falling Fruit API key (optional):**
   - Visit [Falling Fruit API documentation](https://github.com/falling-fruit/falling-fruit-api)
   - Request an API key from the maintainers

3. **Configure environment:**
   ```bash
   # Create .env file with your API key
   echo "FALLING_FRUIT_API_KEY=your_api_key_here" > .env
   ```

4. **Install dependencies:**
   ```bash
   uv sync
   ```

5. **Test the server:**
   ```bash
   uv run server.py
   ```

## Adding to Cursor as MCP Client

To use this server with Cursor IDE, you need to configure it in your MCP settings:

### Add the Falling Fruit server configuration

Add this configuration to your `mcp.json`:

```json
{
  "mcpServers": {
    "falling-fruit": {
      "command": "uv",
      "args": [
        "run", 
        "--directory",
        "/path/to/your/falling-fruit-mcp-server",
        "server.py"
      ],
      "env": {
        "FALLING_FRUIT_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Important:** Replace `/path/to/your/falling-fruit-mcp-server` with the actual absolute path to your project directory.

### Verify connection

You should see the Falling Fruit tools available. You can then ask questions like:

- "Find apple trees near my location"
- "What fruits are in season in Portland Oregon?"
- "Show me foraging spots in Golden Gate Park"
- "Get directions to blackberry bushes from downtown Vancouver"
- "Generate a map link for fruit trees in Central Park"
- "What types of cherries are available in the database?"

## Available Tools

The server provides seven comprehensive tools for fruit foraging:

1. **`search_fruit_locations`** - Search for fruit tree locations in a specific area
   - Find trees by location and optional fruit type
   - Specify search radius (default: 10km)
   - Example: Find blackberries within 5km of Vancouver BC

2. **`get_seasonal_fruits`** - Find fruits currently in season near a location
   - Get seasonally available fruits for any location
   - Automatic season detection based on current date
   - Example: What's in season in Portland Oregon right now?

3. **`find_fruit_types`** - Search for fruit types by name or scientific name
   - Discover available fruit varieties in the database
   - Search by common or scientific names
   - Example: Find all types of apples or crabapples

4. **`get_id_for_fruit`** - Get the ID and details for a specific fruit type
   - Look up specific fruit information by name
   - Returns scientific names and common names
   - Useful for precise searches

5. **`get_location_details`** - Get detailed information about fruit locations
   - Enhanced location data with fruit types and descriptions
   - Includes access information and seasonal data
   - Perfect for planning foraging trips

6. **`generate_maps_link`** - Generate Google Maps links for coordinates
   - Create shareable map links for fruit locations
   - Add custom labels for easy identification
   - Direct integration with mapping services

7. **`get_directions_to_fruit`** - Generate directions to fruit tree locations
   - Turn-by-turn directions from your location to fruit trees
   - Custom labels for destination identification
   - Perfect for navigation to foraging spots

## Technical Details

- **Framework:** [FastMCP](https://github.com/jlowin/fastmcp) for robust MCP protocol handling
- **HTTP Client:** `httpx` for async API requests
- **Geocoding:** `geopy` with Nominatim for location resolution
- **Package Manager:** `uv` for fast dependency management
- **Transport:** STDIO for MCP communication

## Troubleshooting

### Server won't start
- Ensure Python 3.10+ is installed
- Check that `uv` is installed and working
- Verify the `.env` file is in the project root

### Cursor can't connect
- Double-check the absolute path in `mcp.json`
- Ensure Cursor is completely restarted
- Test the server manually with `uv run server.py`

### API errors
- If you see 401 errors, verify your API key is correct
- The server will fall back to mock data if no API key is provided
- Check that the `.env` file contains `FALLING_FRUIT_API_KEY=your_key`

## Contributing

Contributions welcome! This server connects to the open-source [Falling Fruit project](https://github.com/falling-fruit/falling-fruit-api) which maps edible plants worldwide.

## License

This project follows the same open-source spirit as Falling Fruit. Please respect the API terms of service and contribute back to the community! 🌱
