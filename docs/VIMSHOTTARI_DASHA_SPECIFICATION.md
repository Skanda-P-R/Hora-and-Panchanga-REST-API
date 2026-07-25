# Vimshottari Dasha Specification v1.0

## Objective

Extend the existing Hora & Panchanga REST API with support for calculating **Vimshottari Dasha cycles** and intervals. The new feature will expose a JSON API endpoint:

```
GET /api/v1/dasha
```

This endpoint calculates Nakshatra-based Vimshottari Dasha timelines (Mahadashas, Antardashas, and optional Pratyantardashas) starting from the position of the Moon at birth or at a specific transit instant.

### Critical Requirements
- Maintain complete backward compatibility. No existing endpoints or JSON schemas shall be modified.
- Reuse the existing astronomy engine and Swiss Ephemeris wrapper. Do not duplicate astronomical calculations.
- Support both Natal (Birth) and Transit (Gochara) query modes.
- Support localization to Kannada (`lang=kan`) using the existing translation dictionary.
- Support custom year duration formats (standard Julian year or traditional 360-day Savana year).

---

## Vimshottari Dasha Astrological Calculation Rules

Vimshottari Dasha is a 120-year planetary cycle system in Vedic Astrology based on the sidereal longitude of the Moon at a reference time (natal birth or transit).

### 1. Dasha Lords and Durations
The cycle comprises 9 planetary periods (Mahadashas) in a fixed sequence, each with a specific duration in years:

| Order | Dasha Lord (English) | Kannada Translation | Abbreviation | Duration (Years) |
|---|---|---|---|---|
| 0 | Ketu | ಕೇತು | Ke | 7 |
| 1 | Venus | ಶುಕ್ರ | Ve | 20 |
| 2 | Sun | ಸೂರ್ಯ | Su | 6 |
| 3 | Moon | ಚಂದ್ರ | Mo | 10 |
| 4 | Mars | ಕುಜ | Ma | 7 |
| 5 | Rahu | ರಾಹು | Ra | 18 |
| 6 | Jupiter | ಗುರು | Ju | 16 |
| 7 | Saturn | ಶನಿ | Sa | 19 |
| 8 | Mercury | ಬುಧ | Me | 17 |

**Total Cycle Duration:** 120 Years.

