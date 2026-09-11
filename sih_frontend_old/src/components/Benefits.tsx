const BENEFITS = [
  {
    title: 'Early Distress Detection',
    description: 'Identify warning signs before they escalate into a mental health crisis.',
  },
  {
    title: 'Timely Counselling',
    description: 'Route high-risk cases straight to available, qualified counsellors.',
  },
  {
    title: 'Evidence-Based Insights',
    description: 'Ground every intervention in consistent, data-informed assessment.',
  },
  {
    title: 'Better Coordination',
    description: 'Keep victims, counsellors, and administrators aligned on next steps.',
  },
]

function Benefits() {
  return (
    <section className="benefits">
      <div className="container">
        <div className="section-head">
          <span className="section-eyebrow">Why Sahara</span>
          <h2 className="section-heading">Key benefits</h2>
        </div>

        <div className="benefits-grid">
          {BENEFITS.map((benefit) => (
            <div key={benefit.title} className="benefit-card">
              <span className="benefit-marker" aria-hidden="true" />
              <h3 className="benefit-title">{benefit.title}</h3>
              <p className="benefit-description">{benefit.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default Benefits
