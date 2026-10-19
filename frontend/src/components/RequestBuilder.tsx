import { useMemo, useState } from 'react'

import { useApp } from '../context'
import type { Option, UserRequest } from '../types'

type ListKey = 'diets' | 'avoid' | 'cravings' | 'categories' | 'cuisines'

function ToggleGroup({ title, options, selected, onToggle }: { title: string; options: Option[]; selected: string[]; onToggle: (id: string) => void }) {
  return (
    <div>
      <div className="section-title">{title}</div>
      <div className="chips">
        {options.map((o) => (
          <button key={o.id} type="button" className="chip" aria-pressed={selected.includes(o.id)} onClick={() => onToggle(o.id)}>
            {o.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default function RequestBuilder({ value, onChange, onSubmit, busy }: { value: UserRequest; onChange: (r: UserRequest) => void; onSubmit: () => void; busy: boolean }) {
  const { t, meta } = useApp()
  const [query, setQuery] = useState('')
  const inPantry = useMemo(() => new Set(value.pantry.map((p) => p.id)), [value.pantry])
  const matches = useMemo(() => {
    if (!meta || !query.trim()) return []
    const q = query.trim().toLowerCase()
    return meta.ingredients.filter((i) => !i.staple && !inPantry.has(i.id) && (i.name.toLowerCase().includes(q) || i.id.includes(q))).slice(0, 8)
  }, [meta, query, inPantry])

  if (!meta) return null
  const name = (id: string) => meta.ingredients.find((i) => i.id === id)?.name ?? id
  const toggle = (key: ListKey, id: string) =>
    onChange({ ...value, [key]: value[key].includes(id) ? value[key].filter((x) => x !== id) : [...value[key], id] })
  const single = (key: 'occasion' | 'skill', id: string) => onChange({ ...value, [key]: value[key] === id ? null : id })

  return (
    <form
      className="stack"
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit()
      }}
    >
      <div>
        <div className="section-title">{t('pantry')}</div>
        <div className="chips" style={{ marginBottom: 8 }}>
          {value.pantry.map((p) => (
            <button key={p.id} type="button" className="chip" aria-pressed="true" onClick={() => onChange({ ...value, pantry: value.pantry.filter((x) => x.id !== p.id) })}>
              {name(p.id)} ✕
            </button>
          ))}
        </div>
        <input type="text" placeholder={t('searchIngredient')} value={query} onChange={(e) => setQuery(e.target.value)} aria-label={t('searchIngredient')} />
        {matches.length > 0 && (
          <div className="chips" style={{ marginTop: 8 }}>
            {matches.map((i) => (
              <button
                key={i.id}
                type="button"
                className="chip"
                onClick={() => {
                  onChange({ ...value, pantry: [...value.pantry, { id: i.id }] })
                  setQuery('')
                }}
              >
                + {i.name}
              </button>
            ))}
          </div>
        )}
      </div>
      <ToggleGroup title={t('diets')} options={meta.diets} selected={value.diets} onToggle={(id) => toggle('diets', id)} />
      <ToggleGroup title={t('avoid')} options={meta.allergens} selected={value.avoid} onToggle={(id) => toggle('avoid', id)} />
      <ToggleGroup title={t('cravings')} options={meta.flavors} selected={value.cravings} onToggle={(id) => toggle('cravings', id)} />
      <ToggleGroup title={t('categories')} options={meta.categories} selected={value.categories} onToggle={(id) => toggle('categories', id)} />
      <ToggleGroup title={t('occasion')} options={meta.occasions} selected={value.occasion ? [value.occasion] : []} onToggle={(id) => single('occasion', id)} />
      <ToggleGroup title={t('skill')} options={meta.skills} selected={value.skill ? [value.skill] : []} onToggle={(id) => single('skill', id)} />
      <div className="row" style={{ alignItems: 'flex-end' }}>
        <label className="field" style={{ width: 200 }}>
          {t('maxTime')}
          <input type="number" min={5} max={1440} value={value.max_time ?? ''} onChange={(e) => onChange({ ...value, max_time: e.target.value ? Number(e.target.value) : null })} />
        </label>
        <label className="field" style={{ width: 140 }}>
          {t('servings')}
          <input type="number" min={1} max={200} value={value.servings ?? ''} onChange={(e) => onChange({ ...value, servings: e.target.value ? Number(e.target.value) : null })} />
        </label>
        <button className="btn" type="submit" disabled={busy || value.pantry.length === 0}>
          {busy ? t('thinking') : t('recommend')}
        </button>
      </div>
    </form>
  )
}
