# Panchanga Extension Specification

This specification documents the addition of calendar elements to the `/api/v1/panchanga` (and aggregate `/api/v1/all`) endpoint response.

## Background

The client requested additional fields from the Panchanga calculations to support a complete ritual/calendric reference:
1. **Samvatsara**: The name of the year in the 60-year Jovian cycle (South Indian / Shala era convention).
2. **Ayana**: The Sun's northward (`Uttarayana`) or southward (`Dakshinayana`) movement.
3. **Rutu**: The season (one of the six traditional seasons: `Vasanta`, `Grishma`, `Varsha`, `Sharad`, `Hemanta`, `Shishira`).
4. **Masa**: The lunar month name (e.g. `Ashadha` or `Adhika Ashadha`).
5. **Paksha**: The lunar fortnight (`Shukla` or `Krishna`).

---

## Calculations & Formulas

### 1. New Moon Conjunction Solver
To calculate the lunar month and Samvatsara, we locate the new moon ending (conjunction) immediately preceding and following the target instant `T`.
* A conjunction occurs when the tropical elongation `(Moon_tropical - Sun_tropical) % 360 == 0`.
* We approximate the preceding/following conjunction offset based on current elongation and average lunar motion (`~12.19` degrees/day).
* We solve for the exact time using the **Newton-Raphson** method on the elongation function:
  $$t_{n+1} = t_n - \frac{E(t_n)}{v_{\text{Moon}}(t_n) - v_{\text{Sun}}(t_n)}$$
  Since speeds are provided directly by Swiss Ephemeris (`swe.FLG_SPEED`), this converges in 2–3 iterations with microsecond precision.

### 2. Lunar Month (Masa)
In the Amanta system:
* Let $R_{\text{prev}}$ be the Sun's sidereal Rashi index ($0\dots11$) at the previous new moon.
* Let $R_{\text{next}}$ be the Sun's sidereal Rashi index ($0\dots11$) at the next new moon.
* If $R_{\text{prev}} == R_{\text{next}}$, no solar transit occurred during the month. This marks an **Adhika Masa** (intercalary month). The month name is `Adhika` + `MasaName[(R_prev + 1) % 12]`.
* If $R_{\text{prev}} \neq R_{\text{next}}$, it is a normal month (`Nija`) named after the transit Rashi: `MasaName[R_next]`.

### 3. Season (Rutu)
Based on the lunisolar month index ($0\dots11$, where $0 = \text{Chaitra}$):
* $$\text{RutuIndex} = \lfloor \text{MonthIndex} / 2 \rfloor$$
* This maps to the six seasons:
  * 0: `Vasanta` (Spring)
  * 1: `Grishma` (Summer)
  * 2: `Varsha` (Monsoon)
  * 3: `Sharad` (Autumn)
  * 4: `Hemanta` (Pre-winter)
  * 5: `Shishira` (Winter)

### 4. Solar Journey (Ayana)
Determined directly by the Sun's sidereal longitude at the requested instant:
* **Dakshinayana**: If Sun's sidereal longitude is in $[90^\circ, 270^\circ)$ (Cancer to Sagittarius).
* **Uttarayana**: Otherwise (Capricorn to Gemini).

### 5. Jovian Year Name (Samvatsara)
Determined by the Shalivahana Shaka Year:
* Ugadi (Chaitra Shukla Pratipada) increments the Shaka Year.
* If the current month is Magha or Phalguna (indices 10 or 11) and the Gregorian month is early (Jan–Apr), then:
  $$\text{ShakaYear} = \text{GregorianYear} - 79$$
  Otherwise:
  $$\text{ShakaYear} = \text{GregorianYear} - 78$$
* The 0-based index in the 60-year cycle is:
  $$\text{Index} = (\text{ShakaYear} + 11) \bmod 60$$
* Maps to `SAMVATSARAS[Index]`, starting with `Prabhava` (index 0).

---

## Response Schema Update

The `/api/v1/panchanga` and `/api/v1/all` responses will extend the `panchanga` block as follows:

```json
{
  "panchanga": {
    "tithi": "Shukla Dvitiya",
    "nakshatra": "Pushya",
    "yoga": "Vajra",
    "karana": "Balava",
    "vara": "Wednesday",
    "vara_sanskrit": "Budhavara",
    "samvatsara": "Parabhava",
    "ayana": "Dakshinayana",
    "rutu": "Grishma",
    "masa": "Ashadha",
    "paksha": "Shukla"
  }
}
```
