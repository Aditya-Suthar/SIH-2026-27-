import { useState } from 'react'

const NAV_LINKS = ['Home', 'About', 'How It Works', 'Contact']

function Navbar() {
  const [open, setOpen] = useState(false)

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <a href="#home" className="navbar-logo">
          <span className="navbar-logo-mark" aria-hidden="true" />
          <span>
            Sahara<span className="navbar-logo-accent">.</span>
          </span>
        </a>

        <nav className={`navbar-links ${open ? 'is-open' : ''}`}>
          {NAV_LINKS.map((link) => (
            <a
              key={link}
              href={`#${link.toLowerCase().replace(/\s+/g, '-')}`}
              onClick={() => setOpen(false)}
            >
              {link}
            </a>
          ))}
          <button className="btn btn-primary navbar-login navbar-login-mobile">
            Login
          </button>
        </nav>

        <div className="navbar-actions">
          <button className="btn btn-primary navbar-login">Login</button>
          <button
            className="navbar-toggle"
            aria-label="Toggle navigation menu"
            aria-expanded={open}
            onClick={() => setOpen((prev) => !prev)}
          >
            <span />
            <span />
            <span />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Navbar
