function Hero() {
  return (
    <section id="home" className="hero">
      <div className="container hero-inner">
        <div className="hero-copy">
          <span className="section-eyebrow">AI-Powered Early Intervention</span>
          <h1 className="hero-heading">
            Detecting distress early, <span className="hero-heading-accent">before</span> it
            becomes a crisis
          </h1>
          <p className="hero-subtext">
            Sahas helps identify early signs of psychological distress in survivors of
            atrocities and connects them with the right counsellor at the right time — backed
            by responsible AI and monitored by trained professionals.
          </p>
          <div className="hero-actions">
            <a href="/login" className="btn btn-primary">
              Get Support
            </a>
            <a href="#how-it-works" className="btn btn-secondary">
              Learn More
            </a>
          </div>

          <div className="hero-trust">
            <div className="hero-trust-item">
              <strong>At your pace</strong>
              <span>Private check-ins</span>
            </div>
            <div className="hero-trust-divider" />
            <div className="hero-trust-item">
              <strong>Human + AI</strong>
              <span>For counsellor review</span>
            </div>
            <div className="hero-trust-divider" />
            <div className="hero-trust-item">
              <strong>Private</strong>
              <span>Data handled securely</span>
            </div>
          </div>
        </div>

        <div className="hero-visual" aria-hidden="true">
          <div className="hero-card hero-card-main">
            <div className="hero-card-header">
              <div>
                <span className="hero-card-title">Illustrative interface</span>
                <span className="hero-card-subtitle">Sample data · not live results</span>
              </div>
              <span className="hero-card-badge">Stable</span>
            </div>

            <div className="hero-gauge">
              <svg viewBox="0 0 120 70" className="hero-gauge-svg">
                <path
                  d="M10 65 A50 50 0 0 1 110 65"
                  fill="none"
                  stroke="#e3e8f2"
                  strokeWidth="10"
                  strokeLinecap="round"
                />
                <path
                  d="M10 65 A50 50 0 0 1 90 22"
                  fill="none"
                  stroke="#0f9e94"
                  strokeWidth="10"
                  strokeLinecap="round"
                />
              </svg>
              <div className="hero-gauge-label">
                <strong>Low Risk</strong>
                <span>Risk Index: 22%</span>
              </div>
            </div>

            <div className="hero-bars">
              {[38, 62, 45, 70, 52, 30, 48].map((height, index) => (
                <span
                  key={index}
                  className="hero-bar"
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
            <div className="hero-bars-caption">
              <span>Mon</span>
              <span>Tue</span>
              <span>Wed</span>
              <span>Thu</span>
              <span>Fri</span>
              <span>Sat</span>
              <span>Sun</span>
            </div>
          </div>

          <div className="hero-card hero-card-float hero-card-float-1">
            <span className="hero-dot hero-dot-teal" />
            <div>
              <strong>Check-in received</strong>
              <span>Available for review</span>
            </div>
          </div>

          <div className="hero-card hero-card-float hero-card-float-2">
            <span className="hero-dot hero-dot-violet" />
            <div>
              <strong>Session scheduled</strong>
              <span>Today, 4:30 PM</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Hero
