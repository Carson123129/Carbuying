import './CarCard.css'

function CarCard({ match, rank, isExpanded, onExpand }) {
  const { car, match_score, match_reasons, tradeoffs, listings } = match

  const getScoreColor = (score) => {
    if (score >= 85) return 'excellent'
    if (score >= 75) return 'great'
    if (score >= 65) return 'good'
    if (score >= 50) return 'fair'
    return 'low'
  }

  const formatPrice = (price) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(price)
  }

  return (
    <div className={`car-card ${isExpanded ? 'expanded' : ''}`}>
      <div className="car-card-main" onClick={onExpand}>
        <div className="car-rank">#{rank}</div>
        
        <div className="car-info">
          <div className="car-title-row">
            <h3 className="car-title">
              {car.year} {car.make} {car.model}
              <span className="car-trim">{car.trim}</span>
            </h3>
          </div>
          
          <div className="car-specs">
            <span className="spec">
              <span className="spec-value">{car.power_hp}</span>
              <span className="spec-label">hp</span>
            </span>
            <span className="spec-divider">·</span>
            <span className="spec">
              <span className="spec-value">{car.zero_to_sixty}s</span>
              <span className="spec-label">0-60</span>
            </span>
            <span className="spec-divider">·</span>
            <span className="spec">
              <span className="spec-value">{car.drivetrain}</span>
            </span>
            <span className="spec-divider">·</span>
            <span className="spec price">
              ~{formatPrice(car.avg_price)}
            </span>
          </div>

          {match_reasons.length > 0 && (
            <div className="car-reasons">
              {match_reasons.slice(0, 2).map((reason, i) => (
                <span key={i} className="reason-tag">
                  <span className="reason-icon">✓</span>
                  {reason}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="car-score-area">
          <div className={`score-circle ${getScoreColor(match_score)}`}>
            <span className="score-value">{Math.round(match_score)}</span>
            <span className="score-label">match</span>
          </div>
          <button className="expand-btn">
            <span className={`expand-icon ${isExpanded ? 'rotated' : ''}`}>▾</span>
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="car-card-details animate-fade-in">
          <div className="details-grid">
            <div className="details-section">
              <h4>Full Specs</h4>
              <div className="specs-grid">
                <div className="spec-item">
                  <span className="spec-name">Power</span>
                  <span className="spec-val">{car.power_hp} hp</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">Torque</span>
                  <span className="spec-val">{car.torque_lb_ft} lb-ft</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">0-60 mph</span>
                  <span className="spec-val">{car.zero_to_sixty}s</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">Drivetrain</span>
                  <span className="spec-val">{car.drivetrain}</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">Body</span>
                  <span className="spec-val">{car.body_type}</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">MPG</span>
                  <span className="spec-val">{car.fuel_economy_mpg}</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">Reliability</span>
                  <span className="spec-val">{car.reliability_score}/10</span>
                </div>
                <div className="spec-item">
                  <span className="spec-name">Ownership Cost</span>
                  <span className="spec-val">{car.ownership_cost_score}/10</span>
                </div>
              </div>
            </div>

            <div className="details-section">
              <h4>Character</h4>
              <div className="tags-container">
                {car.emotional_tags.map((tag, i) => (
                  <span key={i} className="char-tag">{tag}</span>
                ))}
                {car.driving_feel_tags.map((tag, i) => (
                  <span key={i} className="feel-tag">{tag}</span>
                ))}
              </div>
            </div>

            {tradeoffs.length > 0 && (
              <div className="details-section tradeoffs">
                <h4>Tradeoffs</h4>
                <ul className="tradeoffs-list">
                  {tradeoffs.map((tradeoff, i) => (
                    <li key={i}>{tradeoff}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {listings && listings.length > 0 && (
            <div className="listings-section">
              <h4>Available Listings</h4>
              <div className="listings-grid">
                {listings.map((listing, i) => (
                  <a 
                    key={i} 
                    href={listing.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="listing-card"
                  >
                    <div className="listing-price">
                      {formatPrice(listing.price)}
                    </div>
                    <div className="listing-details">
                      <span className="listing-mileage">{listing.mileage.toLocaleString()} mi</span>
                      <span className="listing-divider">·</span>
                      <span className="listing-location">{listing.location}</span>
                    </div>
                    <div className="listing-condition">{listing.condition}</div>
                    <div className="listing-source">{listing.source} →</div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default CarCard


