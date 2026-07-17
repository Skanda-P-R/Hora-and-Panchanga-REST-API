# Hora & Panchanga REST API

A stateless Flask API for Hora, Panchanga, solar-day, Kalam, and Abhijit
calculations. All calculations run locally; clients only consume JSON.

## Documentation

- [Implemented API specification](docs/IMPLEMENTED_API_SPECIFICATION.md) is
  the authoritative contract for version 1.
- [Birth Chart and Location specification](docs/BIRTH_CHART_AND_LOCATION_SPECIFICATION.md)
  documents the additive birth chart, any-date Panchanga, and location registry features.
- [Session Security specification](docs/SESSION_SECURITY_SPECIFICATION.md)
  documents the passwordless device-bound session security architecture.
- [Kundali extension specification](docs/KUNDALI_EXTENTION_SPECIFICATION.md)
  documents the additive current-transit Kundali endpoints.
- [Original project requirements](docs/ORIGINAL_PROJECT_REQUIREMENTS.md)
  preserve the historical input specification for traceability.
- [Ephemeris data](EPHEMERIS_DATA.md) records the bundled data provenance,
  checksums, strict-mode behavior, and licensing considerations.

## Accuracy profile

The default profile is `drik_lahiri_hindu_sunrise_v1`:

- Swiss Ephemeris 2.10.03 through `pyswisseph`.
- Bundled Swiss planetary/lunar data rebuilt from JPL DE441. The API covers
  1800–2399, with adjacent files included so edge transition searches remain
  on the Swiss backend. Strict verification prevents silent fallback.
- Geocentric apparent ecliptic Sun and Moon longitudes from `calc_ut`.
- Lahiri (`SIDM_LAHIRI`) sidereal mode by default.
- Swiss `BIT_HINDU_RISING`: geocentric solar-disc center at the geometric
  horizon, no atmospheric refraction.
- Vara and planetary day run from sunrise to the following sunrise.
- Day and night horas are divided separately in elapsed time.
- Panchanga transitions are bracketed and bisected to within one second.
- IANA timezone rules and offline coordinate lookup.

These conventions are explicit because different regional Panchangas can use
different ayanamsas, sunrise definitions, spellings, or Wednesday Abhijit
rules. The API returns its active conventions in `meta`.

The sample JSON in the original specification is treated as shape guidance,
not a golden calculation. Its stated Sun, Moon, tithi, horas, and fixed-length
Kalam blocks are mutually inconsistent. Tests instead use Swiss Ephemeris
positions and a published Bengaluru reference day.

## Performance controls

All `/api/v1` calculation endpoints use a 60-second in-process `SimpleCache`
keyed by the full query string. They also return
`Cache-Control: public, max-age=60` and are limited to `60/minute` per client
IP address. Latitude and longitude are normalized to four decimals before
calculation.

## Run locally

Python 3.11 is the supported runtime. The pinned PySwissEph release provides a
3.11 wheel; later Python versions would require a compiler and are not claimed
as supported without additional CI coverage.

```bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest
python app.py
```

The development server listens on `http://127.0.0.1:8000`. For production,
use the included synchronous Gunicorn configuration:

```bash
gunicorn --config gunicorn.conf.py app:app
```

Or build the self-contained image:

```bash
docker build -t hora-panchanga .
docker run --rm -p 8000:8000 hora-panchanga
```

Gunicorn serves plain HTTP and should sit behind TLS termination in production.
[`deploy/nginx.conf.example`](deploy/nginx.conf.example) provides the HTTPS
reverse-proxy shape from the specification; replace its hostname and
certificate paths for the deployment environment.

## User administration

When session security is enabled, you must pre-register usernames before they can connect. Usernames and device bindings are stored in `instance/users.json`.

### Pre-register a user
Pre-register a new username so they can log in and bind their device UUID on first access:
```bash
flask add-user <username>
```

### Reset a user's bound device
If a user changes their phone or gets locked out, reset their bound device UUID and active token:
```bash
flask reset-device <username>
```

