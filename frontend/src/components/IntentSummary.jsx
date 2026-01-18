import './IntentSummary.css'

function IntentSummary({ summary, intent }) {
  return (
    <div className="intent-summary">
      <div className="intent-header">
        <span className="intent-icon">✦</span>
        <span className="intent-label">We understood:</span>
      </div>
      <p className="intent-text">{summary}</p>
      
      <div className="intent-details">
        {intent.budget_max && (
          <span className="intent-tag budget">
            <span className="tag-icon">$</span>
            Under ${intent.budget_max.toLocaleString()}
          </span>
        )}
        
        {intent.drivetrain && (
          <span className="intent-tag drivetrain">
            <span className="tag-icon">◎</span>
            {intent.drivetrain}
          </span>
        )}
        
        {intent.performance_priority > 0.6 && (
          <span className="intent-tag performance">
            <span className="tag-icon">⚡</span>
            Performance focused
          </span>
        )}
        
        {intent.reliability_priority > 0.6 && (
          <span className="intent-tag reliability">
            <span className="tag-icon">✓</span>
            Reliability matters
          </span>
        )}
        
        {intent.body_style && (
          <span className="intent-tag body">
            <span className="tag-icon">◇</span>
            {intent.body_style}
          </span>
        )}
        
        {intent.emotional_tags?.slice(0, 3).map((tag, i) => (
          <span key={i} className="intent-tag emotion">
            {tag}
          </span>
        ))}
        
        {intent.reference_car && (
          <span className="intent-tag reference">
            <span className="tag-icon">≈</span>
            Like {intent.reference_car}
          </span>
        )}
      </div>
    </div>
  )
}

export default IntentSummary

