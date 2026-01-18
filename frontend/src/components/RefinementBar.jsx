import './RefinementBar.css'

function RefinementBar({ suggestions, onRefine, isLoading }) {
  if (!suggestions || suggestions.length === 0) return null

  return (
    <div className="refinement-bar">
      <span className="refinement-label">Refine:</span>
      <div className="refinement-chips">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            className="refinement-chip"
            onClick={() => onRefine(suggestion)}
            disabled={isLoading}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}

export default RefinementBar

