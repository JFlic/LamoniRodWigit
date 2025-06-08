"use client";

import { useState, useRef, useEffect } from "react";
import Image from "next/image";
import AnimatedChatResponse from "./components/AnimatedChatResponse";

// Language translations
const translations = {
  en: {
    title: "Hi I'm Rod Dixon, what do you want to know about your town?",
    placeholder: "Enter your question",
    askButton: "Ask Question",
    loading: "Loading...",
    darkMode: "Dark Mode 🌙",
    lightMode: "Light Mode 🌞",
    sources: "Sources",
    send: "Send",
    typeMessage: "Type your message...",
    uploadButton: "Upload Documents",
    uploadTitle: "Upload Documents to Knowledge Base",
    dragDropText: "Drag and drop files here, or click to select files",
    uploadSuccess: "Files uploaded successfully!",
    uploadError: "Error uploading files. Please try again.",
    close: "Close",
    category: "Category",
    selectCategory: "Select a category...",
    login: "Login",
    email: "Email",
    password: "Password",
    loginError: "Invalid email or password",
    loginSuccess: "Login successful",
    logout: "Logout",
    loginRequired: "Please login to upload documents",
  },
  es: {
    title: "Hola, soy Rod Dixon, ¿qué quieres saber sobre tu ciudad?",
    placeholder: "Ingresa tu pregunta",
    askButton: "Hacer Pregunta",
    loading: "Cargando...",
    darkMode: "Modo Oscuro 🌙",
    lightMode: "Modo Claro 🌞",
    sources: "Fuentes",
    send: "Enviar",
    typeMessage: "Escribe tu mensaje...",
    uploadButton: "Subir Documentos",
    uploadTitle: "Subir Documentos a la Base de Conocimientos",
    dragDropText: "Arrastra y suelta archivos aquí, o haz clic para seleccionar archivos",
    uploadSuccess: "¡Archivos subidos con éxito!",
    uploadError: "Error al subir archivos. Por favor, inténtalo de nuevo.",
    close: "Cerrar",
    category: "Categoría",
    selectCategory: "Selecciona una categoría...",
    login: "Iniciar sesión",
    email: "Correo electrónico",
    password: "Contraseña",
    loginError: "Correo electrónico o contraseña inválidos",
    loginSuccess: "Inicio de sesión exitoso",
    logout: "Cerrar sesión",
    loginRequired: "Por favor inicie sesión para subir documentos",
  }
};

