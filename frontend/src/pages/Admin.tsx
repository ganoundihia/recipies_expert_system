import { useEffect, useState } from 'react'

import { ApiError, api } from '../api'
import type { AdminItem, Impact } from '../types'

type Kind = 'rules' | 'substitutions'

function tokenFromStorage(): string {
  try {
    return sessionStorage.getItem('pc.admin') ?? ''
  } catch {
    return ''
  }
}

function summary(kind: Kind, data: Record<string, unknown>): string {
  if (kind === 'substitutions') {
    const extra = data.kind ? ` · ${data.kind}` : ''
    return `${data.from} → ${data.to} (×${data.ratio}, CF ${data.cf})${data.support ? ` · support ${data.support}` : ''}${extra}`
  }
  const conditions = (data.if as string[][]).map((c) => c.join(' ')).join(' ∧ ')
  return `IF ${conditions} THEN ${(data.then as string[]).join(' ')} (CF ${data.cf})`
}

export default function Admin() {
  const [token, setToken] = useState(tokenFromStorage)
  const [kind, setKind] = useState<Kind>('substitutions')
  const [items, setItems] = useState<AdminItem[] | null>(null)
  const [editing, setEditing] = useState<{ id: string; json: string; status: string } | null>(null)
  const [impact, setImpact] = useState<Record<string, Impact>>({})
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [version, setVersion] = useState(0)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    api.admin
      .list(kind, token)
      .then((list) => {
        if (cancelled) return
        setItems(list)
        setError(null)
      })
      .catch((e: Error) => {
        if (cancelled) return
        setItems(null)
        setError(e instanceof ApiError && e.status === 401 ? 'Invalid admin token.' : e.message)
      })
    return () => {
      cancelled = true
    }
  }, [kind, token, version])

  const act = async (task: () => Promise<unknown>, done: string) => {
    try {
      await task()
      setMessage(done)
      setError(null)
      setVersion((v) => v + 1)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const pending = items?.filter((i) => i.status === 'pending') ?? []
  const others = items?.filter((i) => i.status !== 'pending') ?? []

  const row = (item: AdminItem) => (
    <tr key={item.id}>
      <td>
        <code>{item.id}</code>
        <div className="muted">
          {item.source} · {item.status}
        </div>
      </td>
      <td>
        {summary(kind, item.data)}
        {impact[item.id] && (
          <div className="muted">
            Impact on 60 benchmark requests: {impact[item.id].requests_changed} changed, {impact[item.id].recipes_unlocked} recipes unlocked, {impact[item.id].recipes_lost} lost,{' '}
            {impact[item.id].top_pick_changed} top picks changed.
          </div>
        )}
      </td>
      <td>
        <div className="row" style={{ gap: 6 }}>
          {item.status === 'pending' && (
            <>
              <button className="btn small ghost" type="button" onClick={() => act(async () => setImpact({ ...impact, [item.id]: await api.admin.preview(kind, item.data, token) }), `Impact computed for ${item.id}`)}>
                Preview impact
              </button>
              <button className="btn small" type="button" onClick={() => act(() => api.admin.decide(kind, item.id, 'approve', token), `${item.id} approved and live`)}>
                Approve
              </button>
              <button className="btn small danger" type="button" onClick={() => act(() => api.admin.decide(kind, item.id, 'reject', token), `${item.id} rejected`)}>
                Reject
              </button>
            </>
          )}
          <button className="btn small ghost" type="button" onClick={() => setEditing({ id: item.id, json: JSON.stringify(item.data, null, 2), status: item.status })}>
            Edit
          </button>
        </div>
      </td>
    </tr>
  )

  return (
    <div className="stack" style={{ gap: 20 }}>
      <section className="card stack">
        <h1 className="display" style={{ fontSize: 52 }}>
          Knowledge console
        </h1>
        <p className="muted">
          Knowledge engineering for the expert system: edit rules and substitutions, mine new candidates from recipe data, preview their impact on benchmark requests, then approve them. Every change is validated and
          audited.
        </p>
        <div className="row" style={{ alignItems: 'flex-end' }}>
          <label className="field" style={{ width: 260 }}>
            Admin token
            <input
              type="password"
              value={token}
              onChange={(e) => {
                setToken(e.target.value)
                try {
                  sessionStorage.setItem('pc.admin', e.target.value)
                } catch {
                  /* not persisted */
                }
              }}
            />
          </label>
          <div className="langs" role="group" aria-label="Knowledge type">
            {(['substitutions', 'rules'] as Kind[]).map((k) => (
              <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>
                {k}
              </button>
            ))}
          </div>
          <button className="btn ghost" type="button" disabled={!token} onClick={() => act(async () => {
            const r = await api.admin.mine(token)
            setMessage(`Mined ${r.added.substitutions} substitutions and ${r.added.rules} rules (pending review).`)
          }, 'Mining complete')}>
            Mine candidates
          </button>
          <button
            className="btn ghost"
            type="button"
            disabled={!token}
            onClick={() => setEditing({ id: kind === 'rules' ? 'NEW_RULE' : 'new_substitution', status: 'approved', json: kind === 'rules' ? '{\n  "if": [["occasion", "guests"]],\n  "then": ["prefer_cuisine", "french"],\n  "cf": 0.4,\n  "explain": {"en": "…", "fr": "…"}\n}' : '{\n  "from": "butter",\n  "to": "margarine",\n  "ratio": 1,\n  "cf": 0.8,\n  "note": {"en": "…"}\n}' })}
          >
            New {kind === 'rules' ? 'rule' : 'substitution'}
          </button>
        </div>
        {message && <div className="badge ok">{message}</div>}
        {error && <div className="error">{error}</div>}
      </section>

      {editing && (
        <section className="card stack">
          <label className="field">
            ID
            <input type="text" value={editing.id} onChange={(e) => setEditing({ ...editing, id: e.target.value })} />
          </label>
          <textarea style={{ minHeight: 220, fontFamily: 'monospace', fontSize: 13 }} value={editing.json} onChange={(e) => setEditing({ ...editing, json: e.target.value })} />
          <div className="row">
            <button
              className="btn"
              type="button"
              onClick={() =>
                act(async () => {
                  await api.admin.save(kind, editing.id, JSON.parse(editing.json), editing.status === 'pending' ? 'pending' : 'approved', token)
                  setEditing(null)
                }, 'Saved and validated')
              }
            >
              Save
            </button>
            <button className="btn danger" type="button" onClick={() => act(async () => {
              await api.admin.remove(kind, editing.id, token)
              setEditing(null)
            }, 'Deleted')}>
              Delete
            </button>
            <button className="btn ghost" type="button" onClick={() => setEditing(null)}>
              Cancel
            </button>
          </div>
        </section>
      )}

      {items && (
        <>
          {pending.length > 0 && (
            <section className="card">
              <h2 className="section-title">Pending review ({pending.length})</h2>
              <div className="table-wrap">
                <table>
                  <tbody>{pending.map(row)}</tbody>
                </table>
              </div>
            </section>
          )}
          <section className="card">
            <h2 className="section-title">
              {kind} ({others.length})
            </h2>
            <div className="table-wrap">
              <table>
                <tbody>{others.map(row)}</tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
