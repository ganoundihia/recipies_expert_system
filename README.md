# Sweet Recipes: a baking expert system

A rule-based **expert system** that recommends a baking recipe from the ingredients you have on hand.
Pick a flour, a fat and a flavoring; the inference engine reasons over its knowledge base, recommends one
of 36 recipes and explains which rules led to that choice.

## Architecture

```
client/clientrecepies   React app (Create React App): ingredient stepper, recipe page
        │  POST /recommend { flour, fat, flavor }
        ▼
server/server.js        Express API: validates the request and runs the expert system
        │  python expert_system.py '<json>'
        ▼
server/expert_system.py Knowledge base + forward-chaining inference engine (pure Python)
```

### How the expert system reasons

The user's choices are asserted as facts in working memory, e.g. `flour = cake_flour`.
The engine then fires production rules until nothing new can be derived:

1. **Classification rules** turn each ingredient into a culinary property:
   - flour → crumb (`versatile`, `tender`, `grainy`, `chewy`)
   - fat → texture (`rich`, `moist`, `dense`)
   - flavoring → aroma (`citrus`, `coffee`, `vanilla`)
2. **Recommendation rules** combine crumb + texture + aroma into a recipe,
   e.g. `tender crumb + rich texture + vanilla aroma → Vanilla Cupcakes`.

Every fired rule is recorded and returned as a trace, which the recipe page shows under *Why this recipe?*.

| Category  | Options                                             |
|-----------|-----------------------------------------------------|
| Flour     | All-purpose flour, Cake flour, Semolina, Bread flour |
| Fat       | Butter, Margarine, Vegetable oil                    |
| Flavoring | Lemon/orange extract, Coffee extract, Vanilla extract |

## Getting started

Requirements: Node.js 18+ and Python 3.9+ (standard library only).

```bash
cd server
npm install
npm start            # API on http://localhost:7000
```

```bash
cd client/clientrecepies
npm install
npm start            # app on http://localhost:3000
```

### Configuration

| Variable               | Where  | Default                 | Purpose                          |
|------------------------|--------|-------------------------|----------------------------------|
| `PORT`                 | server | `7000`                  | API port                         |
| `CLIENT_ORIGIN`        | server | `http://localhost:3000` | Allowed CORS origin              |
| `EXPERT_SYSTEM_PYTHON` | server | `python` / `python3`    | Python interpreter to run        |
| `REACT_APP_API_URL`    | client | `http://localhost:7000` | API base URL used by the client  |

## API

`POST /recommend`

```json
{ "flour": "cake_flour", "fat": "butter", "flavor": "vanilla" }
```

```json
{
  "recipe": "Vanilla_Cupcakes_butter",
  "trace": ["R-F2: low-protein cake flour gives a soft, tender crumb", "..."]
}
```

Unknown ingredients return `400` with an `error` message. `GET /health` returns `{ "status": "ok" }`.

You can also query the expert system directly:

```bash
python server/expert_system.py '{"flour": "semolina", "fat": "butter", "flavor": "coffee_extract"}'
```

## Tests

```bash
cd server && npm test                                        # API + rule base tests
cd client/clientrecepies && npm test -- --watchAll=false     # React tests
```

The server suite also checks that every recipe the rule base can infer has a matching entry
in the client's recipe book (`client/clientrecepies/src/pages/display/Display.js`).

## Adding a recipe

1. Add or change a recommendation in `_RECOMMENDATIONS` in `server/expert_system.py`.
2. Add its ingredients and instructions to `RECIPES` in `Display.js`, using the same name as the key.
3. To add a new ingredient option, add it to `CHOICES` and write a classification rule for it in
   `expert_system.py`, then add it to `STEPS` in `Stepper.js`.
