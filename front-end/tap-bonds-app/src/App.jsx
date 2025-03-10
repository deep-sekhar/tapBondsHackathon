import { useState, useEffect } from 'react';
import './App.css';
import ResponsePanel from './ResponsePanel';

function App() {
  const [query, setQuery] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [currentMessageIndex, setCurrentMessageIndex] = useState(0);
  const [isClosing, setIsClosing] = useState(false);
  /// Ensure this is defined:
  const [isExpanded, setIsExpanded] = useState(false);

  const handleIconClick = () => {
    setIsExpanded((prev) => !prev);
  };

  const loadingMessages = [
    'Analyzing your query...',
    'Fetching the informati you asked for ...',
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

  // Simulate an API call
  const fetchResults = async (userQuery) => {
    try {
      // Simulate 5-second delay
      await new Promise((resolve) => setTimeout(resolve, 5000));

      const data = `
# Bond Analysis Results

## Recommendations

Here are the top bonds based on your query:

- **HDFC Bank**: AAA rated, 7.85% coupon, matures in 2026
- **SBI**: AAA rated, 8.15% coupon, matures in 2025
- **Reliance Industries**: AA+ rated, 6.95% coupon, matures in 2027

## Performance Metrics

| Issuer | YTM  | Duration | Credit Rating |
|--------|------|----------|--------------|
| HDFC   | 8.2% | 3.5 yrs  | AAA          |
| SBI    | 8.5% | 2.8 yrs  | AAA          |
| RIL    | 7.3% | 4.2 yrs  | AA+          |

## Summary

Based on your requirements, HDFC Bank bonds offer the best balance of yield and safety.
`;

      // real query from fastAPI running on uvicorn on port 8000
      const params = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: userQuery })
      }
      const res = await fetch('http://localhost:8000/query', params);
      if(res.ok) {
        const resdata = await res.json();
        console.log(resdata);
        setResponse(resdata?.response?.response);
      } else {
        console.log("Data correupted");
      }

      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching results:', error);
      setIsLoading(false);
      setResponse('Failed to fetch data');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      // If results are already shown, animate them away first
      if (isSubmitted && response) {
        setIsClosing(true);
        setTimeout(() => {
          setIsSubmitted(true);
          setIsLoading(true);
          setResponse(null);
          setIsClosing(false);
          fetchResults(query);
        }, 800);
      } else {
        setIsSubmitted(true);
        setIsLoading(true);
        setResponse(null);
        fetchResults(query);
      }
    }
  };

  return (
    <div className="app">
      <form
        onSubmit={handleSubmit}
        className={`search-bar ${isSubmitted ? 'search-bar-top' : 'search-bar-center'} ${isExpanded ? 'expanded' : ''}`}
      >
        <i className="fa-solid fa-magnifying-glass search-icon" onClick={handleIconClick}></i>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for your favorite Bonds information..."
        />
      </form>


      {isSubmitted && (
        <div className={`results-card ${isClosing ? 'results-card-exit' : 'results-card-enter'}`}>
          {isLoading ? (
            <div className="loading">
              {/* <div className="loading-icon">
                <i className="fa-solid fa-magnifying-glass"></i>
              </div> */}
              <p style={{ color: '#f5f5f5' }}>{loadingMessages[currentMessageIndex]}</p>
            </div>
          ) : (
            <ResponsePanel
              isLoading={isLoading}
              loadingMessage={loadingMessages[currentMessageIndex]}
              response={response}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default App;
