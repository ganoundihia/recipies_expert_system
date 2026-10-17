import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'

import { api } from './api'
import { AppContext, type AppState, type Session } from './context'
import { dictionaries } from './i18n'
import type { Lang, Meta } from './types'

function load<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function save(key: string, value: unknown) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage unavailable: state just won't survive a reload */
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => load<Lang>('pc.lang', 'en'))
  const [meta, setMeta] = useState<Meta | null>(null)
  const [session, setSessionState] = useState<Session | null>(() => load<Session | null>('pc.session', null))

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    let cancelled = false
    api.meta(lang).then((m) => !cancelled && setMeta(m)).catch(() => !cancelled && setMeta(null))
    return () => {
      cancelled = true
    }
  }, [lang])

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    save('pc.lang', next)
  }, [])

  const setSession = useCallback((next: Session | null) => {
    setSessionState(next)
    save('pc.session', next)
  }, [])

  const value = useMemo<AppState>(
    () => ({ lang, setLang, t: (key) => dictionaries[lang][key], meta, session, setSession }),
    [lang, setLang, meta, session, setSession],
  )
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}
