"""Write the benchmark table from eval/results.json into the project README.

python -m eval.report
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RESULTS = Path(__file__).parent / "results.json"
README = Path(__file__).resolve().parents[2] / "README.md"


def fmt(value, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "percent":
        return f"{value * 100:.1f}%"
    if kind == "ms":
        return f"{value / 1000:.1f} s" if value >= 1000 else f"{value:.0f} ms"
    return f"{value:.3f}"


def table(data: dict) -> str:
    systems = list(data["systems"])
    lines = ["| Metric | " + " | ".join(data["system_labels"][s] for s in systems) + " |", "|---|" + "---:|" * len(systems)]
    for key, doc in data["metrics"].items():
        values = [data["systems"][s].get(key) for s in systems]
        numbers = [v for v in values if v is not None]
        best = (min(numbers) if doc["better"] == "lower" else max(numbers)) if numbers else None
        cells = [f"**{fmt(v, doc['format'])}**" if v is not None and v == best and len(numbers) > 1 else fmt(v, doc["format"]) for v in values]
        lines.append(f"| {doc['label']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    block = (
        f"{data['cases']} requests with known ground truth (English, French, Arabic), "
        f"models: `{data['models']['parse']}` (parsing), `{data['models']['narrate']}` (writing and the LLM-only baseline). "
        "Reproduce with `python -m eval.run_eval`; results are also shown on the app's *Benchmark* page.\n\n" + table(data) + "\n\n" + "\n".join(f"- {note}" for note in data["notes"])
    )
    readme = README.read_text(encoding="utf-8")
    readme = re.sub(r"<!-- BENCHMARK:START -->.*<!-- BENCHMARK:END -->", f"<!-- BENCHMARK:START -->\n{block}\n<!-- BENCHMARK:END -->", readme, flags=re.S)
    README.write_text(readme, encoding="utf-8")
    print(table(data))


if __name__ == "__main__":
    main()
