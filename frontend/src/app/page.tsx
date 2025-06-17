'use client';
import { useState } from "react";
import { useRouter } from 'next/navigation';

const cities = [
  "New York", "London", "Paris", "Tokyo", "Mumbai",
  "Sydney", "Cairo", "São Paulo", "Moscow", "Toronto", "Delhi"
];

export default function ClimateStoryGenerator() {
  const [selectedCity, setSelectedCity] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const router = useRouter();

  const generateStory = async () => {
    if (!selectedCity) return;

    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8000/generate-climate-story", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ city: selectedCity }),
      });

      const data = await response.json();

      if (!data.story) throw new Error("No story returned");

      // ✅ Redirect to story page with story in URL query
      const encodedStory = encodeURIComponent(data.story);
      router.push(`/story?city=${encodeURIComponent(selectedCity)}&story=${encodedStory}`);
      
    } catch (error) {
      console.error(error);
      setError("Failed to generate story.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="min-h-screen bg-cover bg-center bg-no-repeat flex flex-col items-center justify-center p-4"
      style={{ backgroundImage: 'url(/bg2.png)' }}
    >
      <div className="bg-white/90 backdrop-blur-sm shadow-xl rounded-2xl px-8 py-10 max-w-3xl w-full text-center">
        
        {/* Website title and description */}
        <h1 className="text-4xl font-extrabold mb-2 text-green-700">EcoInsight 🌱</h1>
        <p className="text-gray-700 mb-6 text-lg">
          Discover powerful climate stories shaped by real-time data from around the world.
          Choose a city and explore its environmental narrative.
        </p>

        {/* Dropdown */}
        <select
          className="w-full border border-gray-300 rounded-lg p-3 text-gray-800 mb-4"
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
        >
          <option value="">Select a City</option>
          {cities.map((city) => (
            <option key={city} value={city}>{city}</option>
          ))}
        </select>

        {/* Generate Button */}
        <button
          onClick={generateStory}
          className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg transition duration-200 disabled:opacity-50"
          disabled={loading || !selectedCity}
        >
          {loading ? "Generating..." : "Generate Climate Story"}
        </button>

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-300 text-red-700 rounded-md">
            <p><strong>Error:</strong> {error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
