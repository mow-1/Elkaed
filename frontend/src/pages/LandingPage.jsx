import { useState, useEffect } from 'react'
import Hero from '../components/Hero'
import Features from '../components/Features'
import DarkBand from '../components/DarkBand'
import Courses from '../components/Courses'
import Testimonials from '../components/Testimonials'
import RegisterCTA from '../components/RegisterCTA'
import { getLandingContent } from '../api/landing'

export default function LandingPage() {
  const [content, setContent] = useState(null)

  useEffect(() => {
    getLandingContent()
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setContent(data) })
      .catch(() => {})
  }, [])

  return (
    <>
      <Hero data={content?.hero} />
      <Features features={content?.features} />
      <DarkBand data={content?.dark_band} />
      <Courses />
      <Testimonials testimonials={content?.testimonials} />
      <RegisterCTA data={content?.cta} />
    </>
  )
}
