# Performance & Scalability Enhancement Specification

## Goal

Add Flask-Caching and Flask-Limiter without changing API behavior.

## Dependencies

Add to requirements.txt: - Flask-Caching - Flask-Limiter

## Caching

Configure: - CACHE_TYPE = "SimpleCache" - CACHE_DEFAULT_TIMEOUT = 60

Initialize once with the Flask app.

Decorate: - /api/v1/all - /api/v1/kundali - /api/v1/kundali/chart

using: `@cache.cached(timeout=60, query_string=True)`

## Coordinate normalization

Round before expensive calculations:

``` python
lat = round(lat, 4)
lon = round(lon, 4)
```

## Rate Limiting

Initialize Flask-Limiter using get_remote_address.

Limits:

-   /api/v1/all -\> 60/minute/IP
-   /api/v1/kundali -\> 60/minute/IP
-   /api/v1/kundali/chart -\> 60/minute/IP

PNG endpoint is cached, therefore repeated requests should become cache
hits.

## HTTP Cache Headers

Return:

Cache-Control: public, max-age=60

## Do Not Change

-   API schema
-   Endpoint URLs
-   Swiss Ephemeris logic
-   Panchanga calculations
-   Kundali calculations
-   Rendering logic
-   Widget compatibility

## Logging

If available log: - endpoint - request duration - cache hit/miss -
response status

## Tests

Add tests for: - cache hit - cache expiry - query-string cache
separation - coordinate normalization - HTTP 429 after limit exceeded -
limit reset - existing endpoints unchanged

## Documentation

Update: - README.md - docs/IMPLEMENTED_API_SPECIFICATION.md -
requirements.txt - Any architecture or deployment docs

Document: - Flask-Caching - Flask-Limiter - 60-second cache - 60/min/IP
rate limits - coordinate normalization - Cache-Control headers

## Acceptance

-   Existing clients continue to work.
-   Cached requests avoid repeated Swiss calculations.
-   Cached PNG requests avoid repeated rendering.
-   HTTP 429 returned after limit exceeded.
-   Tests pass.
