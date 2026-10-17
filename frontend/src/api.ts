import type { AdminItem, AskResponse, Impact, Lang, Meta, Plan, ProofNode, RecipeDetail, Recommendation, UserRequest } from './types'

const BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function call<T>(path: string, init: RequestInit = {}, adminToken?: string): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (adminToken) headers['X-Admin-Token'] = adminToken
  const response = await fetch(`${BASE}${path}`, { ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } })
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* keep the status text */
    }
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}

const post = <T>(path: string, body: unknown, adminToken?: string) => call<T>(path, { method: 'POST', body: JSON.stringify(body) }, adminToken)

export const api = {
  meta: (lang: Lang) => call<Meta>(`/api/meta?lang=${lang}`),
  health: () => call<{ llm: boolean; knowledge_base: Record<string, number> }>('/api/health'),
  ask: (text: string, lang?: Lang) => post<AskResponse>('/api/ask', { text, lang, top_k: 6 }),
  recommend: (request: UserRequest) => post<{ answer: string; result: Recommendation }>('/api/recommend', request),
  recipe: (id: string, lang: Lang, servings?: number) => call<RecipeDetail>(`/api/recipes/${id}?lang=${lang}${servings ? `&servings=${servings}` : ''}`),
  prove: (request: UserRequest, recipeId: string) => post<ProofNode & { evaluation: unknown }>('/api/prove', { request, recipe_id: recipeId }),
  whatIf: (request: UserRequest, add: string[]) =>
    post<{ added: string[]; newly_makeable: string[]; makeable_before: number; makeable_after: number }>('/api/what-if', { request, add }),
  plan: (request: UserRequest, bakes: number, budget: number | null) => post<Plan>('/api/plan', { request, bakes, budget }),
  evaluation: () => call<Record<string, unknown>>('/api/eval'),
  admin: {
    list: (kind: 'rules' | 'substitutions', token: string) => call<AdminItem[]>(`/api/admin/${kind}`, {}, token),
    save: (kind: 'rules' | 'substitutions', id: string, data: unknown, status: string, token: string) =>
      call<{ id: string }>(`/api/admin/${kind}/${id}`, { method: 'PUT', body: JSON.stringify({ data, status }) }, token),
    decide: (kind: 'rules' | 'substitutions', id: string, decision: 'approve' | 'reject', token: string) =>
      post<{ status: string }>(`/api/admin/${kind}/${id}/${decision}`, {}, token),
    remove: (kind: 'rules' | 'substitutions', id: string, token: string) => call<unknown>(`/api/admin/${kind}/${id}`, { method: 'DELETE' }, token),
    mine: (token: string) => post<{ added: Record<string, number>; corpus_recipes: number }>('/api/admin/mine', {}, token),
    preview: (kind: 'rules' | 'substitutions', data: unknown, token: string) => post<Impact>('/api/admin/preview', { kind, data }, token),
    audit: (token: string) => call<{ at: string; action: string; target: string; detail: string }[]>('/api/admin/audit/log', {}, token),
  },
}

export const emptyRequest = (lang: Lang): UserRequest => ({
  pantry: [],
  diets: [],
  avoid: [],
  cravings: [],
  categories: [],
  cuisines: [],
  occasion: null,
  skill: null,
  max_time: null,
  servings: null,
  lang,
  top_k: 6,
})
