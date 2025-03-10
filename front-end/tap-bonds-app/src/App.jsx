import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [query, setQuery] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);

  const loadingMessages = [
    'Analyzing your query...',
    'Fetching the most appropriate response...',
    'Almost there...'
  ];

  // Rotate loading messages every 2 seconds
  useEffect(() => {
    if (isLoading) {
      const interval = setInterval(() => {
        setCurrentMessageIndex((prev) => (prev + 1) % loadingMessages.length);
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      setIsSubmitted(true);
      setIsLoading(true);
      setResponse(null); // Reset previous response

      // Simulate API call (replace with real fetch if you have a backend)
      setTimeout(() => {
        const mockResponse = {
          title: `# ${query}`,
          message: 'NO TAGS FOUND',
          description: `"${query}" did not match any tags currently used in projects. Please try again or create a new tag.`
        };
        setResponse(mockResponse);
        setIsLoading(false);
      }, 3000); // Simulate 3-second fetch delay
    }
  };

  return (
    <div className="app">
      <form
        onSubmit={handleSubmit}
        className={`search-bar ${isSubmitted ? 'search-bar-top' : 'search-bar-center'}`}
      >
        <div className="search-icon">#</div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Type a command or search"
        />
        <div className="grid-icon">#</div>
      </form>
      {isSubmitted && (
        <div className="results-card">
          {isLoading ? (
            <div className="loading">
              <div className="loading-icon">#</div>
              <p>{loadingMessages[currentMessageIndex]}</p>
            </div>
          ) : (
            <div className="results-content">
              <div className="results-header">
                <div className="search-icon">#</div>
                <span>{response.title}</span>
                <div className="grid-icon">#</div>
              </div>
              <div className="results-body">
                <div className="results-icon">#</div>
                <h2>{response.message}</h2>
                <p>{response.description}</p>
                <button className="clear-search">Clear search</button>
              </div>
            </div>
          )}
        </div>
      )}
      <div className="bottom-nav">
        <div className="nav-item"># tags</div>
        <div className="nav-item">↑ navigate</div>
        <div className="nav-item">↓ navigate</div>
        <div className="nav-item">→ open</div>
        <div className="nav-item">esc close</div>
        <div className="nav-item">← parent</div>
      </div>
    </div>
  );
}

export default App;