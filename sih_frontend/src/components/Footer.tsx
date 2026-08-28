function Footer() {
  return (
    <footer id="contact" className="footer">
      <div className="container footer-inner">
        <div className="footer-brand">
          <a href="#home" className="navbar-logo footer-logo">
            <span className="navbar-logo-mark" aria-hidden="true" />
            <span>
              Sahara<span className="navbar-logo-accent">.</span>
            </span>
          </a>
          <p className="footer-tagline">
            AI-assisted mental health monitoring and distress prediction for survivors of
            atrocities — built for SIH 2026.
          </p>
        </div>

        <div className="footer-links">
          <div className="footer-column">
            <h4>Platform</h4>
            <a href="#home">Home</a>
            <a href="#about">About</a>
            <a href="#how-it-works">How It Works</a>
          </div>
          <div className="footer-column">
            <h4>Support</h4>
            <a href="#contact">Contact</a>
            <a href="#get-support">Get Support</a>
          </div>
          <div className="footer-column">
            <h4>Contact</h4>
            <a href="mailto:support@sahara.gov.in">support@sahara.gov.in</a>
            <span className="footer-static">Helpline: 1800-XXX-XXXX</span>
          </div>
        </div>
      </div>

      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} Sahara. Smart India Hackathon.</span>
        <span>Built with care for those who need it most.</span>
      </div>
    </footer>
  )
}

export default Footer
