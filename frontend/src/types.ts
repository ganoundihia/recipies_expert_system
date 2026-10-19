export type Lang = 'en' | 'fr' | 'ar'

export interface PantryItem {
  id: string
  qty?: number | null
}

export interface UserRequest {
  pantry: PantryItem[]
  diets: string[]
  avoid: string[]
  cravings: string[]
  categories: string[]
  cuisines: string[]
  occasion: string | null
  skill: string | null
  max_time: number | null
  servings: number | null
  lang: Lang
  top_k: number
}

export interface Resolution {
  ingredient: string
  need: number
  status: 'have' | 'partial' | 'substitute' | 'buy' | 'staple' | 'skipped' | 'impossible'
  use: string | null
  use_qty: number
  buy: string | null
  buy_qty: number
  substitution: string | null
  cf: number
  note: string | null
}

export interface Evidence {
  label: string
  cf: number
}

export interface Evaluation {
  recipe_id: string
  name: string
  category: string
  cuisine: string
  difficulty: string
  time_minutes: number
  servings: number
  feasible: boolean
  makeable_now: boolean
  score: number
  match_percent: number
  missing: Resolution[]
  substitutions: Resolution[]
  resolutions: Resolution[]
  evidence: Evidence[]
  excluded_reason: string | null
  cost_to_complete: number
}

export interface PurchaseSuggestion {
  ingredient: string
  name: string
  unlocks: string[]
  cost: number
}

export interface Recommendation {
  recommendations: Evaluation[]
  excluded: Evaluation[]
  trace: { rule: string; text: string; cf: number }[]
  best_purchases: PurchaseSuggestion[]
  forbidden: string[]
  considered: number
}

export interface Answer {
  text: string
  source: 'llm' | 'template'
  verified: boolean
  violations: string[]
}

export interface AskResponse {
  request: UserRequest
  parser: 'llm' | 'keywords'
  unrecognized: string[]
  safety_net: string[]
  guard: { checked: boolean; score: number; flagged: boolean }
  answer: Answer
  result: Recommendation
  timings_ms: Record<string, number>
}

export interface Option {
  id: string
  label: string
}

export interface IngredientInfo {
  id: string
  name: string
  category: string
  unit: string
  allergens: string[]
  animal: boolean
  staple?: boolean
}

export interface Meta {
  diets: Option[]
  allergens: Option[]
  flavors: Option[]
  categories: Option[]
  cuisines: Option[]
  occasions: Option[]
  skills: Option[]
  difficulties: Option[]
  ingredients: IngredientInfo[]
  llm: boolean
}

export interface RecipeDetail {
  id: string
  name: string
  cuisine: string
  category: string
  flavors: string[]
  time_minutes: number
  difficulty: string
  servings: number
  ingredients: { id: string; name: string; qty: number; unit: string; optional: boolean }[]
  steps: string[]
  steps_translated: boolean
}

export interface ProofNode {
  goal: string
  status: string
  cf?: number
  rule?: string
  note?: string | null
  children?: ProofNode[]
}

export interface Plan {
  plan: { recipe_id: string; name: string; match_percent: number; cost: number; buy: { name: string; qty: number; unit: string }[] }[]
  shopping_list: { ingredient: string; name: string; packs: number; pack_size: number; unit: string; cost: number }[]
  total_cost: number
  budget: number | null
  leftovers: { name: string; qty: number; unit: string }[]
  currency: string
}

export interface AdminItem {
  id: string
  status: 'approved' | 'pending' | 'rejected'
  source: string
  updated_at: string
  data: Record<string, unknown>
}

export interface Impact {
  requests: number
  requests_changed: number
  top_pick_changed: number
  recipes_unlocked: number
  recipes_lost: number
  examples: { pantry: string[]; newly_makeable: string[] }[]
}
