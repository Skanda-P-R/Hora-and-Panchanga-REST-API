# Hora & Panchanga REST Server Specification

## Goal

Build a Flask REST API that performs all astronomical and Vedic
astrology calculations on the server. Clients (Scriptable, iOS, Android,
Web) only consume JSON.

## Architecture

``` text
Clients -> HTTPS -> Flask API
                  |- Astronomy
                  |- Hora Engine
                  |- Panchanga Engine
                  |- Muhurta Engine
```

## Suggested Stack

-   Flask
-   pyswisseph (Swiss Ephemeris)
-   Astral
-   timezonefinder
-   zoneinfo/pytz
-   gunicorn
-   nginx
-   redis (optional)
-   sqlite/postgresql (optional)

## Project Structure

``` text
hora_server/
  app.py
  config.py
  requirements.txt
  api/
    hora.py
    panchanga.py
    calendar.py
    muhurta.py
  astronomy/
    sunrise.py
    planets.py
    moon.py
    sun.py
  astrology/
    hora.py
    tithi.py
    nakshatra.py
    yoga.py
    karana.py
    rahukalam.py
    gulika.py
    yamaganda.py
    abhijit.py
  utils/
    timezone.py
    datetime.py
    cache.py
  tests/
```

## Endpoints

-   GET /api/v1/hora
-   GET /api/v1/panchanga
-   GET /api/v1/day
-   GET /api/v1/planetary-hours
-   GET /api/v1/calendar
-   GET /api/v1/muhurta
-   GET /api/v1/rahu
-   GET /api/v1/all

### Query Parameters

-   lat
-   lon
-   datetime (ISO8601, optional)
-   timezone (optional)
-   ayanamsa (default Lahiri)

## Example Response

``` json
{
  "date":"2026-07-08",
  "location":"Bengaluru",
  "sunrise":"05:58",
  "sunset":"18:46",
  "hora":{
    "planet":"Jupiter",
    "symbol":"♃",
    "started":"10:36",
    "ends":"11:37",
    "remaining":"19 min",
    "next":"Mars"
  },
  "panchanga":{
    "tithi":"Shukla Panchami",
    "nakshatra":"Rohini",
    "yoga":"Siddha",
    "karana":"Bava",
    "vara":"Wednesday"
  },
  "rahu_kalam":"12:18-13:48",
  "gulika":"09:18-10:48",
  "yamaganda":"07:48-09:18",
  "abhijit":"12:01-12:49",
  "moon":{"rasi":"Vrishabha","nakshatra":"Rohini","pada":2},
  "sun":{"rasi":"Mithuna"},
  "ayanamsa":"Lahiri"
}
```

## Calculation Requirements

1.  Accurate sunrise/sunset from coordinates.
2.  Day/night hora lengths computed separately.
3.  Hora ruler sequence based on weekday.
4.  Panchanga: tithi, nakshatra, yoga, karana, vara.
5.  Rahu Kalam, Gulika, Yamaganda, Abhijit Muhurta.
6.  Offline calculations using Swiss Ephemeris.
7.  Stateless REST API.

## Future Features

-   Vimshottari Dasha
-   Gochara
-   Choghadiya
-   Panchapakshi
-   Festival calendar
-   Birth chart
-   Ashtakavarga
-   KP/Jaimini support

## Client Integration

Scriptable widget periodically calls: GET
/api/v1/all?lat=`<lat>`{=html}&lon=`<lon>`{=html}

Display: - Current hora - Remaining time - Next hora - Panchanga summary
