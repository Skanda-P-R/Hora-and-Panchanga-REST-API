# Implementation Specification — Birth Chart, Any-Date Selection, and Saved Locations (JSON-based)

This specification details the technical design and API contracts for four new features added to the Hora & Panchanga REST API, using a lightweight JSON file instead of a SQL database for persistence.

## 1. Architectural Strategy & Versioning

### API Versioning Recommendation: `/api/v1`
We recommend keeping the endpoints within the `/api/v1` namespace rather than creating `/api/v2`.
- **Additivity**: All changes are additive. No existing client integration or response payload schema is broken.
- **Maintainability**: A `/api/v2` namespace would either duplicate all unchanged endpoints (such as `/panchanga`, `/hora`, `/muhurta`, etc.) or force clients to mix namespaces.

---

## 2. Feature Details & Specifications

### Feature A: Birth Chart (Janma Kundali)
Allows generating a natal chart for a specific person given a name, date, time, and coordinates of birth.

- **JSON Endpoint**: `GET /api/v1/kundali/birth`
- **PNG Chart Endpoint**: `GET /api/v1/kundali/birth/chart`
- **SVG Chart Endpoint**: `GET /api/v1/kundali/birth/svg`

#### Query Parameters
- `lat` (float, required unless registry reference is used)
- `lon` (float, required unless registry reference is used)
- `timezone` (string, optional)
- `datetime` / `date` (string, optional)
- `time` (string, optional) — Birth time in 24-hour format (e.g. `13:46`). Combined with `date` if `datetime` is not specified.
- `ayanamsa` (string, optional)
- `lang` (string, optional, `en` or `kan`)
- `chart_style` (string, optional, `south`, `north`, `east`)
- `name` (string, optional) — Name of the birth person to draw in the chart center.

#### Rendering Pipeline Reuse
The rendering pipeline (`hora_server/render`) is completely reused.
- If `name` is passed, the center title displays as `[Name] - Birth Chart` (or translated `[Name] - ಜನನ ಕುಂಡಲಿ` in Kannada) instead of the default `Transit Kundali`.
- If `name` is omitted, the title defaults to `Janma Kundali` or `ಜನನ ಕುಂಡಲಿ`.

---

### Feature B: Panchanga for Any Date & Time
Allows querying calculations for any past or future date and time (within 1800-2399).

- **Implementation**: The existing `datetime` query parameter is supplemented with both `date` and `time` options.
- **Behavior**: 
  - If `datetime` is provided, it is parsed directly.
  - If `datetime` is absent, but both `date` (e.g. `2026-07-20`) and `time` (e.g. `13:46` or `13:46:00`) are provided, they are combined as `[date]T[time]` and parsed.
  - If only `date` is provided (e.g. `date=2026-07-20`), it resolves to local noon (12:00:00 PM) in the calculated timezone.
  - If all three are absent, the application defaults to the current UTC timestamp.

---

### Feature C: Multiple Saved Locations & Favorite Cities
To avoid the overhead of a database, we store saved locations and favorite cities in a local `locations.json` file inside the application instance folder (`instance/locations.json`).

#### JSON Registry Format
```json
{
  "saved_locations": {
    "Home": {
      "latitude": 12.9716,
      "longitude": 77.5946,
      "timezone": "Asia/Kolkata",
      "description": "My primary residence"
    }
  },
  "favorite_cities": {
    "Bengaluru": {
      "latitude": 12.9716,
      "longitude": 77.5946,
      "timezone": "Asia/Kolkata"
    }
  }
}
```

#### CRUD REST Endpoints
We expose dedicated endpoints to manage this file registry. Writes are synchronized using a reentrant lock to ensure thread safety.

**Locations Management**:
- `GET /api/v1/locations` — Retrieve all saved locations.
- `POST /api/v1/locations` — Create/update a saved location.
  - JSON payload: `{ "name": "Home", "latitude": 12.9716, "longitude": 77.5946, "timezone": "Asia/Kolkata", "description": "My primary residence" }`
- `DELETE /api/v1/locations/<name>` — Remove a saved location.

**Favorite Cities Management**:
- `GET /api/v1/favorites` — Retrieve all favorite cities.
- `POST /api/v1/favorites` — Create/update a favorite city.
  - JSON payload: `{ "name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "timezone": "Asia/Kolkata" }`
- `DELETE /api/v1/favorites/<name>` — Remove a favorite city.

#### Calculation Coordinate Overrides
All calculation endpoints (e.g. `/panchanga`, `/muhurta`, `/kundali`, `/kundali/birth`) will support:
- `location` — case-insensitive name of a saved location or favorite city from `locations.json`.

If present and found in the registry, the coordinates (`latitude`, `longitude`) and `timezone` are used automatically, overriding standard `lat` / `lon` parameters.

---

## 3. Implementation Plan Tasks

1. **Registry Module (`hora_server/registry.py`)**:
   - `LocationRegistry` class for reading/writing `instance/locations.json` with thread safety.
2. **REST Endpoints (`hora_server/api/locations.py`)**:
   - Implement the Blueprints and endpoints for Saved Locations and Favorite Cities.
   - Register the Blueprint under `/api/v1`.
3. **Calculation Service Integration (`hora_server/service.py`)**:
   - Integrate the registry lookup inside `PanchangaService.request_context()`.
   - Support `date` query parameter.
4. **Birth Chart Endpoints (`hora_server/api/kundali.py`)**:
   - Implement the `/kundali/birth` JSON, PNG, and SVG routes.
   - Customize rendering title via `name` argument.
5. **Verify and Test (`tests/`)**:
   - Write pytest test suite for all registry CRUD operations, overrides, and birth chart endpoints.
6. **Documentation Updates**:
   - Update `README.md` and `docs/IMPLEMENTED_API_SPECIFICATION.md` to document all new features, endpoints, and the location override system.
