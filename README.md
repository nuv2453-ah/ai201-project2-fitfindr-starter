# FitFindr

A multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. Given a natural language query, FitFindr searches mock thrift listings, suggests outfit combinations using the user's wardrobe, and generates a shareable fit card caption.

---

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) → list[dict]`
Searches the mock listings dataset for items matching the description, optional size, and optional price ceiling. Scores each listing by keyword overlap against title, description, and style_tags. Returns a list of matching listing dicts sorted by relevance score, highest first. Returns an empty list if nothing matches — never raises an exception.

### `suggest_outfit(new_item: dict, wardrobe: dict) → str`
Given a thrifted item and the user's wardrobe, calls the Groq LLM to suggest 1–2 complete outfit combinations using named pieces from the wardrobe. If the wardrobe is empty, returns general styling advice instead of crashing.

### `create_fit_card(outfit: str, new_item: dict) → str`
Calls the Groq LLM to generate a 2–4 sentence casual Instagram/TikTok-style caption for the outfit. Mentions the item name, price, and platform naturally. Uses temperature=0.9 so output varies. Guards against empty outfit input.

---

## Planning Loop

The agent runs the following conditional logic in `run_agent()`:

1. Parse the query with regex to extract `description`, `size`, and `max_price`.
2. Call `search_listings(description, size, max_price)`.
   - If results are empty → set `session["error"]` and return immediately. `suggest_outfit` and `create_fit_card` are never called.
   - If results are non-empty → set `session["selected_item"] = results[0]` and continue.
3. Call `suggest_outfit(selected_item, wardrobe)` → store in `session["outfit_suggestion"]`.
4. Call `create_fit_card(outfit_suggestion, selected_item)` → store in `session["fit_card"]`.
5. Return the session.

The agent does not call all three tools unconditionally — it branches on the search result before proceeding.

---

## State Management

All state is stored in a single session dict initialized at the start of `run_agent()`. Each tool writes its output into the session before the next tool is called:

- `session["parsed"]` — description, size, max_price extracted from the query
- `session["search_results"]` — full list returned by search_listings
- `session["selected_item"]` — set to results[0]; passed directly into suggest_outfit
- `session["wardrobe"]` — passed in at start; never modified
- `session["outfit_suggestion"]` — returned by suggest_outfit; passed into create_fit_card
- `session["fit_card"]` — final output shown to user
- `session["error"]` — set on early termination; signals the agent to stop

No data is re-entered between steps. The same dict object flows through all three tools.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match query | Sets `session["error"]`: "No listings found for your search. Try broadening your description, adjusting your size, or raising your price limit." Returns session immediately without calling the other tools. |
| `suggest_outfit` | Wardrobe is empty | Calls LLM with a prompt for general styling advice rather than crashing. Returns a non-empty string describing what the item pairs well with. |
| `create_fit_card` | Outfit string is empty or whitespace | Returns: "Cannot generate a fit card without an outfit suggestion. Please retry your search." No exception raised. |

**Concrete example from testing:**

---

## Testing Example

To verify the agent end-to-end locally:

```python
from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# Happy path — should return a fit card
session = run_agent("vintage graphic tee under $30", get_example_wardrobe())
assert session["error"] is None
assert session["fit_card"] is not None
print("fit_card:", session["fit_card"])

# No-results path — should set error and skip LLM calls
session2 = run_agent("designer ballgown size XXS under $5", get_example_wardrobe())
assert session2["error"] is not None
assert session2["outfit_suggestion"] is None
print("error:", session2["error"])

# Empty wardrobe — suggest_outfit should return general styling advice, not crash
session3 = run_agent("vintage graphic tee under $30", get_empty_wardrobe())
assert session3["outfit_suggestion"] is not None
print("general advice:", session3["outfit_suggestion"])
```

Run from the project root with a valid `GROQ_API_KEY` in `.env`.

---

## Spec Reflection

The final implementation matches the planning.md spec closely. The three-tool structure, session dict pattern, and early-exit branch on empty search results were all designed upfront and carried through without major changes.

One deviation: the original spec noted that `suggest_outfit` should return a fallback string if the LLM call fails, but the initial implementation only handled the empty-wardrobe case — the actual API call had no `try/except`. This was caught during review and fixed by wrapping both LLM calls in `try/except Exception` blocks that return the fallback strings on any API-level failure (network timeout, rate limit, invalid response). The planning.md error handling table has been updated to reflect this.

Everything else — the regex query parser, the keyword scoring in `search_listings`, the temperature=0.9 on `create_fit_card`, and the three-panel Gradio layout — matched the spec as written.

---

## AI Usage

Claude (claude.ai) was used throughout this project in the following specific ways:

- **Tool implementation:** Provided the Tool 1–3 specs from planning.md to Claude and asked it to generate the function bodies. Reviewed each output against the spec before accepting — caught one case where the keyword scoring didn't include `style_tags` and prompted a correction.

- **Planning loop:** Gave Claude the Planning Loop, State Management, and Architecture sections from planning.md and asked it to implement `run_agent()`. Verified the generated code branched correctly on empty results and stored values in the session dict at each step.

- **README drafting:** Used Claude to draft sections of this README, then edited for accuracy and completeness.

- **Bug fix:** After project review flagged missing `try/except` around LLM calls, used Claude to generate the corrected code blocks and verified the output matched the existing function structure before applying.

All AI-generated code was read, tested, and understood before being committed. No output was accepted without manual verification against the spec.
