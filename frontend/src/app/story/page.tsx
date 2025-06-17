'use client';
export const dynamic = 'force-dynamic';
import { useSearchParams } from 'next/navigation';
import { useState, useEffect } from 'react';

export default function StoryPage() {
  const searchParams = useSearchParams();
  const city = searchParams.get('city') || '';
  const storyParam = searchParams.get('story') || '';

  const safeDecodeStory = (encodedStory: string) => {
    if (!encodedStory) return 'No story available.';
    try {
      return decodeURIComponent(encodedStory);
    } catch (error) {
      try {
        return decodeURIComponent(encodedStory.replace(/\+/g, ' '));
      } catch {
        return encodedStory;
      }
    }
  };

  const story = safeDecodeStory(storyParam);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'story' | 'search'>('story');

  const handleSearch = async () => {
    if (!query.trim()) return;

    setSearching(true);
    setSearchResults([]);
    setError('');

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.results) {
        setSearchResults(data.results);
      } else {
        throw new Error('No results returned');
      }
    } catch (err: any) {
      console.error('Search error:', err);
      setError(err.message || 'Search failed. Please try again.');
    } finally {
      setSearching(false);
    }
  };

  return (
    <div
      className="min-h-screen bg-cover bg-center bg-no-repeat p-6 flex flex-col items-center"
      style={{ backgroundImage: 'url(/bg2.png)' }}
    >
      <div className="bg-white/70 backdrop-blur-md rounded-2xl shadow-xl p-8 w-full max-w-4xl text-gray-800">
        <h1 className="text-3xl font-bold text-green-700 mb-6 text-center">
          🌱 Climate Story for {city}
        </h1>

        {/* Tabs */}
        <div className="flex justify-center mb-6">
          <button
            className={`px-4 py-2 rounded-t-lg font-semibold transition ${
              activeTab === 'story'
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            onClick={() => setActiveTab('story')}
          >
            📖 Story
          </button>
          <button
            className={`px-4 py-2 rounded-t-lg font-semibold transition ml-2 ${
              activeTab === 'search'
                ? 'bg-green-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
            onClick={() => setActiveTab('search')}
          >
            🔍 Search Similar
          </button>
        </div>

        {/* Story Tab */}
        {activeTab === 'story' && (
          <div className="mb-6">
            {story ? (
              <p className="whitespace-pre-wrap leading-relaxed text-gray-800">
                {story}
              </p>
            ) : (
              <p className="text-gray-500 italic">
                No story available for this location.
              </p>
            )}
          </div>
        )}

        {/* Search Tab */}
        {activeTab === 'search' && (
          <div>
            <div className="mb-4">
              <input
                type="text"
                placeholder="Try searching 'flood in Chennai', 'drought in Kenya'..."
                className="w-full p-3 border rounded-lg shadow-sm focus:outline-none focus:ring focus:ring-green-400"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button
                onClick={handleSearch}
                disabled={searching || !query.trim()}
                className="mt-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold px-4 py-2 rounded-lg transition w-full"
              >
                {searching ? 'Searching...' : 'Search'}
              </button>
              {error && <p className="text-red-600 mt-2">{error}</p>}
            </div>

            {searchResults.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-bold mb-2 text-green-700">Similar Stories Found:</h3>
                <ul className="space-y-4">
                  {searchResults.map((result: any, index: number) => (
                    <li
                      key={index}
                      className="p-4 bg-white rounded-lg shadow-sm border border-gray-200"
                    >
                      <h4 className="font-semibold text-md text-green-600">{result.location}</h4>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">{result.story_text}</p>
                      <p className="text-xs text-gray-400 mt-2">
                        Generated at: {new Date(result.created_at).toLocaleString()}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
