import { NavLink, Route, Routes } from 'react-router-dom'

import heart from './assets/heart.png'
import whisk from './assets/whisk.png'
import Admin from './pages/Admin'
import Assistant from './pages/Assistant'
import Benchmark from './pages/Benchmark'
import Planner from './pages/Planner'
import RecipePage from './pages/RecipePage'
import { useApp } from './context'
import type { Lang } from './types'

const LANGS: { id: Lang; label: string }[] = [
  { id: 'en', label: 'EN' },
  { id: 'fr', label: 'FR' },
  { id: 'ar', label: 'ع' },
]

export default function App() {
  const { t, lang, setLang } = useApp()
  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="brand">
          <img src={whisk} alt="" />
          NeSyChef
        </NavLink>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>
            {t('navAssistant')}
          </NavLink>
          <NavLink to="/planner">{t('navPlanner')}</NavLink>
          <NavLink to="/benchmark">{t('navBenchmark')}</NavLink>
          <NavLink to="/admin">{t('navAdmin')}</NavLink>
        </nav>
        <div className="langs" role="group" aria-label="Language">
          {LANGS.map((l) => (
            <button key={l.id} type="button" aria-pressed={lang === l.id} onClick={() => setLang(l.id)}>
              {l.label}
            </button>
          ))}
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Assistant />} />
          <Route path="/recipe/:id" element={<RecipePage />} />
          <Route path="/planner" element={<Planner />} />
          <Route path="/benchmark" element={<Benchmark />} />
          <Route path="/admin" element={<Admin />} />
        </Routes>
      </main>
      <footer className="site">
        {t('footer')}
        <img src={heart} alt="" />
      </footer>
    </div>
  )
}
