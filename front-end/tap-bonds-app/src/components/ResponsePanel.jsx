import React, { useEffect, useState } from 'react';

function parseMarkdownLine(line) {
  if (line.startsWith('# ')) {
    return <h1 key={line}>{line.slice(2)}</h1>;
  } else if (line.startsWith('## ')) {
    return <h2 key={line}>{line.slice(3)}</h2>;
  } else if (line.startsWith('- ')) {
    return <li key={line}>{line.slice(2)}</li>;
  } else {
    return <p key={line}>{line}</p>;
  }
}

const ResponsePanel = ({ isLoading, loadingMessage, response }) => {
  const [responseLines, setResponseLines] = useState([]);
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    // Reset on each new query
    setResponseLines([]);
    setVisibleLines(0);

    if (!isLoading && response) {
      // Parse the response into lines
      const lines = response.split('\n').map(parseMarkdownLine);
      setResponseLines(lines);

      // Reveal lines one by one
      let index = 0;
      const interval = setInterval(() => {
        if (index < lines.length) {
          setVisibleLines((prev) => prev + 1);
          index++;
        } else {
          clearInterval(interval);
        }
      }, 400);
    }
  }, [isLoading, response]);

  return (
    <div className="response-panel">
      {isLoading ? (
        <div className="loading-message">{loadingMessage}</div>
      ) : (
        responseLines.slice(0, visibleLines).map((line, idx) => (
          <div key={idx} className="line-fade">{line}</div>
        ))
      )}
    </div>
  );
};

export default ResponsePanel;
