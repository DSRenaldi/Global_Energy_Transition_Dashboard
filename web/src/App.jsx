import { useEffect, useState } from 'react'
import { ComparisonPage } from './pages/ComparisonPage'
import { BriefingPage } from './pages/BriefingPage'
import { MethodologyPage } from './pages/MethodologyPage'
import { OverviewPage } from './pages/OverviewPage'
import { RiskPage } from './pages/RiskPage'
import { TrendsPage } from './pages/TrendsPage'

const pages = [
  ['overview', 'Ikhtisar'],
  ['briefing', 'Briefing'],
  ['comparison', 'Negara'],
  ['trends', 'Jejak transisi'],
  ['risk', 'Risiko aset'],
  ['methodology', 'Metodologi'],
]

const getPage = () => window.location.hash.replace('#', '') || 'overview'

export default function App() {
  const [page, setPage] = useState(getPage)

  useEffect(() => {
    const onHashChange = () => setPage(getPage())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const openPage = (nextPage) => {
    window.location.hash = nextPage
    setPage(nextPage)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const Page = {
    overview: OverviewPage,
    briefing: BriefingPage,
    comparison: ComparisonPage,
    trends: TrendsPage,
    risk: RiskPage,
    methodology: MethodologyPage,
  }[page] ?? OverviewPage

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Lewati ke konten utama</a>
      <header className="site-header">
        <button className="brand" onClick={() => openPage('overview')} aria-label="Gridshift, kembali ke ikhtisar">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <span><b>GRIDSHIFT</b><small>WORLD ENERGY TRANSITION</small></span>
        </button>
        <nav aria-label="Navigasi utama">
          {pages.map(([key, label]) => <button key={key} className={page === key ? 'active' : ''} aria-current={page === key ? 'page' : undefined} onClick={() => openPage(key)}>{label}</button>)}
        </nav>
        <div className="header-meta"><span>DATA CUT</span><b>2020 / 2022</b></div>
      </header>
      <main id="main-content"><Page onOpen={openPage} /></main>
      <footer>
        <div className="brand brand--footer"><span className="brand-mark"><i /><i /><i /></span><span><b>GRIDSHIFT</b><small>OPEN ENERGY INTELLIGENCE</small></span></div>
        <p>Eksplorasi struktur pembangkit dan laju transisi listrik dunia.</p>
        <span>WRI · OWID · WORLD BANK</span>
      </footer>
    </div>
  )
}