### 2. Nakshatras and Lords
The 360° zodiac is divided into 27 Nakshatras of equal width ($13^\circ 20'$ or $13.333333^\circ$ each).
The order of Nakshatra lords cycles through the 9 dasha lords:

$$\text{Nakshatra Index} \in [0, 26]$$
$$\text{Lord Index} = \text{Nakshatra Index} \bmod 9$$

For example, Ashwini (index 0) is ruled by Ketu (index 0), Bharani (index 1) by Venus (index 1), ..., Magha (index 9) by Ketu (index 0).

### 3. Balance of Dasha at Birth/Query Time
Given the Moon's sidereal longitude $\lambda_M$:
1. **Nakshatra Index:** 
   $$N_{idx} = \lfloor \frac{\lambda_M}{360 / 27} \rfloor = \lfloor \frac{3 \lambda_M}{40} \rfloor$$
2. **Starting Lord Index:** 
   $$L_{idx} = N_{idx} \bmod 9$$
3. **Nakshatra Start Longitude:** 
   $$\lambda_{start} = N_{idx} \times \frac{40}{3}$$
4. **Moon Progress in Nakshatra:** 
   $$\Delta = \lambda_M - \lambda_{start}$$
5. **Fraction Completed:** 
   $$F_{completed} = \frac{\Delta}{40 / 3} = \frac{3 \Delta}{40}$$
6. **Fraction Remaining:** 
   $$F_{remaining} = 1.0 - F_{completed}$$
7. **Elapsed Duration (Years):** 
   $$Y_{elapsed} = F_{completed} \times \text{Duration}(L_{idx})$$
8. **Remaining Duration (Years):** 
   $$Y_{remaining} = F_{remaining} \times \text{Duration}(L_{idx})$$

### 4. Continuous Timeline Alignment
To prevent calendar alignment errors, we calculate the theoretical start date of the first Mahadasha:

$$t_{start} = t_{query} - (Y_{elapsed} \times D_{year})$$

Where $t_{query}$ is the input datetime, and $D_{year}$ is the year length in days (365.25 or 360).
From this $t_{start}$, we construct all subsequent periods contiguously. The actual birth/query time $t_{query}$ will fall precisely within the first Mahadasha.

### 5. Sub-period Division (Bhuktis/Antardashas)
Within a Mahadasha of planet $A$ (duration $Y_A$ years), the Antardasha of planet $B$ (duration $Y_B$ years) starts with $A$ and follows the same cyclic sequence. The duration of Antardasha $B$ is:

$$d_{AB} = \frac{Y_A \times Y_B}{120} \text{ years}$$

### 6. Sub-sub-period Division (Pratyantardashas)
Within an Antardasha of planet $B$ (duration $d_{AB}$ years), the Pratyantardasha of planet $C$ (duration $Y_C$ years) starts with $B$ and follows the cyclic sequence. The duration of Pratyantardasha $C$ is:

$$d_{ABC} = \frac{d_{AB} \times Y_C}{120} = \frac{Y_A \times Y_B \times Y_C}{14400} \text{ years}$$

---

## API Endpoint Specification

### `GET /api/v1/dasha`

Returns the Vimshottari Dasha timeline and details.

#### Query Parameters

| Parameter | Type | Required | Default | Description |
| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `lat` | Float | No | - | Latitude of the location (required if `location` is not provided). |
| `lon` | Float | No | - | Longitude of the location (required if `location` is not provided). |
| `location` | String | No | - | Name of a saved location to look up in the registry. |
| `datetime` | String | No | Current Time | ISO-8601 formatted datetime (e.g., `1990-01-01T12:00:00`). |
| `date` | String | No | - | Date portion (e.g., `1990-01-01`), used with `time` if `datetime` is not provided. |
| `time` | String | No | - | Time portion (e.g., `12:00:00`), used with `date` if `datetime` is not provided. |
| `timezone` | String | No | Inferred | Timezone identifier (e.g., `Asia/Kolkata`). |
| `ayanamsa` | String | No | `lahiri` | Ayanamsa type (`lahiri`, `raman`, `krishnamurti`, `fagan_bradley`). |
| `depth` | Integer | No | `2` | Detail level: `1` (Mahadashas), `2` (Mahadashas + Antardashas), `3` (+ Pratyantardashas). |
| `year_type` | String | No | `365.25` | Duration of dasha year in days: `365.25` (solar year) or `360` (Savana year). |
| `lang` | String | No | `en` | Language for response localization: `en` or `kan` (Kannada). |

---

### JSON Response Schema

```json
{
  "date": "1990-01-01",
  "datetime": "1990-01-01T12:00:00+05:30",
  "timezone": "Asia/Kolkata",
  "ayanamsa": "Lahiri",
  "year_type": "365.25",
  "moon": {
    "longitude": 313.4567,
    "degree_in_rasi": 13.4567,
    "rasi": "Aquarius",
    "rasi_number": 11,
    "nakshatra": "Shatabhisha",
    "nakshatra_number": 24,
    "nakshatra_lord": "Rahu"
  },
  "dasha_balance": {
    "lord": "Rahu",
    "total_years": 18.0,
    "elapsed_years": 0.1234,
    "remaining_years": 17.8766,
    "elapsed_fraction": 0.0068,
    "remaining_fraction": 0.9932
  },
  "active_dasha": {
    "mahadasha": "Rahu",
    "antardasha": "Rahu",
    "pratyantardasha": "Jupiter"
  },
  "timeline": [
    {
      "level": 1,
      "lord": "Rahu",
      "start": "1989-11-15T00:00:00+05:30",
      "end": "2007-11-15T00:00:00+05:30",
      "duration_years": 18.0,
      "sub_periods": [
        {
          "level": 2,
          "lord": "Rahu",
          "start": "1989-11-15T00:00:00+05:30",
          "end": "1992-07-27T00:00:00+05:30",
          "duration_years": 2.7,
          "sub_periods": []
        }
      ]
    }
  ]
}
```

---

### `GET /api/v1/dasha/birth`

Returns the birth Vimshottari Dasha timeline starting from the Moon's longitude at birth, but with `"active_dasha"` and `"dasha_balance"` calculated for the **current time of the request** (now) in the resolved local timezone of the request context.

It accepts the exact same query parameters as `GET /api/v1/dasha`.

**Example Scenario:**
If a person was born on `2004-03-18T17:30:00+05:30`:
- The starting lord (at birth) is **Mars**.
- The `"timeline"` contains the contiguous 120-year periods starting from 2004.
- In **2026**, calling `GET /api/v1/dasha/birth` returns:
  - `"active_dasha"`: `"mahadasha": "Jupiter"`, `"antardasha": "Saturn"` (which is the active cycle running in 2026).
  - `"dasha_balance"`: Calculated for the active **Jupiter** Mahadasha at the current moment of request in 2026 (showing the elapsed/remaining years and fraction of the Jupiter Mahadasha *now*).

---

## File Architecture Changes

To implement this specification, the following files will be added or modified:

1. **[NEW]** `hora_server/astrology/dasha.py`
   - Houses core mathematical logic for Vimshottari calculations.
   - Computes Nakshatra indexes, elapsed/remaining balances, and timelines.
2. **[MODIFY]** `hora_server/astrology/__init__.py`
   - Exports the new calculation methods.
3. **[MODIFY]** `hora_server/service.py`
   - Exposes a new `dasha()` method on `PanchangaService` to handle service layer coordination, date conversion, and active period detection.
4. **[MODIFY]** `hora_server/api/kundali.py`
   - Implements the `/dasha` endpoint, parses parameters, performs validation, and formats response JSON.

---

## Verification Plan

### Automated Tests
1. **Unit Tests (`tests/test_dasha.py`)**:
   - Verify Nakshatra calculations and starting lords for edge case Moon degrees (0°, 120°, 240°, 359.9°).
   - Validate dasha period durations sum up to 120 years exactly.
   - Verify timeline alignment logic (start date of first Mahadasha is exactly $Y_{elapsed}$ before the query datetime).
   - Validate year format conversions for both `365.25` and `360` day options.
   - Test JSON output structure and types.
   - Test localization values in Kannada.

### Manual Verification
1. Compare API outputs for a sample birth date and location (e.g. Bengaluru, Jan 1, 1990) against authoritative external calculators (such as Drik Panchang or Jagannatha Hora).
