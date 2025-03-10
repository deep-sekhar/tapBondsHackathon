import React, { useState } from 'react';

const TopSearchBar = ({ onSearch, isSubmitted }) => {
  const [inputValue, setInputValue] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSearch(inputValue);
    }
  };

  return (
    <div className={`top-search-bar ${isSubmitted ? 'bar-top' : 'bar-center'}`}>
      <form onSubmit={handleSubmit} className="search-form">
        <input
          type="text"
          className="search-input"
          placeholder="Type a command or search…"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <button type="submit" className="search-button">
          Submit
        </button>
      </form>
    </div>
  );
};

export default Searchbar;