### Remove a user
To delete a user entirely and revoke their session:
```bash
flask remove-user <username>
```


## Authentication

Every endpoint under `/api/v1/*` (except the login endpoint `/api/v1/auth/login`) requires session authentication.

### Login
- **Endpoint**: `POST /api/v1/auth/login`
- **Request Payload**:
  ```json
  {
    "username": "your-username",
    "device_uuid": "your-device-uuid"
  }
  ```
- **Response**:
  ```json
  {
    "token": "session-token-string"
  }
  ```
  *Note: The first time a username is used to log in, it binds to the provided `device_uuid`. Subsequent logins from a different `device_uuid` will be rejected.*

### Authenticating Requests
Pass the session token in the `Authorization` header of all subsequent API calls:
```http
Authorization: Bearer <token>
```

## Request parameters

Every `/api/v1/*` endpoint accepts the same query parameters. Alternatively, coordinates can be resolved using a saved `location` parameter name.

| Parameter | Required | Meaning |
|---|---:|---|
| `lat` | yes | WGS84 latitude, `-90..90` (required only if `location` is absent) |
| `lon` | yes | WGS84 longitude, `-180..180` (required only if `location` is absent) |
| `location` | no | Case-insensitive name of a saved location or favorite city from `locations.json`. Resolves coordinates & timezone automatically. |
| `datetime` | no | ISO-8601 instant; defaults to now. |
| `date` | no | Alias for `datetime`. Combined with `time` if both are specified; otherwise defaults to local noon of that date (e.g. `date=2026-07-20`). |
| `time` | no | 24-hour time format (e.g. `13:46` or `13:46:00`). Combined with `date` if both are specified. |
| `timezone` | no | IANA zone. If absent, resolved offline or from saved location registry. |
| `ayanamsa` | no | `lahiri` (default), `raman`, `krishnamurti`, or `fagan_bradley` |
| `lang` | no | `en` (default) or `kan` (translates returned values to Kannada) |

An offset-aware `datetime`/`date` defines the instant; `timezone` defines local
presentation and the ritual date. Naive timestamps are interpreted in the
resolved zone. Nonexistent DST times are rejected, and ambiguous repeated
times require an explicit offset.

Example (`+` must be URL-encoded as `%2B`):

```bash
curl 'http://127.0.0.1:8000/api/v1/all?lat=12.9716&lon=77.5946&datetime=2026-07-08T12:00:00%2B05:30&timezone=Asia%2FKolkata'
```

All authoritative times are full offset-aware ISO-8601 values. Short
`HH:MM` fields are included for widget compatibility.

`location` remains a string for compatibility with the specification and uses
the deterministic coordinate label (for example `"12.971600,77.594600"`),
because the offline stack has no reverse geocoder. Exact numeric values are in
`coordinates`. Responses distinguish `local_date` from `vedic_day_date`; the
legacy `date` field follows the Vedic day and can therefore be the preceding
civil date before sunrise.

## Endpoints

