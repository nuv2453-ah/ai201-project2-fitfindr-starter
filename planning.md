# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset for secondhand items that match the user's description, size, and price ceiling. Returns a ranked list of matching items sorted by keyword relevance.

**Input parameters:**
- `description` (str): Keywords describing what the user wants (e.g. "vintage graphic tee"). Used to score listings by keyword overlap against title, description, and style_tags.
- `size` (str or None): Size string to filter by (e.g. "M", "W30"). Case-insensitive. If None, size filtering is skipped.
- `max_price` (float or None): Maximum price (inclusive). If None, price filtering is skipped.

**What it returns:**
A list of listing dicts sorted by relevance score (highest first). Each dict contains: id (str), title (str), description (str), category (str), style_tags (list of str), size (str), condition (str), price (float), colors (list of str), brand (str or None), platform (str). Returns an empty list if nothing matches — never raises an exception.

**What happens if it fails or returns nothing:**
The agent sets session["error"] to: "No listings found for your search. Try broadening your description, adjusting your size, or raising your price limit." The agent returns the session immediately and does NOT call suggest_outfit or create_fit_card.

---

### Tool 2: suggest_outfit

**What it does:**
Given a thrifted item and the user's current wardrobe, calls the Groq LLM to suggest 1–2 complete outfit combinations using specific pieces from the wardrobe. If the wardrobe is empty, returns general styling advice for the item instead.

**Input parameters:**
- `new_item` (dict): A listing dict — the item the user is considering buying. Uses title, category, colors, and style_tags fields.
- `wardrobe` (dict): A wardrobe dict with an 'items' key containing a list of wardrobe item dicts (each with name, category, colors, style_tags, notes). May be empty.

**What it returns:**
A non-empty string with outfit suggestions. If wardrobe is populated, suggestions reference specific named wardrobe pieces. If wardrobe is empty, returns 2–3 sentences of general styling advice for the item (what types of pieces it pairs well with, what aesthetic it suits).

**What happens if it fails or returns nothing:**
If wardrobe['items'] is empty, the LLM is prompted for general styling advice rather than crashing. If the LLM call fails, returns the string: "Could not generate outfit suggestion. Please try again."

---

### Tool 3: create_fit_card

**What it does:**
Calls the Groq LLM to generate a short, casual, shareable caption (2–4 sentences) for a complete outfit featuring the thrifted item — the kind of thing someone would post on Instagram or TikTok.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by suggest_outfit. Must be non-empty.
- `new_item` (dict): The listing dict for the thrifted item. Uses title, price, and platform fields.

**What it returns:**
A 2–4 sentence string written in casual first-person social media voice. Mentions the item name, price, and platform naturally. Captures the outfit vibe specifically. Varies each time for different inputs (higher LLM temperature).

**What happens if it fails or returns nothing:**
If outfit is empty or whitespace-only, returns the error string: "Cannot generate a fit card without an outfit suggestion. Please retry your search." Does not raise an exception.

---

## Planning Loop

The agent runs the following conditional logic in order:

1. Parse the user query to extract description (str), size (str or None), and max_price (float or None) using simple string matching and regex. Store in session["parsed"].

2. Call search_listings(description, size, max_price). Store result in session["search_results"].
   - If results == []: set session["error"] = "No listings found..." and return session immediately. Do not proceed.
   - If results is non-empty: set session["selected_item"] = results[0] and continue.

3. Call suggest_outfit(session["selected_item"], session["wardrobe"]). Store result in session["outfit_suggestion"].

4. Call create_fit_card(session["outfit_suggestion"], session["selected_item"]). Store result in session["fit_card"].

5. Return the completed session. The agent never calls suggest_outfit or create_fit_card if search_listings returned nothing.

---

## State Management

All state is stored in a single session dict initialized at the start of run_agent(). Each tool writes its output into the session before the next tool is called:

- session["parsed"] — set after query parsing; contains description, size, max_price
- session["search_results"] — set after search_listings(); list of matching dicts
- session["selected_item"] — set to search_results[0]; passed directly into suggest_outfit()
- session["wardrobe"] — passed in at the start; never modified
- session["outfit_suggestion"] — set after suggest_outfit(); passed directly into create_fit_card()
- session["fit_card"] — set after create_fit_card(); final output shown to user
- session["error"] — set if any step fails early; signals the agent to stop

