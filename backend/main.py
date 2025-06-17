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

# Load environment variables
load_dotenv()

# Initialize Vertex AI directly here (don't rely on story_ai module)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ecoinsight-2025")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

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
        print(f"Generating story for city: {data.city}")
        
        # 1. Fetch latest weather for the city
        weather_doc = await db.weather.find_one(
            {"city": data.city},
            sort=[("timestamp", -1)]
        )
        
        if not weather_doc:
            raise HTTPException(status_code=404, detail=f"No weather data found for city: {data.city}")

        # 2. Format it as climate_data string
        climate_data = f"""
        - Temperature: {weather_doc['temperature']}°C
        - Weather: {weather_doc['weather']}
        - Humidity: {weather_doc['humidity']}%
        - Wind Speed: {weather_doc['wind_speed']} m/s
        """
        
        print(f"Climate data: {climate_data}")

        # 3. Create prompt
        prompt = create_prompt(data.city, climate_data)
        print(f"Generated prompt length: {len(prompt)} characters")
        
        
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
        embedding_list = embedding.tolist()  # Convert NumPy array to list for MongoDB

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
        print(f"Story saved to MongoDB with ID: {result.inserted_id}")
        
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
        query_embedding = embedding_model.encode(request.query).tolist()
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # name of your vector index
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
        
        return {"results": results}

    except Exception as e:
        print(f"Semantic search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")




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
