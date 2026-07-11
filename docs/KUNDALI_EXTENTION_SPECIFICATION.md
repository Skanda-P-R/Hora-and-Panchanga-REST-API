
# Kundali Extension Specification v1.0

## Objective

Extend the existing Hora & Panchanga REST API with **current transit Kundali**
support while preserving complete backward compatibility.

### Critical Requirements

- No existing endpoint shall change its response.
- No existing JSON schema shall change.
- No existing calculation logic shall change.
- No changes to Hora, Panchanga, Muhurta, or astronomy engines.
- All new functionality must be additive.
- Existing clients (Scriptable widget, Android, Web) must continue to work
  without modification.

---

# Existing Architecture

```text
Client
      ↓
REST API
      ↓
Astronomy Engine
      ↓
Swiss Ephemeris
```

The Kundali engine becomes another independent consumer of the existing
astronomy engine.

```text
                 Swiss Ephemeris
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   Panchanga        Hora Engine     Kundali Engine
        │               │               │
        └───────────────┼───────────────┘
                        │
                     REST API
```

**No duplicated calculations.**

---

# New Modules

```text
hora_server/
    astrology/
        kundali.py

    render/
        south_chart.py
        north_chart.py
        chart_symbols.py

    api/
        kundali.py
```

---

# New Endpoints

## 1. JSON

```
GET /api/v1/kundali
```

Returns the current transit Kundali as JSON.

---

## 2. PNG

```
GET /api/v1/kundali/chart
```

Returns the rendered chart as PNG.

---

## 3. SVG (Optional)

```
GET /api/v1/kundali/svg
```

Returns SVG for scalable rendering.

---

# Query Parameters

Exactly the same as existing endpoints.

```
lat
lon
datetime (optional)
timezone (optional)
ayanamsa (optional)
```

No new mandatory parameters.

---

# Optional Parameters

```
chart_style=south
```

Supported values

```
south
north
east
```

Default

```
south
```

---

# JSON Response

```json
{
  "date": "...",
  "datetime": "...",
  "timezone": "...",

  "lagna": {
    "rasi": "Libra",
    "number": 7,
    "longitude": 199.8421,
    "degree_in_rasi": 19.8421
  },

  "houses": [
    {
      "house": 1,
      "rasi": "Libra",
      "planets": []
    }
  ],

  "planets": [
    {
      "planet": "Sun",
      "symbol": "Su",
      "longitude": 84.2279,
      "rasi": "Gemini",
      "house": 9,
      "retrograde": false
    }
  ],

  "ayanamsa": "Lahiri"
}
```

---

# Planets

Return

- Sun
- Moon
- Mars
- Mercury
- Jupiter
- Venus
- Saturn
- Rahu
- Ketu

Optional future support:

- Uranus
- Neptune
- Pluto

---

# Ascendant

Use Swiss Ephemeris:

- `houses_ex()`
- or `houses_ex2()`

Do **not** approximate.

Do **not** derive from sunrise.

Do **not** manually calculate local sidereal time.

Swiss Ephemeris is the authoritative source.

---

# Planet Positions

Reuse the existing astronomy engine.

Do **not** perform duplicate Swiss Ephemeris calculations.

Refactor reusable internal helpers if required.

---

# House System

Default

```
Whole Sign
```

Future optional systems

- Placidus
- Equal
- Sripati

---

# South Indian Renderer

Renderer input:

```
Kundali object
```

Renderer output:

```
PNG
```

or

```
SVG
```

Renderer performs **no astrology**.

Renderer performs **no calculations**.

It only draws.

---

# Rendering

Canvas

```
512 × 512
```

White background.

Black borders.

Dark text.

The South Indian layout is static.

Only the planet placements change.

---

# Planet Labels

- Su
- Mo
- Ma
- Me
- Ju
- Ve
- Sa
- Ra
- Ke
- As (Ascendant)

Retrograde planets append `(R)`.

Example

```
Sa(R)
```

Multiple planets in one house should stack vertically.

---

# PNG Endpoint

```
GET /api/v1/kundali/chart
```

Returns

```
Content-Type: image/png
```

No JSON wrapper.

---

# SVG Endpoint

Returns

```
image/svg+xml
```

---

# Scriptable Usage

```javascript
let req = new Request(
  BASE_URL + "/api/v1/kundali/chart?lat=...&lon=..."
);

let image = await req.loadImage();

widget.backgroundImage = image;
```

---

# JSON Usage

```javascript
let req = new Request(
  BASE_URL + "/api/v1/kundali?lat=...&lon=..."
);

let data = await req.loadJSON();
```

---

# Performance

Reuse existing Swiss calculations.

Only Ascendant requires an additional Swiss call.

Expected response time:

```
< 50 ms
```

excluding network latency.

---

# Caching

Cache key

- minute
- latitude
- longitude
- ayanamsa

PNG rendering may also be cached.

---

# Thread Safety

Continue using the existing Swiss Ephemeris lock.

Do not introduce additional locking.

---

# Testing

Verify against Drik Panchang:

- Ascendant
- Planet positions
- House placement
- Rashi
- Rahu/Ketu
- Retrograde status

Verify:

- JSON schema
- PNG rendering
- SVG rendering
- Existing endpoints remain unchanged
- `/api/v1/all` response remains backward compatible

---

# Backward Compatibility (Critical)

The following endpoints must remain untouched:

- GET /api/v1/all
- GET /api/v1/hora
- GET /api/v1/panchanga
- GET /api/v1/day
- GET /api/v1/calendar
- GET /api/v1/muhurta
- GET /api/v1/rahu
- GET /health
- GET /

No new fields should be added to these responses unless explicitly requested
through an opt-in parameter such as:

```
include=kundali
```

---

# Design Principles

1. Single source of truth: all astronomy comes from the existing Swiss
   Ephemeris engine.
2. Separation of concerns:
   - Kundali Engine → computes astrology
   - Renderers → draw charts
   - API → serializes responses
3. No duplicated Swiss Ephemeris work.
4. Renderer consumes the same Kundali model returned by the JSON endpoint.

Recommended architecture:

```text
Swiss Ephemeris
        ↓
Kundali Engine
        ↓
Unified Kundali Model
      ↙           ↘
 JSON API      PNG/SVG Renderer
```

This guarantees that JSON and rendered charts can never diverge and makes
future renderers (PDF, HTML, Android, Web) trivial to add.