| Endpoint | Result |
|---|---|
| `GET /api/v1/hora` | Current unequal planetary hour, remaining time, and next ruler |
| `GET /api/v1/planetary-hours` | All 12 day and 12 night horas for the containing Vedic day |
| `GET /api/v1/panchanga` | Tithi, nakshatra/pada, nitya yoga, karana, vara, Sun/Moon rashi, samvatsara, ayana, rutu, masa, paksha, transitions |
| `GET /api/v1/day` | Sunrise, sunset, next sunrise, solar noon, and elapsed durations |
| `GET /api/v1/calendar` | Chronological solar and Panchanga transition timeline for one local civil date |
| `GET /api/v1/muhurta` | Rahu Kalam, Gulika, Yamaganda, and Abhijit intervals |
| `GET /api/v1/rahu` | Rahu Kalam display plus exact `rahu_kalam_details`, Gulika, and Yamaganda intervals |
| `GET /api/v1/all` | Compact aggregate intended for Scriptable/mobile clients |
| `GET /api/v1/kundali` | Current transit Kundali JSON with sidereal lagna, whole-sign houses, planets, Rahu, and Ketu |
| `GET /api/v1/kundali/chart` | Rendered Transit Kundali chart PNG; optional `chart_style=south|north|east` and `lang=en|kan` |
| `GET /api/v1/kundali/svg` | Rendered Transit Kundali chart SVG; optional `chart_style=south|north|east` and `lang=en|kan` |
| `GET /api/v1/kundali/birth` | Birth Chart (Janma Kundali) JSON; optional `name` parameter |
| `GET /api/v1/kundali/birth/chart` | Rendered Birth Chart PNG with optional `name` drawn in the center |
| `GET /api/v1/kundali/birth/svg` | Rendered Birth Chart SVG with optional `name` drawn in the center |
| `GET /api/v1/locations` | List all saved locations |
| `POST /api/v1/locations` | Save or update a custom location (payload: JSON with `name`, `latitude`, `longitude`, optional `timezone`, `description`) |
| `DELETE /api/v1/locations/<name>` | Delete a saved location |
| `GET /api/v1/favorites` | List all favorite cities |
| `POST /api/v1/favorites` | Save or update a favorite city (payload: JSON with `name`, `latitude`, `longitude`, optional `timezone`, `country`) |
| `DELETE /api/v1/favorites/<name>` | Delete a favorite city |
| `GET /health` | Process health and Swiss Ephemeris version |

`/muhurta` returns calculated named intervals, not a universal good/bad
recommendation. Activity-specific muhurta rules and natal-chart analysis are
outside the supplied specification. Wednesday Abhijit is returned with a
traditional caveat instead of being silently removed.

## Formula summary

For tropical Sun/Moon longitudes `S` and `M`, and Lahiri sidereal longitudes
`Ss` and `Ms`:

- Tithi: `floor(((M - S) mod 360) / 12)`
- Karana half: `floor(((M - S) mod 360) / 6)`
- Nakshatra: `floor(Ms / (360 / 27))`
- Pada: `floor((Ms mod (360 / 27)) / (360 / 108)) + 1`
- Nitya yoga: `floor(((Ss + Ms) mod 360) / (360 / 27))`
- Rashi: `floor(sidereal_longitude / 30)`
- Masa: Named after the sidereal zodiac sign the Sun enters during the Amanta month (New Moon to New Moon). An intercalary month with no solar transit is prefixed with `Adhika`.
- Rutu (Season): `floor(masa_index / 2)` (Vasanta, Grishma, Varsha, Sharad, Hemanta, Shishira).
- Ayana: `Dakshinayana` when Sun sidereal longitude is in `[90, 270)`, otherwise `Uttarayana`.
- Samvatsara (60-year cycle): `(Shaka_Year + 11) % 60`. Shaka Year increments at Ugadi.

Rahu, Gulika, and Yamaganda use weekday-specific eighths of the actual
sunrise-to-sunset duration. Abhijit is the eighth of 15 equal daylight
muhurtas. No fixed 90-minute approximation is used.

## Configuration

| Environment variable | Default |
|---|---|
| `SE_EPHEMERIS_PATH` | bundled `hora_server/ephe/` directory |
| `SWISS_EPHEMERIS_STRICT` | `true` |
| `DEFAULT_AYANAMSA` | `lahiri` |
| `OBSERVER_ELEVATION_METERS` | `0` |
| `ATMOSPHERIC_PRESSURE_HPA` | `0` (unused by Hindu rising) |
| `ATMOSPHERIC_TEMPERATURE_C` | `15` (unused by Hindu rising) |
| `WEB_CONCURRENCY` | `2` synchronous workers |

Solar-dependent endpoints return `422 solar_event_unavailable` during polar
day/night instead of inventing a twilight substitute. The bundled data range
is enforced as 1800–2399. See [EPHEMERIS_DATA.md](EPHEMERIS_DATA.md) for data
hashes, provenance, strict-mode behavior, and the Swiss Ephemeris licensing
decision required before production deployment.
