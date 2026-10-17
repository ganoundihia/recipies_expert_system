import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { EvidenceBars, MatchRing } from './components/RecipeCard'
import { AppProvider } from './state'

const meta = {
  diets: [{ id: 'vegan', label: 'vegan' }],
  allergens: [],
  flavors: [],
  categories: [{ id: 'cookie', label: 'cookie' }],
  cuisines: [{ id: 'algerian', label: 'Algerian' }],
  occasions: [],
  skills: [],
  difficulties: [{ id: 'easy', label: 'easy' }],
  ingredients: [{ id: 'all_purpose_flour', name: 'All-purpose flour', category: 'flour', unit: 'g', allergens: ['gluten'], animal: false }],
  llm: true,
}

const askResponse = {
  request: { pantry: [{ id: 'all_purpose_flour' }], diets: [], avoid: [], cravings: [], categories: [], cuisines: [], occasion: null, skill: null, max_time: null, servings: null, lang: 'en', top_k: 6 },
  parser: 'llm',
  unrecognized: ['dragon fruit'],
  safety_net: ['avoid:sesame'],
  guard: { checked: true, score: 0.001, flagged: false },
  answer: { text: 'My top pick is Ghribia.', source: 'llm', verified: true, violations: [] },
  timings_ms: { total: 1234 },
  result: {
    recommendations: [
      {
        recipe_id: 'ghribia', name: 'Ghribia', category: 'cookie', cuisine: 'algerian', difficulty: 'easy', time_minutes: 40, servings: 30,
        feasible: true, makeable_now: false, score: 0.4, match_percent: 70, cost_to_complete: 160, excluded_reason: null,
        missing: [{ ingredient: 'vanilla_sugar', need: 8, status: 'buy', use: null, use_qty: 0, buy: 'vanilla_sugar', buy_qty: 8, substitution: null, cf: 1, note: null }],
        substitutions: [], resolutions: [], evidence: [{ label: 'Missing 1: Vanilla sugar', cf: -0.25 }],
      },
    ],
    excluded: [], trace: [{ rule: 'O1', text: 'Eid is traditionally celebrated with Algerian pastries.', cf: 0.8 }],
    best_purchases: [{ ingredient: 'vanilla_sugar', name: 'Vanilla sugar', unlocks: ['ghribia'], cost: 160 }], forbidden: [], considered: 68,
  },
}

function mockFetch() {
  return vi.fn(async (url: string) => {
    const body = url.startsWith('/api/meta') ? meta : url.startsWith('/api/ask') ? askResponse : {}
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
}

function renderApp() {
  return render(
    <MemoryRouter>
      <AppProvider>
        <App />
      </AppProvider>
    </MemoryRouter>,
  )
}

describe('Pantry Chef UI', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.stubGlobal('fetch', mockFetch())
  })
  afterEach(() => vi.unstubAllGlobals())

  it('asks in natural language and shows the grounded answer, cards and reasoning', async () => {
    renderApp()
    await userEvent.type(screen.getByRole('textbox'), 'I have flour')
    await userEvent.click(screen.getByRole('button', { name: 'Find my recipe' }))

    expect(await screen.findByText('My top pick is Ghribia.')).toBeInTheDocument()
    expect(screen.getByText(/Grounded: every fact checked/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ghribia' })).toBeInTheDocument()
    expect(screen.getByText(/Eid is traditionally celebrated/)).toBeInTheDocument()
    expect(screen.getByText(/dragon fruit/)).toBeInTheDocument()
    expect(screen.getByText(/avoid:sesame/)).toBeInTheDocument()
  })

  it('switches to Arabic with right-to-left layout', async () => {
    renderApp()
    await userEvent.click(screen.getByRole('button', { name: 'ع' }))
    await waitFor(() => expect(document.documentElement.dir).toBe('rtl'))
    expect(screen.getByRole('button', { name: 'ابحث عن وصفتي' })).toBeInTheDocument()
  })
})

describe('explanation widgets', () => {
  it('renders match percentage and signed evidence bars', () => {
    const { container } = render(
      <>
        <MatchRing percent={82} />
        <EvidenceBars evidence={[{ label: 'You have everything', cf: 0.6 }, { label: 'Missing 1', cf: -0.25 }]} />
      </>,
    )
    expect(screen.getByText('82%')).toBeInTheDocument()
    expect(container.querySelectorAll('.bar i.neg')).toHaveLength(1)
  })
})
