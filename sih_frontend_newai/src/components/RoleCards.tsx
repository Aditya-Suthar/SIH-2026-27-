const ROLES = [
  {
    tag: 'Victim',
    title: 'For Victims',
    description:
      'Check in privately, share how you feel, and get connected to support the moment it matters.',
    accent: 'role-accent-blue',
  },
  {
    tag: 'Counsellor',
    title: 'For Counsellors',
    description:
      'View AI-flagged risk cases, prioritise outreach, and track survivor progress over time.',
    accent: 'role-accent-teal',
  },
  {
    tag: 'Government / Admin',
    title: 'For Government & Admins',
    description:
      'Monitor regional trends, allocate resources, and measure the impact of intervention programs.',
    accent: 'role-accent-violet',
  },
]

function RoleCards() {
  return (
    <section id="about" className="roles">
      <div className="container">
        <div className="section-head">
          <span className="section-eyebrow">Built for everyone involved</span>
          <h2 className="section-heading">One platform, three roles</h2>
          <p className="section-subtext">
            Sahara brings survivors, counsellors, and administrators onto a single, secure
            system designed around timely, evidence-based mental health support.
          </p>
        </div>

        <div className="role-grid">
          {ROLES.map((role) => (
            <div key={role.tag} className="role-card">
              <span className={`role-icon ${role.accent}`} aria-hidden="true" />
              <span className="role-tag">{role.tag}</span>
              <h3 className="role-title">{role.title}</h3>
              <p className="role-description">{role.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default RoleCards