// Common questions in both languages
const commonQuestionsTranslations = {
  en: [
    "What are some things to do in Lamoni?",
    "Tell me about the enactus room stats",
    "When is Lamoni's spring yard sale?",
    "Do I have to register my dog?"
  ],
  es: [
    "¿Qué hay para hacer en Lamoni?",
    "Dime las estadísticas de la Sala Enactus",
    "¿Cuándo es la venta de garaje de primavera de Lamoni?",
    "¿Tengo que registrar a mi perro?"
  ]
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [conversations, setConversations] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [darkMode, setDarkMode] = useState(false);
  const [language, setLanguage] = useState("en"); // Default language is English
  const [loadingMessage, setLoadingMessage] = useState(""); // Added for dynamic loading message
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("");
  const latestResponseRef = useRef(null); // Reference for the latest AI response
  const fileInputRef = useRef(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authToken, setAuthToken] = useState(null);
  const [loginError, setLoginError] = useState(null);

  // Get translations based on current language
  const t = translations[language];
  const commonQuestions = commonQuestionsTranslations[language];

  // Backend URL configuration
  const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL_PROD || 'https://questionroddixon.com';

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

  // useEffect for dynamic loading message
  useEffect(() => {
    let timer;
    if (isLoading) {
      // Reset message immediately when loading starts
      setLoadingMessage(""); 
      timer = setTimeout(() => {
        // Check if still loading after 4 seconds
        if (isLoading) { 
          setLoadingMessage("Checking database");
        }
      }, 4000);
    } else {
      setLoadingMessage(""); // Clear message when not loading
    }

    return () => clearTimeout(timer); // Cleanup timer on unmount or if isLoading changes
  }, [isLoading]);

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
        credentials: 'include',
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

  // Toggle language between English and Spanish
  const toggleLanguage = () => {
    setLanguage(prevLang => prevLang === "en" ? "es" : "en");
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError(null);

    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch(`${BACKEND_URL}/query/token`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      setAuthToken(data.access_token);
      setShowLoginModal(false);
      setEmail("");
      setPassword("");
      setLoginError(null);
    } catch (err) {
      console.error('Login error:', err);
      setLoginError(t.loginError);
    }
  };

  const handleFileUpload = async (files) => {
    if (!authToken) {
      setShowLoginModal(true);
      return;
    }

    if (!selectedCategory) {
      setUploadStatus({ type: 'error', message: 'Please select a category first' });
      return;
    }

    const formData = new FormData();
    Array.from(files).forEach(file => {
      formData.append('files', file);
    });
    formData.append('category', selectedCategory);

    try {
      const response = await fetch(`${BACKEND_URL}/query/query/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
        credentials: 'include',
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          setAuthToken(null);
          setShowLoginModal(true);
          throw new Error('Session expired. Please login again.');
        }
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
      }

      const result = await response.json();
      setUploadStatus({ type: 'success', message: result.message || t.uploadSuccess });
      setUploadedFiles([]);
      setSelectedCategory("");
      setTimeout(() => setShowUploadModal(false), 2000);
    } catch (err) {
      console.error('Upload error:', err);
      setUploadStatus({ type: 'error', message: err.message || t.uploadError });
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    setUploadedFiles(Array.from(files));
  };

  const handleFileSelect = (e) => {
    const files = e.target.files;
    setUploadedFiles(Array.from(files));
  };

  const handleLogout = () => {
    setAuthToken(null);
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
        {darkMode ? t.lightMode : t.darkMode}
      </button>

      {/* Language Toggle Button */}
      <button
        onClick={toggleLanguage}
        className={`fixed top-16 left-4 p-2 rounded-lg shadow-md transition ${
          darkMode 
            ? "bg-gray-700 text-white hover:bg-gray-600" 
            : "bg-gray-200 text-black hover:bg-gray-300"
        }`}
      >
        {language === "en" ? "Español" : "English"}
      </button>

      {/* Login Modal */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className={`w-full max-w-md p-6 rounded-lg shadow-xl ${
            darkMode ? "bg-gray-800" : "bg-white"
          }`}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">{t.login}</h2>
              <button
                onClick={() => {
                  setShowLoginModal(false);
                  setLoginError(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block mb-2">{t.email}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={`w-full p-2 rounded border ${
                    darkMode 
                      ? "bg-gray-700 border-gray-600" 
                      : "bg-white border-gray-300"
                  }`}
                  required
                />
              </div>

              <div>
                <label className="block mb-2">{t.password}</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={`w-full p-2 rounded border ${
                    darkMode 
                      ? "bg-gray-700 border-gray-600" 
                      : "bg-white border-gray-300"
                  }`}
                  required
                />
              </div>

              {loginError && (
                <div className="text-red-500 text-sm">{loginError}</div>
              )}

              <button
                type="submit"
                className={`w-full p-2 rounded text-white ${
                  darkMode
                    ? "bg-[#2757a3] hover:bg-[#1e437d]"
                    : "bg-[#04215a] hover:bg-[#03184a]"
                }`}
              >
                {t.login}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Modify Upload Button to show login/logout state */}
      <button
        onClick={() => authToken ? setShowUploadModal(true) : setShowLoginModal(true)}
        className={`fixed top-4 right-4 p-2 rounded-lg shadow-md transition ${
          darkMode 
            ? "bg-[#2757a3] text-white hover:bg-[#1e437d]" 
            : "bg-[#fbcc0d] text-black hover:bg-[#eabd0c]"
        }`}
      >
        {authToken ? t.uploadButton : t.login}
      </button>

      {/* Add Logout Button when logged in */}
      {authToken && (
        <button
          onClick={handleLogout}
          className={`fixed top-16 right-4 p-2 rounded-lg shadow-md transition ${
            darkMode 
              ? "bg-gray-700 text-white hover:bg-gray-600" 
              : "bg-gray-200 text-black hover:bg-gray-300"
          }`}
        >
          {t.logout}
        </button>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className={`w-full max-w-2xl p-6 rounded-lg shadow-xl ${
            darkMode ? "bg-gray-800" : "bg-white"
          }`}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">{t.uploadTitle}</h2>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadedFiles([]);
                  setUploadStatus(null);
                  setSelectedCategory("");
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            {/* Category Selection */}
            <div className="mb-4">
              <label className="block mb-2">{t.category}</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className={`w-full p-2 rounded border ${
                  darkMode 
                    ? "bg-gray-700 border-gray-600" 
                    : "bg-white border-gray-300"
                }`}
              >
                <option value="">{t.selectCategory}</option>
                <option value="events">Events</option>
                <option value="services">Services</option>
                <option value="information">General Information</option>
              </select>
            </div>

            {/* Drag and Drop Area */}
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragging
                  ? "border-[#2757a3] bg-blue-50"
                  : darkMode
                  ? "border-gray-600 hover:border-gray-500"
                  : "border-gray-300 hover:border-gray-400"
              }`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                type="file"
                multiple
                ref={fileInputRef}
                onChange={handleFileSelect}
                className="hidden"
                accept=".pdf,.docx,.md"
              />
              <p>{t.dragDropText}</p>
              {uploadedFiles.length > 0 && (
                <div className="mt-4">
                  <p className="font-semibold">Selected files:</p>
                  <ul className="mt-2">
                    {uploadedFiles.map((file, index) => (
                      <li key={index} className="text-sm">
                        {file.name}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Upload Status */}
            {uploadStatus && (
              <div className={`mt-4 p-3 rounded ${
                uploadStatus.type === 'success' 
                  ? 'bg-green-100 text-green-700' 
                  : 'bg-red-100 text-red-700'
              }`}>
                {uploadStatus.message}
              </div>
            )}

            {/* Upload Button */}
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setUploadedFiles([]);
                  setUploadStatus(null);
                  setSelectedCategory("");
                }}
                className={`px-4 py-2 rounded ${
                  darkMode 
                    ? "bg-gray-700 hover:bg-gray-600" 
                    : "bg-gray-200 hover:bg-gray-300"
                }`}
              >
                {t.close}
              </button>
              <button
                onClick={() => handleFileUpload(uploadedFiles)}
                disabled={uploadedFiles.length === 0 || !selectedCategory}
                className={`px-4 py-2 rounded text-white ${
                  uploadedFiles.length === 0 || !selectedCategory
                    ? "bg-gray-400 cursor-not-allowed"
                    : darkMode
                    ? "bg-[#2757a3] hover:bg-[#1e437d]"
                    : "bg-[#04215a] hover:bg-[#03184a]"
                }`}
              >
                {t.uploadButton}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col items-center justify-center min-h-screen">
        {conversations.length === 0 ? (
          <div className="w-full max-w-2xl px-4">
            {/* Large Rod Dixon Icon */}
            <div className="flex justify-center mb-6">
              <div className="w-42 h-42 rounded-full overflow-hidden border-4 border-[#fbcc0d] shadow-lg">
                <Image 
                  src="/rodicon.png" 
                  alt="Rod Dixon"
                  width={200}
                  height={200}
                  className="object-cover"
                />
              </div>
            </div>
            
            <h1 className="text-3xl font-bold text-center mb-8">
              {t.title}
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
                  placeholder={t.placeholder}
                  className={`w-full p-4 rounded-lg border ${
                    darkMode 
                      ? "bg-gray-700 text-white border-gray-600" 
                      : "bg-white text-black border-gray-300"
                  }`}
                  disabled={isLoading}
                />
                <button 
                  type="submit" 
                  className={`w-full p-4 rounded-lg transition-colors text-white flex items-center justify-center ${
                    darkMode
                      ? "bg-[#0a3683] hover:bg-[#0b4094]"
                      : "bg-[#04215a] hover:bg-[#03184a]"
                  }`}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    t.askButton
                  )}
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
                            <Image src="/rodicon.png" alt="Rod Dixon"
                              width={50}
                              height={50}
                              className="rounded-full object-cover"
                            />
                          </div>
                          <span className="font-semibold">Rod Dixon</span>
                        </div>
                        
                        {/* Animated Chat Response Component */}
                        <AnimatedChatResponse 
                          response={conv.response.answer} 
                          darkMode={darkMode} 
                        />
                        
                        {/* Sources Section */}
                        {conv.response.sources && conv.response.sources.length > 0 && (
                          <div className={`mt-3 pt-3 border-t ${darkMode ? "border-gray-700" : "border-gray-300"}`}>
                            <h4 className="text-xs uppercase font-semibold opacity-70 mb-1">{t.sources}</h4>
                            <ul className="text-xs space-y-1 opacity-80">
                              {conv.response.sources.map((source, idx) => (
                                <li key={idx}>
                                  {source.source && source.source !== "None" ? (
                                    <a 
                                      href={source.url} 
                                      target="_blank" 
                                      rel="noopener noreferrer" 
                                      className={`hover:underline ${darkMode ? 'text-blue-300' : 'text-blue-600'}`}
                                    >
                                      {source.heading || "Private Information"}
                                    </a>
                                  ) : (
                                    <span>{source.heading || "Private Information"}</span>
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
                          <Image src="/rodicon.png" alt="Rod Dixon"
                            width={50}
                            height={50}
                            className="rounded-full object-cover"
                          />
                        </div>
                        <span className="font-semibold">Rod Dixon</span>
                      </div>
                      
                      <div className="flex flex-col items-center py-2"> {/* Wrapper for dots and message */}
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 rounded-full bg-current animate-bounce"></div>
                          <div className="w-2 h-2 rounded-full bg-current animate-bounce delay-100"></div>
                          <div className="w-2 h-2 rounded-full bg-current animate-bounce delay-200"></div>
                        </div>
                        {loadingMessage && <p className="mt-2 text-xs opacity-75">{loadingMessage}</p>}
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
                  placeholder={t.typeMessage}
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
                  {isLoading ? (
                    <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  ) : (
                    <span>{t.send}</span>
                  )}
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