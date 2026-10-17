import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api'
import { useApp } from '../context'
import type { Plan } from '../types'

export default function Planner() {
  const { t, lang, session } = useApp()
  const [bakes, setBakes] = useState(3)
  const [budget, setBudget] = useState<number | ''>(1500)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!session) {
    return (
      <div className="card stack">
        <h1 className="display" style={{ fontSize: 48 }}>
          {t('planner')}
        </h1>
        <p>{t('needRequest')}</p>
        <Link className="btn" to="/" style={{ alignSelf: 'flex-start' }}>
          {t('navAssistant')}
        </Link>
      </div>
    )
  }

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      setPlan(await api.plan({ ...session.request, lang }, bakes, budget === '' ? null : budget))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack" style={{ gap: 22 }}>
      <section className="card stack">
        <h1 className="display" style={{ fontSize: 52 }}>
          {t('planner')}
        </h1>
        <p className="muted">{t('plannerIntro')}</p>
        <div className="row" style={{ alignItems: 'flex-end' }}>
          <label className="field" style={{ width: 170 }}>
            {t('bakes')}
            <input type="number" min={1} max={14} value={bakes} onChange={(e) => setBakes(Number(e.target.value) || 1)} />
          </label>
          <label className="field" style={{ width: 170 }}>
            {t('budget')}
            <input type="number" min={0} value={budget} onChange={(e) => setBudget(e.target.value === '' ? '' : Number(e.target.value))} />
          </label>
          <button className="btn" type="button" onClick={submit} disabled={busy}>
            {busy ? t('thinking') : t('makePlan')}
          </button>
        </div>
      </section>
      {error && <div className="error">{error}</div>}
      {plan && (
        <div className="two-col">
          <section className="card stack">
            {plan.plan.map((item, index) => (
              <div key={item.recipe_id}>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <Link to={`/recipe/${item.recipe_id}`}>
                    <strong>
                      {index + 1}. {item.name}
                    </strong>
                  </Link>
                  <span className="badge">{item.match_percent}%</span>
                </div>
                <div className="muted">
                  {item.buy.length ? item.buy.map((b) => `${b.name} ${b.qty} ${b.unit}`).join(' · ') : t('ready')} — {item.cost} {plan.currency}
                </div>
              </div>
            ))}
          </section>
          <section className="card stack">
            <h2 className="section-title">{t('shopping')}</h2>
            <div className="table-wrap">
              <table>
                <tbody>
                  {plan.shopping_list.map((s) => (
                    <tr key={s.ingredient}>
                      <td>{s.name}</td>
                      <td className="num">
                        {s.packs} × {s.pack_size} {s.unit}
                      </td>
                      <td className="num">{s.cost}</td>
                    </tr>
                  ))}
                  <tr>
                    <th>{t('total')}</th>
                    <td />
                    <th className="num">
                      {plan.total_cost} {plan.currency}
                    </th>
                  </tr>
                </tbody>
              </table>
            </div>
            {plan.leftovers.length > 0 && (
              <p className="muted">
                {t('leftovers')}: {plan.leftovers.map((l) => `${l.name} ${l.qty} ${l.unit}`).join(', ')}
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  )
}
