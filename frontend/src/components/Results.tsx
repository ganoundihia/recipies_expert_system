import { type Session, useApp } from '../context'
import RecipeCard from './RecipeCard'

export default function Results({ session }: { session: Session }) {
  const { t, meta } = useApp()
  const { result, ask } = session
  const ingredientName = (id: string) => meta?.ingredients.find((i) => i.id === id)?.name ?? id.replace(/_/g, ' ')

  return (
    <div className="stack">
      {ask && (
        <section className="card answer" aria-live="polite">
          <h2 className="display" style={{ fontSize: 34 }}>
            {t('answer')}
          </h2>
          <p>{ask.answer.text}</p>
          <div className="meta-line">
            {ask.guard.flagged ? (
              <span className="badge bad">⚠ {t('guardFlagged')}</span>
            ) : ask.answer.source === 'llm' ? (
              <span className="badge ok">✓ {t('verified')}</span>
            ) : (
              <span className="badge warn">{t('templateUsed')}</span>
            )}
            <span className="badge">
              {t('parsedBy')}: {ask.parser === 'llm' ? 'LLM + KB grounding' : 'keyword rules'}
            </span>
            <span className="badge">⏱ {ask.timings_ms.total} ms</span>
          </div>
          {ask.safety_net?.length > 0 && (
            <p className="muted">
              🛡 {t('safetyNet')}: {ask.safety_net.join(', ')}
            </p>
          )}
          {ask.unrecognized.length > 0 && (
            <p className="muted">
              {t('unrecognized')}: {ask.unrecognized.join(', ')}
            </p>
          )}
        </section>
      )}

      <div className="results-layout">
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {result.recommendations.length === 0 && <p className="card">{t('noResult')}</p>}
          {result.recommendations.map((e) => (
            <RecipeCard key={e.recipe_id} evaluation={e} ingredientName={ingredientName} />
          ))}
        </div>

        <aside className="stack">
          {result.best_purchases.length > 0 && (
            <section className="card">
              <div className="section-title">{t('bestBuys')}</div>
              <ul style={{ margin: 0, paddingInlineStart: 18 }}>
                {result.best_purchases.map((p) => (
                  <li key={p.ingredient}>
                    <strong>{p.name}</strong> {t('unlocks')} {p.unlocks.length} {p.unlocks.length === 1 ? t('recipe') : t('recipes')}
                    <span className="muted"> · {p.cost} DZD</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section className="card">
            <div className="section-title">{t('trace')}</div>
            <ol className="trace">
              {result.trace.map((step, index) => (
                <li key={`${step.rule}-${index}`}>
                  <code>{step.rule}</code>
                  <span>
                    {step.text} <span className="muted">(CF {step.cf})</span>
                  </span>
                </li>
              ))}
            </ol>
          </section>
          {result.excluded.length > 0 && (
            <section className="card">
              <details>
                <summary>
                  {t('excludedTitle')} ({result.excluded.length})
                </summary>
                <ul className="muted" style={{ paddingInlineStart: 18 }}>
                  {result.excluded.map((e) => (
                    <li key={e.recipe_id}>
                      <strong>{e.name}</strong>: {e.excluded_reason}
                    </li>
                  ))}
                </ul>
              </details>
            </section>
          )}
        </aside>
      </div>
    </div>
  )
}
