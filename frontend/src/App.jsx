import { useState, useCallback } from 'react'
import SearchBox from './components/SearchBox'
import IntentSummary from './components/IntentSummary'
import CarResults from './components/CarResults'
import RefinementBar from './components/RefinementBar'
import './App.css'

function App() {
  const [searchState, setSearchState] = useState({
    query: '',
    isLoading: false,
    results: null,
    error: null
  })

  const handleSearch = useCallback(async (query) => {
    if (!query.trim()) return

    setSearchState(prev => ({
      ...prev,
      query,
      isLoading: true,
      error: null
    }))

    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })

      if (!response.ok) {
        throw new Error('Search failed')
      }

      const data = await response.json()
      setSearchState(prev => ({
        ...prev,
        isLoading: false,
        results: data
      }))
    } catch (err) {
      setSearchState(prev => ({
        ...prev,
        isLoading: false,
        error: 'Something went wrong. Make sure the backend is running.'
      }))
    }
  }, [])

  const handleRefine = useCallback(async (refinement) => {
    if (!searchState.results) return

    setSearchState(prev => ({
      ...prev,
      isLoading: true,
      error: null
    }))

    try {
      const response = await fetch('/api/refine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          original_query: searchState.query,
          previous_intent: searchState.results.interpreted_intent,
          refinement
        })
      })

      if (!response.ok) {
        throw new Error('Refinement failed')
      }

      const data = await response.json()
      setSearchState(prev => ({
        ...prev,
        isLoading: false,
        results: data
      }))
    } catch (err) {
      setSearchState(prev => ({
        ...prev,
        isLoading: false,
        error: 'Refinement failed. Please try again.'
      }))
    }
  }, [searchState.results, searchState.query])

  const handleReset = useCallback(() => {
    setSearchState({
      query: '',
      isLoading: false,
      results: null,
      error: null
    })
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo" onClick={handleReset}>
          <span className="logo-icon">◈</span>
          <span className="logo-text">FindingMyCar</span>
        </div>
        {searchState.results && (
          <button className="reset-btn" onClick={handleReset}>
            New Search
          </button>
        )}
      </header>

      <main className="app-main">
        {!searchState.results ? (
          <div className="hero-section">
            <div className="hero-content">
              <h1 className="hero-title">
                Find your car.
                <br />
                <span className="hero-accent">Just describe what you want.</span>
              </h1>
              <p className="hero-subtitle">
                No filters. No dropdowns. Just tell us what matters to you.
              </p>
              <SearchBox 
                onSearch={handleSearch} 
                isLoading={searchState.isLoading}
              />
              <div className="hero-examples">
                <span className="examples-label">Try:</span>
                <button 
                  className="example-chip"
                  onClick={() => handleSearch("Something like a BMW 340i but cheaper, AWD, still fast, under 35k, not boring")}
                >
                  "Like a BMW 340i but cheaper"
                </button>
                <button 
                  className="example-chip"
                  onClick={() => handleSearch("Fast but reliable under 30k")}
                >
                  "Fast but reliable under 30k"
                </button>
                <button 
                  className="example-chip"
                  onClick={() => handleSearch("Good in snow, still exciting, under 40k")}
                >
                  "Good in snow, still exciting"
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="results-section stagger-children">
            <IntentSummary 
              summary={searchState.results.intent_summary}
              intent={searchState.results.interpreted_intent}
            />
            
            <RefinementBar 
              suggestions={searchState.results.suggestions}
              onRefine={handleRefine}
              isLoading={searchState.isLoading}
            />
            
            <CarResults 
              matches={searchState.results.matches}
              isLoading={searchState.isLoading}
            />
          </div>
        )}

        {searchState.error && (
          <div className="error-message animate-fade-in">
            <span className="error-icon">⚠</span>
            {searchState.error}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>
          An intent-to-reality engine. Built to understand what you actually want.
          <span className="footer-domain">findingmycar.com</span>
        </p>
      </footer>
    </div>
  )
}

export default App

