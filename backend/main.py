from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.generative_models as genai
from story_ai import create_prompt
from sentence_transformers import SentenceTransformer
import numpy as np
import asyncio
import aiohttp

# Load environment variables
load_dotenv()

# Initialize Vertex AI directly here (don't rely on story_ai module)
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("REGION")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
vertexai.init(project=PROJECT_ID, location=LOCATION)
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# MongoDB setup
MONGO_URI = os.getenv("MONGODB_URI")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.ecoinsight
stories_collection = db.get_collection("stories")

# FastAPI app
app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Story(BaseModel):
    location: str
    story_text: str
    created_at: datetime
    data_source: str

class ClimateRequest(BaseModel):
    city: str

class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/generate-climate-story")
async def generate_climate_story(data: ClimateRequest):
    try:
        city = data.city
       

        # --- 1. Fetch weather data ---
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"

        async with aiohttp.ClientSession() as session:
            async with session.get(weather_url) as weather_resp:
                if weather_resp.status != 200:
                    raise HTTPException(status_code=404, detail=f"City not found: {city}")
                weather_data = await weather_resp.json()

            lat = weather_data["coord"]["lat"]
            lon = weather_data["coord"]["lon"]

            # --- 2. Fetch air quality data ---
            aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}"

            async with session.get(aqi_url) as aqi_resp:
                if aqi_resp.status != 200:
                    raise HTTPException(status_code=404, detail=f"Air quality data not available for: {city}")
                aqi_data = await aqi_resp.json()

        components = aqi_data["list"][0]["components"]
        aqi_value = aqi_data["list"][0]["main"]["aqi"]

        # --- 3. Format climate summary ---
        climate_data = f"""
        - Temperature: {weather_data['main']['temp']}°C
        - Weather: {weather_data['weather'][0]['description'].capitalize()}
        - Humidity: {weather_data['main']['humidity']}%
        - Wind Speed: {weather_data['wind']['speed']} m/s
        - AQI: {aqi_value} (1=Good, 5=Very Poor)
        - PM2.5: {components['pm2_5']} µg/m³
        - PM10: {components['pm10']} µg/m³
        - CO: {components['co']} µg/m³
        - NO₂: {components['no2']} µg/m³
        - O₃: {components['o3']} µg/m³
        """

      

        # --- 4. Create prompt ---
        prompt = create_prompt(city, climate_data)

        model = GenerativeModel("gemini-2.0-flash-001")
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=800,
                top_k=40,
                top_p=0.8
            )
        )

        story_text = response.text       
        embedding = embedding_model.encode(story_text)
        embedding_list = embedding.tolist() 

        # 6.2 Prepare document
        story_doc = {
            "location": data.city,
            "story_text": story_text,
            "climate_data": climate_data,
            "created_at": datetime.now(timezone.utc),
            "data_source": "Vertex AI gemini-2.0-flash-001 + OpenWeatherMap",
            "model_used": "gemini-2.0-flash-001",
            "embedding": embedding_list  # <-- store it here
        }

        
        result = await stories_collection.insert_one(story_doc)
      
        return {
            "story": story_text, 
            "id": str(result.inserted_id),
            "model_used": "gemini-2.0-flash-001",
            "city": data.city
        }

    except Exception as e:
        print(f"Error in generate_climate_story: {str(e)}")
        print(f"Error type: {type(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating story: {str(e)}")
    

@app.post("/search")
async def semantic_search(request: SemanticSearchRequest):
    try:
       
        
        # Generate query embedding
        query_embedding = embedding_model.encode(request.query).tolist()
       
        
        # First, let's check if we have any documents at all
        total_docs = await stories_collection.count_documents({})
       
        
        if total_docs == 0:
            return {"results": [], "debug": "No documents found in collection"}
        
        # Check if documents have embeddings
        sample_doc = await stories_collection.find_one({})
  
        
        if sample_doc and "embedding" in sample_doc:
            print(f"Sample embedding shape: {len(sample_doc['embedding']) if sample_doc['embedding'] else 'None'}")
        else:
            print("No embedding field found in sample document")
            # Fallback to text search if no embeddings
            return await fallback_text_search(request.query, request.top_k)
        
        # Vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Make sure this matches your actual index name
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 100,
                    "limit": request.top_k
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "location": 1,
                    "story_text": 1,
                    "climate_data": 1,
                    "created_at": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        results = []
        async for doc in stories_collection.aggregate(pipeline):
            results.append(doc)
            
      
        
        # If vector search returns no results, try fallback
        if not results:
            print("No vector search results, trying fallback text search...")
            return await fallback_text_search(request.query, request.top_k)
            
        return {"results": results}
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        print(f"Error type: {type(e)}")
        
        # Try fallback search on error
        try:
            return await fallback_text_search(request.query, request.top_k)
        except Exception as fallback_error:
            print(f"Fallback search also failed: {str(fallback_error)}")
            return {"results": [], "error": str(e)}

async def fallback_text_search(query: str, limit: int = 5):
    """Fallback to text-based search when vector search fails"""
    print(f"Performing fallback text search for: {query}")
    
    # Simple text search using regex
    text_pipeline = [
        {
            "$match": {
                "$or": [
                    {"story_text": {"$regex": query, "$options": "i"}},
                    {"location": {"$regex": query, "$options": "i"}}
                ]
            }
        },
        {
            "$project": {
                "_id": 0,
                "location": 1,
                "story_text": 1,
                "climate_data": 1,
                "created_at": 1,
                "score": 1  # No vector score available
            }
        },
        {"$limit": limit}
    ]
    
    results = []
    async for doc in stories_collection.aggregate(text_pipeline):
        results.append(doc)
    
    print(f"Fallback search results: {len(results)}")
    return {"results": results, "search_type": "text_fallback"}



@app.get("/stories/{city}")
async def get_stories_by_city(city: str):
    """Get all stories for a specific city"""
    try:
        stories = []
        async for story in stories_collection.find({"location": city}):
            story["_id"] = str(story["_id"])
            stories.append(story)
        return {"stories": stories, "count": len(stories)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
