import { useState } from "react"
import { useNavigate } from "react-router-dom"
import "./Login.css"
import logImage from "../assets/log.svg"
import registerImage from "../assets/register.svg"

function Login() {
  const navigate = useNavigate()

  const [signUpMode, setSignUpMode] = useState(false)
  const [loginRole, setLoginRole] = useState("")
  const [signupRole, setSignupRole] = useState("")
  const [loginEmail, setLoginEmail] = useState("")
  const [loginPassword, setLoginPassword] = useState("")
  const [signupName, setSignupName] = useState("")
  const [signupEmail, setSignupEmail] = useState("")
  const [signupPassword, setSignupPassword] = useState("")

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()

    console.log("LOGIN BUTTON CLICKED")


    try {
      const response = await fetch("http://127.0.0.1:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: loginEmail,
          password: loginPassword,
          role: loginRole,
        }),
      })

      console.log("STATUS",response.status)

      const data = await response.json()

      console.log("RESPONSE:", data)
      if (!response.ok) {
        alert(data.detail || "Login failed")
        return
      }

      localStorage.setItem("access_token", data.access_token)
      localStorage.setItem("isLoggedIn", "true")
      localStorage.setItem("role", data.role)
      localStorage.setItem("name", data.name)
      localStorage.setItem("email", data.email)

      if (data.role === "victim") {
        navigate("/victim")
      } else if (data.role === "counsellor") {
        navigate("/counsellor")
      } else if (data.role === "authority") {
        navigate("/authority")
      }
    } catch (error) {
      console.error(error)
      alert("Could not connect to backend")
    }
  }

  const handleSignup = async (e: React.FormEvent) => {
  e.preventDefault()

  try {
    const response = await fetch("http://127.0.0.1:8000/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: signupName,
        email: signupEmail,
        password: signupPassword,
        role: signupRole,
      }),
    })

    const data = await response.json()

    if (!response.ok) {
      alert(data.detail || "Signup failed")
      return
    }

    alert("Registered successfully")
    setSignUpMode(false)
  } catch (error) {
    console.error(error)
    alert("Could not connect to backend")
  }
}

  return (
    <div className={`login-container ${signUpMode ? "sign-up-mode" : ""}`}>
      <div className="forms-container">
        <div className="signin-signup">

          <form
            className="sign-in-form"
            onSubmit={handleLogin}
          >
            <h2 className="title">Sign in</h2>

            <div className="input-field">
              <i className="fas fa-envelope"></i>

              <input
                type="email"
                placeholder="Email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
            </div>

            <div className="input-field">
              <i className="fas fa-lock"></i>

              <input
                type="password"
                placeholder="Password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
              />
            </div>

            <div className="input-field">
              <i className="fas fa-users"></i>

              <select
                value={loginRole}
                onChange={(e) => setLoginRole(e.target.value)}
                required
              >
                <option value="">Select Role</option>
                <option value="victim">Victim</option>
                <option value="counsellor">Counsellor</option>
                <option value="authority">Authority</option>
              </select>
            </div>

            <input
              type="submit"
              value="Login"
              className="btn solid"
            />

            <p className="social-text">
              Or sign in with social platforms
            </p>

            <div className="social-media">
              <a href="#" className="social-icon">
                <i className="fab fa-facebook-f"></i>
              </a>

              <a href="#" className="social-icon">
                <i className="fab fa-twitter"></i>
              </a>

              <a href="#" className="social-icon">
                <i className="fab fa-google"></i>
              </a>

              <a href="#" className="social-icon">
                <i className="fab fa-linkedin-in"></i>
              </a>
            </div>
          </form>

          <form className="sign-up-form" onSubmit={handleSignup}>
            <h2 className="title">Sign up</h2>

            <div className="input-field">
              <i className="fas fa-user"></i>
              <input
              type="text"
              placeholder="Username"
              value={signupName}
              onChange={(e) => setSignupName(e.target.value)}
              required
            />
            </div>

            <div className="input-field">
              <i className="fas fa-envelope"></i>
              <input
                type="email"
                placeholder="Email"
                value={signupEmail}
                onChange={(e) => setSignupEmail(e.target.value)}
                required
              />
            </div>

            <div className="input-field">
              <i className="fas fa-lock"></i>
              <input
              type="password"
              placeholder="Password"
              value={signupPassword}
              onChange={(e) => setSignupPassword(e.target.value)}
              required
            />
            </div>

            <div className="input-field">
              <i className="fas fa-users"></i>

              <select
                value={signupRole}
                onChange={(e) => setSignupRole(e.target.value)}
                required
              >
                <option value="">Select Role</option>
                <option value="victim">Victim</option>
                <option value="counsellor">Counsellor</option>
                <option value="authority">Authority</option>
              </select>
            </div>

            <input
              type="submit"
              className="btn"
              value="Sign up"
            />

            <p className="social-text">
              Or sign up with social platforms
            </p>

            <div className="social-media">
              <a href="#" className="social-icon">
                <i className="fab fa-facebook-f"></i>
              </a>

              <a href="#" className="social-icon">
                <i className="fab fa-twitter"></i>
              </a>

              <a href="#" className="social-icon">
                <i className="fab fa-google"></i>
              </a>

              <a href="#" className="social-icon">
                <i className="fab fa-linkedin-in"></i>
              </a>
            </div>
          </form>
        </div>
      </div>

      <div className="panels-container">

        <div className="panel left-panel">
          <div className="content">
            <h3>New here?</h3>

            <p>
              Enter your details and start your journey with us.
            </p>

            <button
              className="btn transparent"
              onClick={() => setSignUpMode(true)}
            >
              Sign up
            </button>
          </div>

          <img
            src={logImage}
            className="image"
            alt="Login illustration"
          />
        </div>

        <div className="panel right-panel">
          <div className="content">
            <h3>One of us?</h3>

            <p>
              To keep connected with us, please login with your personal info.
            </p>

            <button
              className="btn transparent"
              onClick={() => setSignUpMode(false)}
            >
              Sign in
            </button>
          </div>

          <img
            src={registerImage}
            className="image"
            alt="Register illustration"
          />
        </div>

      </div>
    </div>
  )
}

export default Login