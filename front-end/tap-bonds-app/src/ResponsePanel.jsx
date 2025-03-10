import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown'; // You'll need to install this package

const ResponsePanel = ({ isLoading, loadingMessage, response }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [isTyping, setIsTyping] = useState(false);

useEffect(() => {
    if (isLoading) {
      // Reset when loading starts
      setDisplayedContent('');
      setIsTyping(false);
    } else {
      // Begin typewriter effect with demo content when no response is available
      const content = response || 'No response available.';
      setIsTyping(true);
  
      // Simulate typing effect
      let i = 0;
      const typeSpeed = 10; // characters per interval
      const interval = setInterval(() => {
        setDisplayedContent(content?.substring(0, i));
        i += typeSpeed;
        
        if (i > content.length) {
          clearInterval(interval);
          setIsTyping(false);
        }
      }, 30);
  
      return () => clearInterval(interval);
    }
  }, [isLoading, response]);

  return (
    <div className="response-panel">
      {isLoading ? (
        <div className="loading-message">{loadingMessage}</div>
      ) : (
        <div className="markdown-content">
          <ReactMarkdown>{displayedContent}</ReactMarkdown>
          {isTyping && <span className="cursor-blink">|</span>}
        </div>
      )}
    </div>
  );
};

export default ResponsePanel;