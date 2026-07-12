# Hora & Panchanga REST API — Implemented Specification

## 1. Document control

| Field | Value |
|---|---|
| Application version | 1.0.0 |
| API version | v1 |
| API prefix | /api/v1 |
| Status | As built |
| Supported Python | 3.11 |
| Public calculation range | 1800-01-01 through 2399-12-31 |
| Default accuracy profile | drik_lahiri_hindu_sunrise_v1 |

This document is the authoritative contract for the implemented application.
The historical input is retained separately in
[ORIGINAL_PROJECT_REQUIREMENTS.md](ORIGINAL_PROJECT_REQUIREMENTS.md).

The service is astrologically accurate under the declared Drik,
selected-ayanamsa, and Hindu-sunrise conventions. It is not intended to be
identical to every regional Panchanga, which may use different astronomical
or interpretive conventions.

## 2. Purpose and scope

The application provides a stateless JSON REST API for:

- sunrise, sunset, solar transit, and Vedic-day calculations;
- current and full-day planetary Hora calculations;
- Tithi, Nakshatra, Pada, Nitya Yoga, Karana, Vara, and Rashi;
- Panchanga transition times;
- Rahu Kalam, Gulika Kalam, Yamaganda, and Abhijit Muhurta;
- current transit Kundali with sidereal ascendant, whole-sign houses,
  classical visible planets, Rahu, and Ketu; and
- an aggregate response for mobile, web, and Scriptable clients.

All runtime calculations are local. No network request, database, session
state, or external geocoding service is required.

### 2.1 Non-goals

Version 1 does not provide:

- a universal good/bad muhurta recommendation;
- activity-specific muhurta selection;
- natal chart interpretation or birth-chart workflows;
- reverse geocoding or a city-name database;
- Vimshottari Dasha, Gochara, Choghadiya, or festivals;
- authentication, rate limiting, or CORS policy; or
- regional Panchanga profiles beyond the selectable ayanamsas and declared
  calculation conventions.

## 3. Architecture

~~~text
Client
  |
  | HTTPS in production
  v
nginx / load balancer
  |
  | HTTP
  v
Gunicorn sync workers
  |
  v
