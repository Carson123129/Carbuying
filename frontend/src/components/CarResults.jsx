import { useState } from 'react'
import CarCard from './CarCard'
import './CarResults.css'

function CarResults({ matches, isLoading }) {
  const [expandedId, setExpandedId] = useState(null)

  if (isLoading) {
    return (
      <div className="car-results loading">
        <div className="results-header">
          <h2>Finding your matches...</h2>
        </div>
        <div className="loading-skeleton">
          {[1, 2, 3].map(i => (
            <div key={i} className="skeleton-card" />
          ))}
        </div>
      </div>
    )
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="car-results empty">
        <p>No matches found. Try a different search.</p>
      </div>
    )
  }

  const handleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id)
  }

  return (
    <div className="car-results">
      <div className="results-header">
        <h2>
          <span className="results-count">{matches.length}</span> cars match your criteria
        </h2>
      </div>
      
      <div className="results-list stagger-children">
        {matches.map((match, index) => (
          <CarCard
            key={match.car.id}
            match={match}
            rank={index + 1}
            isExpanded={expandedId === match.car.id}
            onExpand={() => handleExpand(match.car.id)}
          />
        ))}
      </div>
    </div>
  )
}

export default CarResults

