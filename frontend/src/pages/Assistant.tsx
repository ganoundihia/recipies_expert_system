import { useState } from 'react'

import { api, emptyRequest } from '../api'
import blueberry from '../assets/blueberry.png'
import cake from '../assets/cake-mauve.png'
import leaf from '../assets/leaf.png'
import macarons from '../assets/macarons.png'
import whisk from '../assets/whisk.png'
import RequestBuilder from '../components/RequestBuilder'
import Results from '../components/Results'
import { EXAMPLES } from '../i18n'
import { useApp } from '../context'
import type { UserRequest } from '../types'

export default function Assistant() {
  const { t, lang, session, setSession } = useApp()
  const [text, setText] = useState('')
  const [picker, setPicker] = useState(false)
  const [request, setRequest] = useState<UserRequest>(() => session?.request ?? emptyRequest(lang))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async (task: () => Promise<void>) => {
    setBusy(true)
    setError(null)
    try {
      await task()
    } catch (e) {
      setError(e instanceof Error ? e.message : t('error'))
    } finally {
      setBusy(false)
    }
  }

  const ask = (value = text) =>
    run(async () => {
      const response = await api.ask(value, lang)
      const { result, request: parsed, ...rest } = response
      setSession({ request: parsed, result, ask: rest })
      setRequest(parsed)
    })

  const recommend = () =>
    run(async () => {
      const body = { ...request, lang }
      const response = await api.recommend(body)
      setSession({ request: body, result: response.result })
    })

  return (
    <div className="stack" style={{ gap: 24 }}>
      <section className="hero">
        <img className="leaf" src={leaf} alt="" />
        <div>
          <h1 className="display">
            {t('tagline')} <img src={blueberry} alt="" style={{ width: 46, verticalAlign: 'middle' }} />
          </h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="art" aria-hidden="true">
          <img className="cake" src={cake} alt="" />
          <img className="macarons" src={macarons} alt="" />
        </div>
      </section>

      <section className="card ask-box stack">
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault()
            if (text.trim().length > 1) ask()
          }}
        >
          <textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={t('askPlaceholder')} aria-label={t('askPlaceholder')} maxLength={2000} />
          <div className="row" style={{ justifyContent: 'space-between' }}>
            <div className="row">
              <span className="muted">{t('examples')}:</span>
              {EXAMPLES[lang].map((example, index) => (
                <button
                  key={example}
                  type="button"
                  className="chip"
                  title={example}
                  onClick={() => {
                    setText(example)
                    ask(example)
                  }}
                >
                  #{index + 1}
                </button>
              ))}
            </div>
            <button className="btn" type="submit" disabled={busy || text.trim().length < 2}>
              {busy ? t('thinking') : t('ask')}
            </button>
          </div>
        </form>
        <button type="button" className="link-btn" style={{ alignSelf: 'flex-start' }} onClick={() => setPicker(!picker)}>
          {picker ? t('hidePicker') : t('orPick')}
        </button>
        {picker && <RequestBuilder value={request} onChange={setRequest} onSubmit={recommend} busy={busy} />}
      </section>

      {error && <div className="error">{error}</div>}
      {busy && (
        <div className="loader">
          <img src={whisk} alt="" /> {t('thinking')}
        </div>
      )}
      {!busy && session && <Results session={session} />}
    </div>
  )
}
