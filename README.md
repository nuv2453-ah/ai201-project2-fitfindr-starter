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
