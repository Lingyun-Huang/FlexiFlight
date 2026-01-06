# Flexiflight

This is a Flight Planning Agent. The goal of this agent is to take **blurry, flexible user travel requirements** and return **ranked trip options with reasoning**, including price, stops, travel time, and other trade-offs. The agent does **not need to book flights**, only search, compare, and explain.

Here are the requirements:

1. **Input Handling**:

   The system accepts a single free-form natural language string describing the user’s travel intent.
   The agent parses this input into structured constraints, explores multiple feasible trip strategies, and returns a ranked list of trip options

   Example invocation
   ```
   python Flexiflight.py "Help me find round‑trip flights from Ottawa that visit both France and Italy, in either order, with one week in each country, before returning to Ottawa."
   ```

   The agent must be able to interpret and reason over the following types of flexible requirements:

   - Flexible dates (e.g., "May or June", "~3 weeks", "maximize weekends to minimize PTO")
   - Multiple departure/arrival airport options (e.g., "To anywhere in Caribbean except for X")
   - Flexible routing
      - Support one way
      - Support round trip
      - Support stopovers: you intentionally stay in an intermediate city for more than 24 hours
      - Support open jaw: you fly into one city, and fly out from another city

   The agent should users to optionally filtering by
      - Maximum number of stops
      - Airlines to exclude
      - Airlines to include
      - Number of carry-on bags
      - Maximum total price
      - Preferred outbound departure time window
      - Preferred return departure time window
      - Maximum layover duration
      - Excluded connection airports
      - Maximum total travel duration (door-to-door)

2. **Evaluation Criteria**:
   - Total cost including luggage
   - Total number of stops
   - Total duration
   - Overnight layovers
   - Risk (tight connections)
   - Visa requirements
   - Airline preferences (e.g., avoid low-cost carriers)
   - Convenience / user-friendly routing

3. **Data Sources**:
   - SerpAPI (For MVP)
   - If SerpAPI can not handle it, use **light scraping** (Google Flights or Skyscanner)
   - For scraping:
     - Use **Playwright** or similar
     - Minimal stealth settings
     - Use home IP, low request volume
     - Only scrape top candidate routes (after pruning)
     - Implement caching to avoid repeated requests

4. **Processing Flow**:
   - User Input
   - Requirements Interprator (LLM)
   - Routing Strategy Generator for Flexible trip (LLM) (Optional)
   - Flight Data Fetcher: SerpAPI
   - Option Ranker (Code + LLM)
   - Explanation Generator (LLM)

5. **Output**:
   - List of top N options (e.g., 3–5)
   - For each option, include:
     - Total cost
     - Trip dates
     - Stops and layovers
     - Airlines
     - PTO days required
     - Risk or connection notes
     - Short explanation why this option is good / trade-offs

6. **Constraints**:
   - Do not attempt booking
   - Keep SerpAPI call/scraping volume minimal
   - Make caching optional
   - Focus on **reasoning + comparison**, not just raw results

7. **Tech stack**:
   - python
   - cli interface
   - pydantic
   - langgraph
   - SerpAPI (google-search-results): https://serpapi.com/google-flights-api
