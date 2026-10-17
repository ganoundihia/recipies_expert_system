import { useEffect, useState } from 'react'

import { api } from '../api'
import { useApp } from '../context'

interface MetricDoc {
  label: string
  description: string
  better: 'lower' | 'higher'
  format: 'percent' | 'ms' | 'number'
}

interface EvalResults {
  generated_at: string
  cases: number
  models: Record<string, string>
  systems: Record<string, Record<string, number | null>>
  system_labels: Record<string, string>
  metrics: Record<string, MetricDoc>
  notes: string[]
}

function format(value: number | null | undefined, kind: MetricDoc['format']) {
  if (value === null || value === undefined) return '—'
  if (kind === 'percent') return `${(value * 100).toFixed(1)}%`
  if (kind === 'ms') return `${Math.round(value)} ms`
  return value.toFixed(3)
}

export default function Benchmark() {
  const { t } = useApp()
  const [data, setData] = useState<EvalResults | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .evaluation()
      .then((d) => setData(d as unknown as EvalResults))
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) return <div className="error">{error}</div>
  if (!data) return null
  const systems = Object.keys(data.systems)

  return (
    <div className="stack" style={{ gap: 22 }}>
      <section className="card stack">
        <h1 className="display" style={{ fontSize: 52 }}>
          {t('navBenchmark')}
        </h1>
        <p className="muted">
          {data.cases} test requests · {new Date(data.generated_at).toLocaleString()} · {Object.entries(data.models).map(([k, v]) => `${k}: ${v}`).join(' · ')}
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                {systems.map((s) => (
                  <th key={s} className="num">
                    {data.system_labels[s] ?? s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.metrics).map(([key, doc]) => {
                const values = systems.map((s) => data.systems[s][key]).filter((v): v is number => typeof v === 'number')
                const best = values.length ? (doc.better === 'lower' ? Math.min(...values) : Math.max(...values)) : null
                return (
                  <tr key={key}>
                    <td>
                      <strong>{doc.label}</strong>
                      <div className="muted">{doc.description}</div>
                    </td>
                    {systems.map((s) => {
                      const value = data.systems[s][key]
                      return (
                        <td key={s} className="num" style={{ fontWeight: value === best ? 700 : 400, color: value === best ? 'var(--ok)' : undefined }}>
                          {format(value, doc.format)}
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <ul className="muted">
          {data.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
