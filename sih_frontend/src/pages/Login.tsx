import { useState } from "react"
import "./Login.css"
import logImage from "../assets/log.svg"
import registerImage from "../assets/register.svg"

function Login() {
  const [signUpMode, setSignUpMode] = useState(false)

  return (
    <div className={`login-container ${signUpMode ? "sign-up-mode" : ""}`}>
      <div className="forms-container">
        <div className="signin-signup">

          <form className="sign-in-form">
            <h2 className="title">Sign in</h2>

            <div className="input-field">
              <i className="fas fa-user"></i>
              <input type="text" placeholder="Username" />
            </div>

            <div className="input-field">
              <i className="fas fa-lock"></i>
              <input type="password" placeholder="Password" />
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

          <form className="sign-up-form">
            <h2 className="title">Sign up</h2>

            <div className="input-field">
              <i className="fas fa-user"></i>
              <input type="text" placeholder="Username" />
            </div>

            <div className="input-field">
              <i className="fas fa-envelope"></i>
              <input type="email" placeholder="Email" />
            </div>

            <div className="input-field">
              <i className="fas fa-lock"></i>
              <input type="password" placeholder="Password" />
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