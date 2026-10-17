import { Link } from 'react-router-dom'

import { useApp } from '../context'
import type { Evaluation } from '../types'

export function MatchRing({ percent }: { percent: number }) {
  return (
    <div className="match" style={{ ['--pct' as string]: percent }} aria-label={`${percent}%`}>
      <span>{percent}%</span>
    </div>
  )
}

export function EvidenceBars({ evidence }: { evidence: Evaluation['evidence'] }) {
  return (
    <div className="evidence">
      {evidence.map((e) => (
        <div key={e.label} style={{ display: 'contents' }}>
          <span>{e.label}</span>
          <div className="bar" title={`CF ${e.cf.toFixed(2)}`}>
            <i className={e.cf < 0 ? 'neg' : ''} style={{ width: `${Math.min(Math.abs(e.cf), 1) * 50}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function RecipeCard({ evaluation, ingredientName }: { evaluation: Evaluation; ingredientName: (id: string) => string }) {
  const { t, meta } = useApp()
  const unit = (id: string) => meta?.ingredients.find((i) => i.id === id)?.unit ?? ''
  const label = (group: 'categories' | 'cuisines' | 'difficulties', id: string) => meta?.[group].find((o) => o.id === id)?.label ?? id
  return (
    <article className="card recipe-card">
      <div className="row" style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
        <div>
          <h3>{evaluation.name}</h3>
          <div className="muted">
            {label('categories', evaluation.category)} · {label('cuisines', evaluation.cuisine)} · {evaluation.time_minutes} {t('minutes')} · {label('difficulties', evaluation.difficulty)}
          </div>
        </div>
        <MatchRing percent={evaluation.match_percent} />
      </div>

      {evaluation.makeable_now ? (
        <span className="chip static ok">✓ {t('ready')}</span>
      ) : (
        <div>
          <div className="section-title">{t('toBuy')}</div>
          <div className="chips">
            {evaluation.missing.map((r) => (
              <span key={r.ingredient} className="chip static warn">
                {ingredientName(r.buy!)} · {Math.round(r.buy_qty)} {unit(r.buy!) === 'pc' ? '×' : unit(r.buy!)}
              </span>
            ))}
          </div>
        </div>
      )}

      {evaluation.substitutions.length > 0 && (
        <div>
          <div className="section-title">{t('swaps')}</div>
          <ul className="muted" style={{ margin: 0, paddingInlineStart: 18 }}>
            {evaluation.substitutions.map((r) => (
              <li key={r.ingredient}>
                <strong>{ingredientName(r.ingredient)}</strong> → {ingredientName(r.use!)}
                {r.note ? ` — ${r.note}` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      <details>
        <summary>{t('why')}</summary>
        <div style={{ marginTop: 10 }}>
          <EvidenceBars evidence={evaluation.evidence} />
        </div>
      </details>

      <Link className="btn ghost small" to={`/recipe/${evaluation.recipe_id}`} style={{ alignSelf: 'flex-start' }}>
        {t('open')}
      </Link>
    </article>
  )
}