No data is re-entered by the user between steps. The selected_item from step 2 is the exact same dict object passed into step 3.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets session["error"] = "No listings found for your search. Try broadening your description, adjusting your size, or raising your price limit." Returns session immediately without calling the other tools. |
| suggest_outfit | Wardrobe is empty | Calls LLM with a prompt for general styling advice about the item (what it pairs with, what aesthetic it suits). Returns that string instead of crashing. |
| create_fit_card | Outfit input is empty or whitespace | Returns the string "Cannot generate a fit card without an outfit suggestion. Please retry your search." without raising an exception. |

---

## Architecture
User query (natural language)
│
▼
run_agent()
│
├─ Step 1: Parse query → session["parsed"] (description, size, max_price)
│
├─ Step 2: search_listings(description, size, max_price)
│               │
│               ├── results == [] ──► session["error"] = "No listings found..."
│               │                              │
│               │                              └──► return session (EARLY EXIT)
│               │
│               └── results non-empty ──► session["selected_item"] = results[0]
│                                                  │
├─ Step 3: suggest_outfit(selected_item, wardrobe) │
│               │                                  │
│               ├── wardrobe empty ──► LLM general styling advice
│               └── wardrobe populated ──► LLM specific outfit combos
│               │
│               └──► session["outfit_suggestion"] = result
│                                   │
├─ Step 4: create_fit_card(outfit_suggestion, selected_item)
│               │
│               └──► session["fit_card"] = result
│
└─ Step 5: return session

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

- **search_listings**: Give Claude the Tool 1 spec from this file (inputs, return value, failure mode) and ask it to implement the function using load_listings() from utils/data_loader.py. Verify the generated code: (1) filters by max_price and size when provided, (2) scores by keyword overlap against title, description, and style_tags, (3) returns [] on no match without raising. Test with 3 queries before trusting it.

- **suggest_outfit**: Give Claude the Tool 2 spec and ask it to implement using the Groq client with llama-3.3-70b-versatile. Verify it handles the empty wardrobe case with a separate LLM prompt path. Test with both get_example_wardrobe() and get_empty_wardrobe().

- **create_fit_card**: Give Claude the Tool 3 spec and ask it to implement with a higher LLM temperature (0.9). Verify it guards against empty outfit string and returns an error string (not an exception). Run 3 times on the same input and confirm outputs vary.

**Milestone 4 — Planning loop and state management:**

- Give Claude the Planning Loop section, State Management section, and the Architecture diagram from this file. Ask it to implement run_agent() in agent.py following those exact steps. Verify: (1) it branches on empty search results and returns early, (2) it stores values in the session dict at each step, (3) it does not call all three tools unconditionally. Test the no-results path explicitly before moving on.

---

## A Complete Interaction (Step by Step)

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query and extracts: description = "vintage graphic tee", size = None (not specified), max_price = 30.0. Stores in session["parsed"]. Calls search_listings("vintage graphic tee", size=None, max_price=30.0).

**Step 2:**
search_listings returns 3 matches scored by keyword overlap — for example: lst_006 "Graphic Tee — 2003 Tour Bootleg Style" ($24), lst_033 "Vintage Band Tee — Faded Grey" ($19), lst_015 "Vintage Graphic Hoodie — Faded Black" ($26). session["selected_item"] is set to lst_006 (top result). Results are non-empty so the agent continues.

**Step 3:**
The agent calls suggest_outfit(selected_item=lst_006, wardrobe=example_wardrobe). The wardrobe is non-empty so the LLM is given the item details and all 10 wardrobe pieces. The LLM returns something like: "Pair this boxy graphic tee with your baggy straight-leg dark wash jeans and chunky white sneakers for an easy 90s streetwear look. Tuck the front corner slightly for shape. For a grungier take, layer your vintage black denim jacket on top and swap the sneakers for black combat boots." Stored in session["outfit_suggestion"].

**Step 4:**
The agent calls create_fit_card(outfit=session["outfit_suggestion"], new_item=lst_006). The LLM generates a casual caption like: "found this faded 2003 bootleg tee on depop for $24 and it was made for my baggy jeans era 🖤 front tuck + chunky sneakers and we're good. full fit in my stories." Stored in session["fit_card"].

**Final output to user:**
The Gradio interface displays three panels: (1) the listing details for lst_006 including title, price, condition, and platform, (2) the outfit suggestion text, (3) the fit card caption.