import { useState, useRef, useEffect } from 'react'
import './SearchBox.css'

function SearchBox({ onSearch, isLoading, initialValue = '' }) {
  const [query, setQuery] = useState(initialValue)
  const inputRef = useRef(null)

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim() && !isLoading) {
      onSearch(query.trim())
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e)
    }
  }

  return (
    <form className="search-box" onSubmit={handleSubmit}>
      <div className="search-input-wrapper">
        <textarea
          ref={inputRef}
          className="search-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your perfect car..."
          rows={2}
          disabled={isLoading}
        />
        <div className="search-hint">
          Press Enter to search
        </div>
      </div>
      <button 
        type="submit" 
        className="search-btn"
        disabled={!query.trim() || isLoading}
      >
        {isLoading ? (
          <span className="search-loading">
            <span className="dot"></span>
            <span className="dot"></span>
            <span className="dot"></span>
          </span>
        ) : (
          <>
            <span className="search-icon">→</span>
            <span className="search-text">Find Cars</span>
          </>
        )}
      </button>
    </form>
  )
}

export default SearchBox

