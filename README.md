# 🌱 EcoInsight: AI-Powered Climate Storyteller

**EcoInsight** is an intelligent web application that transforms real-time environmental data into compelling climate stories. It leverages the power of generative AI, vector search, and scalable cloud infrastructure to raise climate awareness in an accessible and engaging way.


---

## 🚀 Features

- 🌍 Fetches **real-time weather and air quality data** via OpenWeatherMap API
- 🧠 Uses **Google Cloud Vertex AI (Gemini)** to generate human-like climate stories
- 🧾 Stores all stories and metadata in **MongoDB**, including **vector embeddings** for semantic search
- 🔍 Enables **semantic similarity search** to compare climate stories across locations
- ☁️ Deployed using **Google Cloud Run** for scale and performance

---

## How It Works

1. **User Inputs City**  
   → A user enters a city in the Next.js frontend interface.

2. **Real-Time Data Fetching**  
   → The FastAPI backend fetches live weather + AQI data from OpenWeatherMap.

3. **Story Generation with Vertex AI**  
   → Using the climate data, a prompt is created and passed to **Gemini via Vertex AI**, which generates a rich, localized climate story.

4. **Vector Embedding & Storage in MongoDB**  
   → The generated story is embedded into a vector using **SentenceTransformers** and stored in MongoDB along with metadata.

5. **Semantic Search**  
   → Similar stories can be retrieved using **MongoDB Atlas Vector Search**, enabling natural-language and similarity-based story comparisons.

---

## Tech Stack

### Frontend
- **Next.js 14**
- Tailwind CSS
- Deployed via **Vercel**

### Backend
- **FastAPI** with async support

### AI & ML
- **Google Vertex AI** (Gemini 2.0)
- **SentenceTransformers** (`all-MiniLM-L6-v2`) for embeddings

### Database
- **MongoDB Atlas** with:
  - Flexible document storage
  - Vector Search using `embedding` field
  - Time-based sorting & city filtering

### Cloud Deployment
- **Google Cloud Run** (for FastAPI backend)
- **Google Cloud Build** for containerization
- **Secret Manager** for API keys and environment variables

### Try it out

[EcoInsight](https://ecoinsight-nu.vercel.app/)

