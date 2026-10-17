import { createContext, useContext } from 'react'

import type { TextKey } from './i18n'
import type { AskResponse, Lang, Meta, Recommendation, UserRequest } from './types'

export interface Session {
  request: UserRequest
  result: Recommendation
  ask?: Omit<AskResponse, 'result' | 'request'>
}

export interface AppState {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: TextKey) => string
  meta: Meta | null
  session: Session | null
  setSession: (session: Session | null) => void
}

export const AppContext = createContext<AppState | null>(null)

export function useApp(): AppState {
  const state = useContext(AppContext)
  if (!state) throw new Error('useApp must be used inside <AppProvider>')
  return state
}
