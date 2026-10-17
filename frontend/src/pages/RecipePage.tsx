import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../api'
import cake from '../assets/cake.png'
import whisk from '../assets/whisk.png'
import { MatchRing } from '../components/RecipeCard'
import { useApp } from '../context'
import type { Evaluation, ProofNode, RecipeDetail } from '../types'

function ProofTree({ node }: { node: ProofNode }) {
  return (
    <li>
      <span className={`status-dot ${node.status}`} />
      <span>{node.goal}</span>
      {node.rule && <code style={{ marginInlineStart: 6, fontSize: 11 }}>{node.rule}</code>}
      {node.note && <div className="muted" style={{ marginInlineStart: 16 }}>{node.note}</div>}
      {node.children && node.children.length > 0 && (
        <ul>
          {node.children.map((child, index) => (
            <ProofTree key={`${child.goal}-${index}`} node={child} />
          ))}
        </ul>
      )}
    </li>
  )
}

export default function RecipePage() {
  const { id = '' } = useParams()
  const { t, lang, session, meta } = useApp()
  const vocab = (group: 'difficulties' | 'flavors', value: string) => meta?.[group].find((o) => o.id === value)?.label ?? value
  const ingredientName = (ingredientId: string) => meta?.ingredients.find((i) => i.id === ingredientId)?.name ?? ingredientId.replace(/_/g, ' ')
  const [servings, setServings] = useState<number | undefined>(undefined)
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null)
  const [proof, setProof] = useState<(ProofNode & { evaluation: unknown }) | null>(null)
  const [whatIf, setWhatIf] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .recipe(id, lang, servings)
      .then((r) => !cancelled && setRecipe(r))
      .catch((e: Error) => !cancelled && setError(e.message))
    return () => {
      cancelled = true
    }
  }, [id, lang, servings])

  useEffect(() => {
    if (!session) return
    let cancelled = false
    api
      .prove({ ...session.request, lang, servings: servings ?? null }, id)
      .then((p) => !cancelled && setProof(p))
      .catch(() => !cancelled && setProof(null))
    return () => {
      cancelled = true
    }
  }, [id, lang, servings, session])

  if (error) return <div className="error">{error}</div>
  if (!recipe)
    return (
      <div className="loader">
        <img src={whisk} alt="" />
      </div>
    )

  const evaluation = proof?.evaluation as Evaluation | undefined
  const missing = evaluation?.missing.map((m) => m.buy!).filter(Boolean) ?? []

  return (
    <div className="stack" style={{ gap: 22 }}>
      <Link to="/">← {t('back')}</Link>
      <section className="recipe-head card">
        <div className="stack" style={{ gap: 8 }}>
          <h1 className="display">{recipe.name}</h1>
          <div className="row">
            <span className="badge">⏱ {recipe.time_minutes} {t('minutes')}</span>
            <span className="badge">{vocab('difficulties', recipe.difficulty)}</span>
            {recipe.flavors.map((f) => (
              <span key={f} className="badge">
                {vocab('flavors', f)}
              </span>
            ))}
            {evaluation && <MatchRing percent={evaluation.match_percent} />}
          </div>
          <label className="field" style={{ width: 160 }}>
            {t('servings')}
            <input type="number" min={1} max={200} value={servings ?? recipe.servings} onChange={(e) => setServings(Number(e.target.value) || undefined)} />
          </label>
        </div>
        <img src={cake} alt="" />
      </section>

      <div className="two-col">
        <section className="card">
          <h2 className="section-title">{t('ingredients')}</h2>
          <ul className="ingredients-list">
            {recipe.ingredients.map((i) => (
              <li key={i.id}>
                <strong>
                  {i.qty} {i.unit === 'pc' ? '×' : i.unit}
                </strong>{' '}
                {i.name} {i.optional && <span className="muted">({t('optional')})</span>}
              </li>
            ))}
          </ul>
        </section>
        <section className="card">
          <h2 className="section-title">{t('steps')}</h2>
          {recipe.steps_translated && <span className="badge" style={{ marginBottom: 8 }}>{t('translated')}</span>}
          <ol className="steps">
            {recipe.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      </div>

      {proof && session && (
        <section className="card stack">
          <h2 className="section-title">{t('canIMake')}</h2>
          <ul className="tree">
            <ProofTree node={proof} />
          </ul>
          {missing.length > 0 && (
            <div className="row">
              <span className="muted">{t('whatIf')}</span>
              {missing.map((ingredient) => (
                <button
                  key={ingredient}
                  className="chip"
                  type="button"
                  onClick={async () => {
                    const r = await api.whatIf({ ...session.request, lang }, [ingredient])
                    setWhatIf(`+ ${ingredientName(ingredient)}: ${r.makeable_before} → ${r.makeable_after} ${t('recipes')}${r.newly_makeable.length ? ` (${r.newly_makeable.join(', ')})` : ''}`)
                  }}
                >
                  {ingredientName(ingredient)}
                </button>
              ))}
            </div>
          )}
          {whatIf && <p className="muted">{whatIf}</p>}
        </section>
      )}
    </div>
  )
}
