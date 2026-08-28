import Navbar from '../components/Navbar'
import Hero from '../components/Hero'
import RoleCards from '../components/RoleCards'
import HowItWorks from '../components/HowItWorks'
import Benefits from '../components/Benefits'
import Footer from '../components/Footer'
import './Home.css'

function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <RoleCards />
        <HowItWorks />
        <Benefits />
      </main>
      <Footer />
    </>
  )
}

export default Home
