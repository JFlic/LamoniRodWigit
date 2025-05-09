"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from 'react-markdown';
import Image from "next/image";

export default function Home() {
  const [query, setQuery] = useState("");
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const latestResponseRef = useRef(null); // Reference for the latest AI response

  // Backend URL configuration
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "https://questionroddixon.com";

  // Common questions for quick access
  const commonQuestions = [
    "How do I make a club at Graceland?",
    "What are some events on campus?",
    "Where do I eat on campus?",
    "What do I need for the Data Science?"
  ];

  // Function to scroll to the latest AI response
  const scrollToLatestResponse = () => {
    if (latestResponseRef.current) {
      latestResponseRef.current.scrollIntoView({ 
        behavior: "smooth",
        block: "start" // Align to the top of the viewport
      });
    }
  };

  // Scroll to latest response when conversations change or loading state changes
  useEffect(() => {
    if (conversations.length > 0 || !isLoading) {
      // Small delay to ensure DOM has updated
      setTimeout(scrollToLatestResponse, 100);
    }
  }, [conversations, isLoading]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setIsLoading(true);
    setError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/query/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: query }),
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status} - ${res.statusText}`);
      }

      const data = await res.json();
      
      // Process the sources to remove duplicates
      if (data.sources && data.sources.length > 0) {
        // Create a map to store unique sources based on their title and source URL
        const uniqueSourcesMap = new Map();
        
        data.sources.forEach(source => {
          const key = `${source.title || "Unknown"}|${source.source || "None"}`;
          
          // If this source hasn't been seen yet, or if the current source has a page number and the existing one doesn't
          if (!uniqueSourcesMap.has(key) || 
              (source.page && (!uniqueSourcesMap.get(key).page || uniqueSourcesMap.get(key).page > source.page))) {
            uniqueSourcesMap.set(key, source);
          }
        });
        
        // Convert the map values back to an array
        data.sources = Array.from(uniqueSourcesMap.values());
      }
      
      setConversations(prev => [...prev, { question: query, response: data }]);
      setQuery("");
    } catch (err) {
      console.error("Error fetching data:", err);
      setError(`Failed to get response: ${err.message}. Please check if the backend server is running and accessible.`);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle clicking a common question button
  const handleQuestionClick = (question) => {
    setQuery(question);
  };

  return (
    <div className={`min-h-screen ${darkMode ? "bg-gray-900 text-white" : "bg-white text-black"}`}>
      {/* Dark Mode Toggle Button */}
      <button
        onClick={() => setDarkMode(!darkMode)}
        className={`fixed top-4 left-4 p-2 rounded-lg shadow-md transition ${
          darkMode 
            ? "bg-gray-700 text-white hover:bg-gray-600" 
            : "bg-gray-200 text-black hover:bg-gray-300"
        }`}
      >
        {darkMode ? "Light Mode 🌞" : "Dark Mode 🌙"}
      </button>

      <div className="flex flex-col items-center justify-center min-h-screen">
        {conversations.length === 0 ? (
          <div className="w-full max-w-2xl px-4">
            {/* Large Rod Dixon Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-42 h-42 rounded-full overflow-hidden border-4 border-[#fbcc0d] shadow-lg">
                <Image 
                  src="/person.JPG" 
                  alt="Rod Dixon"
                  width={200}
                  height={200}
                  className="object-cover"
                />
              </div>
            </div>
            
            <h1 className="text-3xl font-bold text-center mb-8">
              Hi I'm Rod Dixon, what do you want to know about your town?
            </h1>
            
            {/* Common Questions */}
            <div className={`mb-6 grid grid-cols-1 md:grid-cols-2 gap-3`}>
              {commonQuestions.map((question, index) => (
                <button
                  key={index}
                  onClick={() => handleQuestionClick(question)}
                  className={`p-3 rounded-lg text-left transition-colors ${
                    darkMode 
                      ? "bg-[#2757a3] hover:bg-[#1e437d] text-gray" 
                      : "bg-[#fbcc0d] hover:bg-[#eabd0c] text-black"
                  }`}
                >
                  {question}
                </button>
              ))}
            </div>
            
            {/* Form Container */}
            <div className={`p-6 rounded-lg shadow-lg ${darkMode ? "bg-gray-800" : "bg-gray-100"}`}>
              <form onSubmit={handleSubmit} className="space-y-4">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter your question"
                  className={`w-full p-4 rounded-lg border ${
                    darkMode 
                      ? "bg-gray-700 text-white border-gray-600" 
                      : "bg-white text-black border-gray-300"
                  }`}
                  disabled={isLoading}
                />
                <button 
                  type="submit" 
                  className={`w-full p-4 rounded-lg transition-colors text-white ${
                    darkMode
                      ? "bg-[#0a3683] hover:bg-[#0b4094]"
                      : "bg-[#04215a] hover:bg-[#03184a]"
                  }`}
                  disabled={isLoading}
                >
                  {isLoading ? "Loading..." : "Ask Question"}
                </button>
              </form>
              {error && <div className="text-red-500 mt-4">{error}</div>}
            </div>
          </div>
        ) : (
          <div className="w-full max-w-2xl px-4 py-8 flex flex-col h-[calc(100vh-4rem)]">
            {/* Chat Container with scrollable area */}
            <div className="flex-grow overflow-y-auto mb-4 pr-2 scrollbar-thin">
              <div className="flex flex-col space-y-4">
                {conversations.map((conv, index) => (
                  <div key={index} className="flex flex-col space-y-3">
                    {/* User Message Bubble (right aligned) */}
                    <div className="flex justify-end">
                      <div className={`max-w-[75%] rounded-lg py-2 px-4 ${
                        darkMode 
                          ? "bg-[#2757a3] text-white" 
                          : "bg-[#fbcc0d] text-black"
                      }`}>
                        <p>{conv.question}</p>
                      </div>
                    </div>
                    
                    {/* AI Response Bubble (left aligned) */}
                    <div className="flex justify-start">
                      <div 
                        className={`max-w-[90%] rounded-lg py-3 px-4 ${
                          darkMode 
                            ? "bg-gray-800 text-white" 
                            : "bg-gray-100 text-black"
                        }`}
                        ref={index === conversations.length - 1 ? latestResponseRef : null}
                      >
                        {/* AI Header with Icon and Name */}
                        <div className={`flex items-center mb-3 -mx-4 -mt-3 px-4 py-2 ${
                          darkMode 
                            ? "bg-gray-600 rounded-t-lg" 
                            : "bg-gray-300 rounded-t-lg"
                        }`}>
                        <div className="w-12 h-12 rounded-full overflow-hidden mr-2">
                        <Image src="/person.JPG" alt="Rod Dixon"
                      width={50}
                      height={50}
                      className="rounded-full object-cover"
                    />
                        </div>
                        <span className="font-semibold">Rod Dixon</span>
                      </div>
                        
                        <div className="prose max-w-none">
                          <div className={darkMode ? "markdown-dark" : "markdown-light"}>
                            <ReactMarkdown>{conv.response.answer}</ReactMarkdown>
                          </div>
                        </div>
                        
                        {/* Sources Section */}
                        {conv.response.sources && conv.response.sources.length > 0 && (
                          <div className={`mt-3 pt-3 border-t ${darkMode ? "border-gray-700" : "border-gray-300"}`}>
                            <h4 className="text-xs uppercase font-semibold opacity-70 mb-1">Sources</h4>
                            <ul className="text-xs space-y-1 opacity-80">
                              {conv.response.sources.map((source, idx) => (
                                <li key={idx}>
                                  {source.source && source.source !== "None" ? (
                                    <a 
                                      href={source.source} 
                                      target="_blank" 
                                      rel="noopener noreferrer" 
                                      className={`hover:underline ${darkMode ? 'text-blue-300' : 'text-blue-600'}`}
                                    >
                                      {source.title || "Unknown Title"}
                                    </a>
                                  ) : (
                                    <span>{source.title || "Unknown Title"}</span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                
                {/* Loading bubble */}
                {isLoading && (
                  <div className="flex justify-start">
                    <div 
                      className={`max-w-[75%] rounded-lg py-3 px-4 ${
                        darkMode 
                          ? "bg-gray-800 text-white" 
                          : "bg-gray-100 text-black"
                      }`}
                      ref={latestResponseRef}
                    >
                      {/* AI Header with Icon and Name */}
                      <div className={`flex items-center mb-3 -mx-4 -mt-3 px-4 py-2 ${
                        darkMode 
                          ? "bg-gray-600 rounded-t-lg" 
                          : "bg-gray-300 rounded-t-lg"
                      }`}>
                        <div className="w-12 h-12 rounded-full overflow-hidden mr-2">
                        <Image src="/person.JPG" alt="Rod Dixon"
                      width={50}
                      height={50}
                      className="rounded-full object-cover"
                    />
                        </div>
                        <span className="font-semibold">Rod Dixon</span>
                      </div>
                      
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 rounded-full bg-current animate-bounce"></div>
                        <div className="w-2 h-2 rounded-full bg-current animate-bounce delay-100"></div>
                        <div className="w-2 h-2 rounded-full bg-current animate-bounce delay-200"></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Input for next question */}
            <div className={`sticky bottom-0 p-4 rounded-lg shadow-lg ${darkMode ? "bg-gray-800" : "bg-white"}`}>
              <form onSubmit={handleSubmit} className="flex items-center space-x-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Type your message..."
                  className={`flex-grow p-3 rounded-lg border ${
                    darkMode 
                      ? "bg-gray-700 text-white border-gray-600" 
                      : "bg-white text-black border-gray-300"
                  }`}
                  disabled={isLoading}
                />
                <button 
                  type="submit" 
                  className={`p-3 rounded-lg transition-colors text-white ${
                    darkMode
                      ? "bg-[#0a3683] hover:bg-[#0b4094]"
                      : "bg-[#04215a] hover:bg-[#03184a]"
                  } disabled:opacity-50`}
                  disabled={isLoading}
                >
                  {isLoading ? 
                    <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg> : 
                    <span>Send</span>
                  }
                </button>
              </form>
              {error && <div className="text-red-500 mt-2 text-sm">{error}</div>}
            </div>
          </div>
        )}
      </div>
      
      {/* Add custom CSS for markdown styling */}
      <style jsx global>{`
        .markdown-dark h1, .markdown-dark h2, .markdown-dark h3, 
        .markdown-dark h4, .markdown-dark h5, .markdown-dark h6 {
          color: #e2e8f0;
          margin-top: 1rem;
          margin-bottom: 0.5rem;
          font-weight: bold;
        }
        .markdown-dark h1 { font-size: 1.8rem; }
        .markdown-dark h2 { font-size: 1.5rem; }
        .markdown-dark h3 { font-size: 1.3rem; }
        
        .markdown-light h1, .markdown-light h2, .markdown-light h3,
        .markdown-light h4, .markdown-light h5, .markdown-light h6 {
          color: #1a202c;
          margin-top: 1rem;
          margin-bottom: 0.5rem;
          font-weight: bold;
        }
        .markdown-light h1 { font-size: 1.8rem; }
        .markdown-light h2 { font-size: 1.5rem; }
        .markdown-light h3 { font-size: 1.3rem; }
        
        .markdown-dark p, .markdown-light p {
          margin-bottom: 1rem;
        }
        
        .markdown-dark ul, .markdown-dark ol,
        .markdown-light ul, .markdown-light ol {
          padding-left: 2rem;
          margin-bottom: 1rem;
          list-style-type: disc;
        }
        
        .markdown-dark ol, .markdown-light ol {
          list-style-type: decimal;
        }
        
        .markdown-dark li, .markdown-light li {
          margin-bottom: 0.5rem;
          display: list-item;
        }
        
        .markdown-dark strong {
          color: rgb(255, 255, 255);
          font-weight: bold;
        }
        
        .markdown-light strong {
          color: rgb(0, 0, 0);
          font-weight: bold;
        }
        
        .markdown-dark code, .markdown-light code {
          font-family: monospace;
        }
        
        .markdown-dark code {
          background-color: #2d3748;
          padding: 0.2rem 0.4rem;
          border-radius: 0.25rem;
        }
        
        .markdown-light code {
          background-color: #edf2f7;
          padding: 0.2rem 0.4rem;
          border-radius: 0.25rem;
        }
        
        .delay-100 {
          animation-delay: 0.1s;
        }
        
        .delay-200 {
          animation-delay: 0.2s;
        }
        
        .whitespace-pre-wrap {
          white-space: pre-wrap;
        }
        
        /* Custom scrollbar */
        .scrollbar-thin::-webkit-scrollbar {
          width: 6px;
        }
        
        .scrollbar-thin::-webkit-scrollbar-track {
          background: transparent;
        }
        
        .scrollbar-thin::-webkit-scrollbar-thumb {
          background-color: rgba(156, 163, 175, 0.5);
          border-radius: 20px;
        }
      `}</style>
    </div>
  );
}