import os
import asyncio
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
MONGODB_URI = os.getenv("MONGODB_URI")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITIES = [
  "New York", "London", "Paris", "Tokyo", "Mumbai",
  "Sydney", "Cairo", "São Paulo", "Moscow", "Toronto", "Delhi"
]

# === MongoDB Setup ===
if not MONGODB_URI:
    raise ValueError("❌ MONGODB_URI not found in .env")
client = AsyncIOMotorClient(MONGODB_URI)
db = client.ecoinsight
weather_collection = db.weather
aqi_collection = db.aqi
nasa_collection = db.nasa_temperature


# === Fetch Current Weather ===
async def fetch_weather(session, city):
    weather_url = "http://api.openweathermap.org/data/2.5/weather"
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    aqi_url = "http://api.openweathermap.org/data/2.5/air_pollution"

    try:
        # Step 1: Get coordinates for the city
        geo_params = {
            "q": city,
            "limit": 1,
            "appid": OPENWEATHER_API_KEY
        }
        async with session.get(geo_url, params=geo_params) as geo_response:
            geo_data = await geo_response.json()
            if not geo_data:
                print(f"❌ Could not find coordinates for {city}")
                return None
            lat = geo_data[0]["lat"]
            lon = geo_data[0]["lon"]

        # Step 2: Get current weather
        weather_params = {
            "q": city,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        async with session.get(weather_url, params=weather_params) as weather_response:
            weather_data = await weather_response.json()
            if weather_response.status != 200 or weather_data.get("cod") != 200:
                print(f"❌ Weather error for {city}: {weather_data.get('message')}")
                return None

        # Step 3: Get air quality
        aqi_params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY
        }
        async with session.get(aqi_url, params=aqi_params) as aqi_response:
            aqi_data = await aqi_response.json()
            if aqi_response.status != 200 or "list" not in aqi_data:
                print(f"❌ AQI error for {city}")
                return None
            air_info = aqi_data["list"][0]
            aqi_value = air_info["main"]["aqi"]
            components = air_info["components"]

        return {
            "city": city,
            "temperature": weather_data["main"]["temp"],
            "weather": weather_data["weather"][0]["description"],
            "humidity": weather_data["main"]["humidity"],
            "wind_speed": weather_data["wind"]["speed"],
            "aqi": aqi_value,  # AQI index: 1 (Good) to 5 (Very Poor)
            "pm2_5": components["pm2_5"],
            "pm10": components["pm10"],
            "co": components["co"],
            "no2": components["no2"],
            "o3": components["o3"],
            "timestamp": datetime.now(timezone.utc)
        }

    except Exception as e:
        print(f"❌ Exception fetching weather & AQI for {city}: {e}")
        return None



# === Fetch NASA Global Temperature Anomaly Data ===
import ssl
import aiohttp

# async def fetch_nasa_temperature_anomalies(session):
#     """Fetch Berkeley Earth temperature data"""
#     try:
#         print("🔄 Trying Berkeley Earth data...")
        
#         # Berkeley Earth provides accessible data
#         url = "http://berkeleyearth.lbl.gov/auto/Global/Land_and_Ocean_complete.txt"
        
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
#         }
        
#         async with session.get(url, headers=headers, timeout=20) as response:
#             if response.status != 200:
#                 print(f"❌ Berkeley Earth request failed: {response.status}")
#                 return None
            
#             text = await response.text()
            
#             # Parse Berkeley Earth format (space-separated, skip comments)
#             lines = text.strip().split('\n')
#             data_lines = [line for line in lines if not line.startswith('%') and line.strip()]
            
#             if data_lines:
#                 # Get the last line with data
#                 last_line = data_lines[-1].split()
#                 if len(last_line) >= 2:
#                     year = int(float(last_line[0]))
#                     temp_anomaly = float(last_line[1])
                    
#                     return {
#                         "year": year,
#                         "jan": temp_anomaly,
#                         "feb": temp_anomaly,
#                         "mar": temp_anomaly,
#                         "timestamp": datetime.now(timezone.utc),
#                         "source": "Berkeley Earth"
#                     }
            
#     except Exception as e:
#         print(f"❌ Berkeley Earth fetch failed: {e}")
#         return None


# === Main Aggregate Function ===
async def fetch_and_store_all():
    async with aiohttp.ClientSession() as session:
        weather_tasks = [fetch_weather(session, city) for city in CITIES]

        # Run in parallel
        weather_data = await asyncio.gather(*weather_tasks)
        # nasa_data = await fetch_nasa_temperature_anomalies(session)

        # Store in MongoDB
        weather_clean = [w for w in weather_data if w]
        if weather_clean:
            await weather_collection.insert_many(weather_clean)
            print(f"✅ Stored weather data for {[w['city'] for w in weather_clean]}")

        # if nasa_data:
        #     await nasa_collection.insert_one(nasa_data)
        #     print(f"✅ Stored NASA temperature anomaly for {nasa_data['year']}")

if __name__ == "__main__":
    asyncio.run(fetch_and_store_all())
