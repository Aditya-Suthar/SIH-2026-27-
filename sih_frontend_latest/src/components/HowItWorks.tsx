const STEPS = [
  {
    number: '01',
    title: 'Report / Check-In',
    description:
      'A survivor submits a confidential check-in describing how they are feeling, either on their own or with assistance.',
  },
  {
    number: '02',
    title: 'AI Risk Assessment',
    description:
      'The platform analyses the check-in for early markers of distress and assigns a risk level for review.',
  },
  {
    number: '03',
    title: 'Counsellor Intervention',
    description:
      'A qualified counsellor is notified, reviews the case, and reaches out with the appropriate level of support.',
  },
]

function HowItWorks() {
  return (
    <section id="how-it-works" className="how-it-works">
      <div className="container">
        <div className="section-head">
          <span className="section-eyebrow">A simple, guided process</span>
          <h2 className="section-heading">How It Works</h2>
          <p className="section-subtext">
            From the first check-in to real human support, every step is designed to close the
            gap between distress and intervention.
          </p>
        </div>

        <div className="steps-grid">
          {STEPS.map((step, index) => (
            <div key={step.number} className="step-card">
              <span className="step-number">{step.number}</span>
              <h3 className="step-title">{step.title}</h3>
              <p className="step-description">{step.description}</p>
              {index < STEPS.length - 1 && <span className="step-connector" aria-hidden="true" />}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default HowItWorks
