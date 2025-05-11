import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';

const AnimatedChatResponse = ({ response, darkMode }) => {
  const [displayedText, setDisplayedText] = useState('');
  const textToAnimate = response || '';
  const intervalRef = useRef(null);
  const wordIndex = useRef(0);
  const fullTextRef = useRef('');
  
  // Reset animation when response changes
  useEffect(() => {
    // Store full text to ensure we have the complete response
    fullTextRef.current = textToAnimate;
    
    // Reset state
    setDisplayedText('');
    wordIndex.current = 0;
    
    // Clear any existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    if (!textToAnimate) return;

    // Instead of splitting by spaces, preserve line breaks and special characters
    // by processing one character at a time
    let currentIndex = 0;
    const totalLength = textToAnimate.length;
    
    // Set up the interval to add characters at a time
    intervalRef.current = setInterval(() => {
      if (currentIndex < totalLength) {
        // Add the next character
        setDisplayedText(prev => {
          return textToAnimate.substring(0, currentIndex + 1);
        });
        currentIndex++;
      } else {
        // Ensure we have the full text at the end
        setDisplayedText(textToAnimate);
        clearInterval(intervalRef.current);
      }
    }, 10); // Faster speed for character-by-character
    
    // Clean up on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [textToAnimate]);
  
  return (
    <div className="prose max-w-none">
      <div className={darkMode ? "markdown-dark" : "markdown-light"}>
        <ReactMarkdown>{displayedText}</ReactMarkdown>
      </div>
    </div>
  );
};

export default AnimatedChatResponse;