Flask application
  |- API blueprints
  |- PanchangaService
  |- Astronomy
  |  |- EphemerisEngine
  |  `- SolarCalculator
  |- Astrology
  |  |- Hora
  |  |- Panchanga
  |  |- Muhurta
  |  `- Kundali
  |- Render
  |  `- Kundali chart PNG/SVG renderers
  `- Utilities
     |- ISO-8601 and IANA timezone handling
     |- offline coordinate-to-timezone lookup
     `- stable JSON errors
~~~

The Flask application is created by an application factory. PySwissEph uses
process-global ephemeris path and sidereal-mode configuration. Every Swiss
operation is serialized by a process-wide reentrant lock, and the configured
ephemeris path is restored inside the lock. Production defaults therefore use
synchronous Gunicorn workers with one thread per worker.

## 4. Runtime dependencies

The direct dependencies are pinned:

| Dependency | Version | Purpose |
|---|---:|---|
| Flask | 3.1.3 | HTTP application and JSON API |
| pyswisseph | 2.10.3.2 | Swiss Ephemeris Python binding |
| timezonefinder | 8.2.4 | Offline coordinate-to-IANA-zone lookup |
| tzdata | 2026.2 | Reproducible IANA timezone data fallback |
| gunicorn | 26.0.0 | Production WSGI server |

The supported runtime is Python 3.11. Later Python versions can require a C
compiler for PySwissEph and are not claimed as supported without additional
CI validation.

## 5. Accuracy and astronomy profile

### 5.1 Ephemeris

- Swiss Ephemeris version 2.10.03 is used through pyswisseph.
- Sun and Moon positions use calc_ut with a UTC Julian day.
- Gregorian calendar conversion is always used.
- Positions are geocentric apparent ecliptic longitudes.
- Tropical and selected sidereal longitudes are computed for each request.
- The default sidereal mode is Lahiri.
- The returned ayanamsa angle uses the extended UT calculation and participates
  in backend verification.

Six Swiss data files are bundled as package data:

- sepl_12.se1 and semo_12.se1 for 1200–1799;
- sepl_18.se1 and semo_18.se1 for 1800–2399; and
- sepl_24.se1 and semo_24.se1 for 2400–2999.

The public input range remains 1800–2399. The adjacent files ensure that
previous-sunrise and next-transition searches at public range boundaries stay
on the Swiss backend. File origins and SHA-256 values are recorded in
[EPHEMERIS_DATA.md](../EPHEMERIS_DATA.md).

Strict mode is enabled by default. If a position calculation returns Moshier,
JPL, or mixed backend flags instead of the requested Swiss backend, the
request fails with 503 ephemeris_unavailable. When strict mode is explicitly
disabled, meta.ephemeris_backend reports the actual backend.

### 5.2 Supported ayanamsas

| Canonical query value | Display value | Accepted aliases |
|---|---|---|
| lahiri | Lahiri | chitrapaksha |
| raman | Raman | — |
| krishnamurti | Krishnamurti | kp |
| fagan_bradley | Fagan-Bradley | fagan, fagan-bradley |

Query values are case-insensitive; spaces are normalized to underscores. The
alternate query spelling ayanamsha is accepted for compatibility.

### 5.3 Solar-event convention

Sunrise and sunset use the Swiss BIT_HINDU_RISING convention:

- geocentric solar position;
- center of the solar disc;
- geometric horizon;
- no atmospheric refraction; and
- solar ecliptic latitude ignored by the Swiss Hindu-rising composite flag.

The selected events must form this strict UTC ordering:

~~~text
sunrise < meridian transit < sunset < next sunrise
~~~

Sunset is searched after sunrise, and the following sunrise is searched after
sunset. If a location/date does not provide one ordered local solar cycle,
the service returns 422 rather than fabricating a substitute.

The API exposes:

- solar_noon_at: the true Swiss upper-meridian transit; and
- daylight_midpoint_at: the elapsed-time midpoint between sunrise and sunset.

Abhijit uses the daylight division, not the meridian-transit timestamp.

### 5.4 Transition precision

Panchanga transitions are found by:

1. classifying the requested instant;
2. scanning forward in three-hour elapsed-time increments;
3. bracketing the first classification change; and
4. bisecting the bracket in UTC to at most one second.

The returned ends_at is the upper bracket and therefore lies on the new side
of the boundary. ISO timestamps preserve microseconds so serialization cannot
move the time back across that boundary.

The conceptual profile name drik_lahiri_hindu_sunrise_v1 documents this
combination of conventions. It is not currently emitted as a separate
response field; the individual conventions are exposed in meta.

## 6. HTTP conventions

### 6.1 Methods and media type

All application resources are read-only GET endpoints. Successful API data
responses and all error responses are JSON. The Kundali chart endpoints return
image/png or image/svg+xml directly without a JSON wrapper.

### 6.2 Common query parameters

Every endpoint under /api/v1 accepts:

| Parameter | Required | Contract |
|---|---:|---|
| lat | Yes | Finite WGS84 latitude from -90 through 90 |
| lon | Yes | Finite WGS84 longitude from -180 through 180 |
| datetime | No | ISO-8601 date or timestamp; defaults to current time |
| timezone | No | IANA timezone name; inferred offline when absent |
| ayanamsa | No | Supported sidereal mode; defaults to lahiri |

The alias ayanamsha is also accepted.

Kundali chart endpoints also accept optional chart_style. Supported values are
south, north, and east; the default is south.

In a URL query string, a positive UTC offset must encode the plus sign as
%2B.

### 6.3 Datetime rules

- An offset-aware timestamp defines an absolute instant.
- timezone controls local presentation, civil date, and ritual-day selection.
- An aware timestamp is converted to the selected timezone.
- A naive timestamp is interpreted in the selected timezone.
- A date-only value represents local noon.
- A nonexistent DST wall time is rejected.
- An ambiguous repeated wall time requires an explicit UTC offset.
- A civil date skipped by timezone legislation is rejected.
- Conversion overflow returns a typed 422 error.
- Supported request years are 1800 through 2399.

Elapsed durations and interval boundaries are calculated in UTC and then
converted to the selected timezone. This preserves correctness across DST
changes.

### 6.4 Base response fields

Most /api/v1 JSON responses include:

| Field | Type | Meaning |
|---|---|---|
| date | string | Legacy alias for vedic_day_date |
| local_date | string | Civil date of the requested instant |
| vedic_day_date | string | Date on which the containing sunrise occurred |
| datetime | string | Requested instant rendered in the selected timezone |
| timezone | string | Selected IANA timezone |
| location | string | Deterministic latitude,longitude label to six decimals |
| coordinates | object | Numeric latitude and longitude |
| ayanamsa | string | Selected display name |

Before sunrise, local_date and vedic_day_date can differ. No city name is
returned because the service intentionally has no reverse geocoder.

The compact Kundali JSON response is intentionally additive and does not use
the solar-day base envelope, because transit Kundali is an instant chart rather
than a Vedic-day resource. It includes date, datetime, timezone, lagna, houses,
planets, and ayanamsa.

### 6.5 Timestamp and numeric formatting

- Authoritative timestamps are offset-aware ISO-8601 strings with microseconds.
- Short HH:MM or HH:MM-HH:MM strings are display-only compatibility fields.
- Durations are reported in elapsed seconds and rounded to three decimals.
- Longitudes, Julian day, ayanamsa, and progress values are rounded to eight
  decimals.
- Kundali longitudes and degrees within rashi are rounded to four decimals.
- Limb progress is a fraction in the half-open range [0, 1).

## 7. Endpoint contracts

### 7.1 GET /

Returns service discovery information: service, version, health, and
endpoint_prefix. This endpoint does not require coordinates.

### 7.2 GET /health

Performs a real Swiss position calculation and returns status, service,
swiss_ephemeris_version, ephemeris_backend, and ephemeris_ready. In strict
mode, missing or unusable Swiss files produce a 503 response.

### 7.3 GET /api/v1/hora

Returns the base fields, solar fields, current hora, and meta.

The hora object contains:

| Field | Meaning |
|---|---|
| planet | Current ruler |
| symbol | Unicode planetary symbol |
| number | Global Hora number, 1–24 |
| period | day or night |
| period_number | Number within day/night, 1–12 |
| started / ends | Short display times |
| started_at / ends_at | Exact timestamps |
| remaining | Display minutes, rounded upward |
| remaining_seconds | Non-negative integer elapsed seconds |
| next | Next ruler |

### 7.4 GET /api/v1/planetary-hours

Returns the base fields, solar fields, a planetary_hours array of 24
contiguous items, and meta. Each item contains number, period, period_number,
planet, symbol, start, end, display, and is_current.

The first 12 items exactly tile sunrise to sunset. The remaining 12 exactly
tile sunset to next sunrise.

### 7.5 GET /api/v1/panchanga

Returns base fields, panchanga summary, panchanga_details, moon, sun, and meta.

The summary contains tithi, nakshatra, yoga, karana, vara, and vara_sanskrit.
Every limb detail contains name, one-based number, progress,
longitude_degrees, and ends_at. Tithi also contains paksha,
lunar_day_number (1–30), and paksha_day_number (1–15). Nakshatra also contains
pada (1–4).

The moon object contains rasi, nakshatra, pada, and sidereal_longitude. The sun
object contains rasi and sidereal_longitude.

### 7.6 GET /api/v1/day

Returns the base fields, solar fields, Vara, Sanskrit Vara, and meta.

Solar fields are sunrise, sunset, sunrise_at, sunset_at, next_sunrise_at,
solar_noon_at, daylight_midpoint_at, day_duration_seconds,
night_duration_seconds, day_hora_seconds, and night_hora_seconds.

### 7.7 GET /api/v1/calendar

Builds a chronological timeline for the selected local civil date and returns
base and solar fields, panchanga_at_sunrise, events, and meta.

Events include sunrise, sunset, and every in-date Tithi, Nakshatra, Yoga, and
Karana transition. Transition events contain type, at, from, and to.
Collection is capped defensively at four transitions per limb per civil day.
After each boundary the collector advances two elapsed seconds before
searching again.

### 7.8 GET /api/v1/muhurta

Returns the base fields, solar fields, a muhurta map, and meta. The keys are
rahu_kalam, gulika, yamaganda, and abhijit.

Each interval contains name, exact start/end, display, and duration_seconds.
Daylight-eighth intervals include day_eighth. An interval can also include
traditionally_auspicious and note.

This is a calculated interval response, not an activity-specific or universal
recommendation.

### 7.9 GET /api/v1/rahu

Returns the legacy rahu_kalam short display, rahu_kalam_details with exact
timestamps, related_intervals containing Gulika and Yamaganda, base and solar
fields, and meta.

### 7.10 GET /api/v1/all

Returns the mobile/widget aggregate:

- base and solar fields;
- current Hora;
- Panchanga summary and details;
- Sun and Moon;
- top-level rahu_kalam, gulika, yamaganda, and abhijit display strings;
- the exact muhurta interval map; and
- meta.

It intentionally excludes the full 24-Hora list and the calendar timeline.
It also intentionally excludes Kundali fields for backward compatibility.

### 7.11 GET /api/v1/kundali

Returns current transit Kundali JSON for the requested instant and location.
It uses the common lat, lon, datetime, timezone, and ayanamsa parameters.

The lagna object contains rasi, one-based number, absolute sidereal longitude,
and degree_in_rasi.

The houses array contains 12 whole-sign houses. Each item contains house,
rasi, and planets. House 1 is the lagna sign, and subsequent houses advance
one rashi at a time.

The planets array contains Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
Rahu, and Ketu. Each item contains planet, symbol, longitude, degree_in_rasi,
rasi, house, and retrograde. Rahu uses the Swiss mean lunar node. Ketu is
returned as the exact opposite point from Rahu and inherits the node's
retrograde flag.

### 7.12 GET /api/v1/kundali/chart

Returns a rendered Kundali chart as image/png. The default chart_style is
south. The renderer uses the same Kundali model as the JSON endpoint and does
not perform astrology calculations.

The canvas is 512 by 512 pixels with a white background, black borders, and
dark text. The South Indian chart uses a static-rashi outer layout. The four
middle cells are merged into one empty information panel containing the title
"Transit Kundali", local date, local time, and the latitude/longitude label.

### 7.13 GET /api/v1/kundali/svg

Returns the same rendered Kundali chart model as image/svg+xml. The SVG uses a
512 by 512 viewBox and the same chart_style values as the PNG endpoint.

### 7.14 Meta object

| Field | Meaning |
|---|---|
| engine | Swiss Ephemeris |
| engine_version | Runtime Swiss version |
| ephemeris_backend | swiss, moshier, jpl, or a mixed value |
| julian_day_ut | Gregorian UTC Julian day |
| ayanamsa_degrees | Selected apparent ayanamsa |
| longitude_model | geocentric apparent ecliptic |
| solar_event_convention | Human-readable Hindu-rising convention |
| solar_event_swiss_flag | BIT_HINDU_RISING |
| vedic_day_convention | sunrise to next sunrise |
| transition_tolerance_seconds | 1 |

## 8. Calculation rules

### 8.1 Vedic day and Vara

The Vedic day begins at local Hindu sunrise and ends at the following sunrise.
An instant before civil-date sunrise belongs to the previous Vedic date and
weekday. English Vara names are deterministic and do not depend on process
locale. Intervals are half-open: start is inclusive and end is exclusive.

### 8.2 Planetary Hora

~~~text
Saturn -> Jupiter -> Mars -> Sun -> Venus -> Mercury -> Moon -> repeat
~~~

| Weekday | First ruler |
|---|---|
| Monday | Moon |
| Tuesday | Mars |
| Wednesday | Mercury |
| Thursday | Jupiter |
| Friday | Venus |
| Saturday | Saturn |
| Sunday | Sun |

Day Hora length is the actual elapsed sunrise-to-sunset duration divided by
12. Night Hora length is the actual elapsed sunset-to-next-sunrise duration
divided by 12. The sequence continues at sunset and never resets there.

Exact sunrise begins daytime Hora 1. Exact sunset begins nighttime Hora 1.
The following exact sunrise begins the new weekday's cycle.

### 8.3 Tithi

Let S be tropical Sun longitude and M tropical Moon longitude:

~~~text
elongation = (M - S) mod 360
tithi_index = floor(elongation / 12)
~~~

Indices 0–14 are Shukla Pratipada through Purnima. Indices 15–29 are Krishna
Pratipada through Amavasya. Tithi is ayanamsa-independent because the
sidereal correction cancels in the angular difference.

### 8.4 Karana

~~~text
karana_half_index = floor(elongation / 6)
~~~

- index 0: Kimstughna;
- indices 1–56: repeating Bava, Balava, Kaulava, Taitila, Gara, Vanija,
  Vishti;
- index 57: Shakuni;
- index 58: Chatushpada; and
- index 59: Naga.

### 8.5 Nakshatra and Pada

Let Ms be the selected sidereal Moon longitude:

~~~text
nakshatra_index = floor(Ms / (360 / 27))
pada = floor((Ms mod (360 / 27)) / (360 / 108)) + 1
~~~

The standard 27-name order from Ashwini through Revati is used.

### 8.6 Nitya Yoga

Let Ss and Ms be selected sidereal Sun and Moon longitudes:

~~~text
yoga_index = floor(((Ss + Ms) mod 360) / (360 / 27))
~~~

The standard 27-name order from Vishkambha through Vaidhriti is used.

### 8.7 Rashi

~~~text
rashi_index = floor(sidereal_longitude / 30)
~~~

The Sanskrit sequence from Mesha through Meena is used.

### 8.8 Rahu, Gulika, and Yamaganda

Sunrise-to-sunset is divided into eight equal elapsed-time segments. In
Monday-through-Sunday order:

| Interval | Segment sequence |
|---|---|
| Rahu Kalam | 2, 7, 5, 6, 4, 3, 8 |
| Gulika Kalam | 6, 5, 4, 3, 2, 1, 7 |
| Yamaganda | 4, 3, 2, 1, 7, 6, 5 |

The implementation never substitutes fixed 90-minute blocks.

### 8.9 Abhijit

Abhijit is the eighth of 15 equal daylight muhurtas:

~~~text
start = sunrise + (7 / 15) * daylight
end   = sunrise + (8 / 15) * daylight
~~~

The interval is still returned on Wednesday with
traditionally_auspicious=false and a traditional caveat.

### 8.10 Transit Kundali

The Kundali endpoint calculates an instant transit chart, not a natal chart.
Ascendant is calculated through Swiss Ephemeris houses_ex with the selected
sidereal mode. It is not derived from sunrise or manually calculated local
sidereal time.

Whole Sign is the implemented house system. The lagna rashi is house 1, and
each following rashi is the next house. Planetary positions are selected
sidereal longitudes from Swiss Ephemeris with speed flags so retrograde status
can be reported. Rashi is floor(sidereal_longitude / 30) + 1. House is:

~~~text
house = ((planet_rashi - lagna_rashi) mod 12) + 1
~~~

Returned planet labels are Su, Mo, Ma, Me, Ju, Ve, Sa, Ra, and Ke. Rendered
charts append (R) for retrograde planets and include AS plus the ascendant
degree/minute within the rashi, formatted like 16°59', in the lagna rashi or
first house.

## 9. Error contract

~~~json
{
  "error": {
    "code": "machine_readable_code",
    "message": "Human-readable message",
    "details": {}
  }
}
~~~

### 9.1 HTTP 400

Typical codes are missing_parameter, invalid_parameter, invalid_timezone,
timezone_not_found, invalid_datetime, nonexistent_local_datetime,
ambiguous_local_datetime, and invalid_ayanamsa.

### 9.2 HTTP 422

Codes are datetime_out_of_range, solar_event_unavailable, and
kundali_unavailable. Solar-event unavailability includes polar day/night, an
event missing from the requested local date, or an unordered daily solar cycle.
Kundali unavailability means Swiss Ephemeris could not return the ascendant
for the requested instant and location.

### 9.3 HTTP 503

ephemeris_unavailable is returned when strict Swiss mode detects a fallback.

### 9.4 Other errors

Framework HTTP errors use a lowercase underscore code. Unexpected exceptions
are logged server-side and return a generic 500 internal_error without
exposing internals.

## 10. Configuration

| Environment variable | Default | Meaning |
|---|---|---|
| SE_EPHEMERIS_PATH | bundled hora_server/ephe | Swiss data path |
| SWISS_EPHEMERIS_STRICT | true | Reject non-Swiss fallback |
| DEFAULT_AYANAMSA | lahiri | Default sidereal mode |
| OBSERVER_ELEVATION_METERS | 0 | Observer height |
| ATMOSPHERIC_PRESSURE_HPA | 0 | Retained; Hindu rising ignores refraction |
| ATMOSPHERIC_TEMPERATURE_C | 15 | Retained; Hindu rising ignores refraction |
| BIND | 0.0.0.0:8000 | Gunicorn bind |
| WEB_CONCURRENCY | 2 | Synchronous worker count |
| GUNICORN_TIMEOUT | 30 | Worker timeout in seconds |

## 11. Deployment

### 11.1 Local development

~~~bash
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pytest
python app.py
~~~

### 11.2 Gunicorn

~~~bash
gunicorn --config gunicorn.conf.py app:app
~~~

The provided configuration uses synchronous workers, one thread per worker,
access logs on standard output, and errors on standard error.

### 11.3 Container

The Dockerfile uses Python 3.11 slim, installs pinned requirements, copies the
application and ephemeris data, runs as non-root UID 10001, exposes port 8000,
and starts Gunicorn.

### 11.4 HTTPS

Gunicorn serves plain HTTP. Production HTTPS terminates at a reverse proxy or
load balancer. deploy/nginx.conf.example provides an nginx TLS 1.2/1.3
template. The operator must supply the real hostname and certificates.

## 12. Verification and acceptance

The as-built validation baseline is:

- 50 passing tests;
- 97 percent statement coverage;
- successful wheel and source-distribution build;
- all six ephemeris files present in the wheel;
- Gunicorn startup verified;
- GET /health returned HTTP 200 with ephemeris_ready=true; and
- GET /api/v1/all and GET /api/v1/kundali returned HTTP 200 for the Bengaluru
  reference request.

Run:

~~~bash
pytest
pytest --cov=hora_server --cov-report=term-missing
~~~

The suite covers:

- all documented endpoints and common validation;
- Bengaluru on 2026-07-08 at 12:00 IST;
- Krishna Ashtami, Revati Pada 4, Atiganda, and Kaulava;
- Hindu sunrise and sunset reference tolerances;
- exact sunrise/sunset half-open Hora boundaries;
- separate unequal day/night Hora tiling;
- all seven weekday rulers and Kalam segment tables;
- Wednesday Abhijit behavior;
- pre-sunrise Vedic-day selection;
- DST gaps, folds, and elapsed-time arithmetic;
- a skipped civil date and timezone-conversion overflow;
- polar-day and unordered-solar-cycle errors;
- 1800 and 2399 strict-backend boundaries;
- 0/360-degree classification wrap;
- transition timestamps lying on the new side;
- concurrent ayanamsa isolation;
- process-global ephemeris-path restoration;
- chronological calendar events; and
- Kundali schema, sidereal ascendant, whole-sign house placement, Rahu/Ketu,
  retrograde status, PNG/SVG rendering, merged chart information panel, and
  chart_style validation; and
- representative calculation with network access disabled.

## 13. Compatibility notes

- The original example response is shape guidance, not a golden fixture. Its
  stated Sun, Moon, Tithi, Hora, and fixed Kalam periods are mutually
  inconsistent.
- Formula-derived Swiss results in this specification are normative.
- Short display times are not authoritative; clients needing precision must
  use the full timestamp fields.
- Before sunrise, date follows vedic_day_date for backward compatibility.
- /api/v1/all returns the preceding Vedic day's daylight-derived periods
  before sunrise. Clients asking for the upcoming civil day's timeline should
  query an instant on that civil day after sunrise or use /api/v1/calendar.
- /api/v1/all does not include Kundali fields. Clients needing chart data must
  call /api/v1/kundali, /api/v1/kundali/chart, or /api/v1/kundali/svg.
- Different ayanamsas, sunrise conventions, regional spellings, or ritual
  rules can legitimately produce different almanac values.
- Solar-dependent resources can be unavailable at polar locations.

## 14. Licensing

Swiss Ephemeris and PySwissEph are available under AGPL terms or applicable
professional/commercial licensing. A proprietary network deployment can
require a professional Swiss Ephemeris license. The repository owner must
review and choose the appropriate licensing path before public deployment.

The repository's own source-code license must be selected separately. Adding
a general repository LICENSE file does not override Swiss Ephemeris or
ephemeris-data obligations.

See [EPHEMERIS_DATA.md](../EPHEMERIS_DATA.md) for provenance and checksums.

## 15. Future work

Potential later versions may add authentication, rate limiting,
activity-specific muhurta rules, regional profiles, reverse geocoding,
Choghadiya, festival calendars, Vimshottari Dasha, Gochara, natal chart
workflows, divisional charts, additional house systems, and an OpenAPI schema.
