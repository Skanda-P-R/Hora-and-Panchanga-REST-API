# Swiss Ephemeris data

The bundled files cover 1200–2999 and were downloaded on 2026-07-08 from the
[`ephe` directory of the official Swiss Ephemeris repository](https://github.com/aloistr/swisseph/tree/master/ephe).
That repository states that its planetary files were rebuilt from JPL DE441 in
April 2026 and remain compatible with older Swiss Ephemeris releases.

| File | Purpose | SHA-256 |
|---|---|---|
| `hora_server/ephe/sepl_12.se1` | Adjacent Sun/planet range, 1200–1799 | `8dccace2557601a223d5f8a7cf64de4e6bbb8a82b9b130b95a54d49adfbe546d` |
| `hora_server/ephe/semo_12.se1` | Adjacent Moon range, 1200–1799 | `1c65fdbb854f350d3de36afc3e4ac126a53f360ae4f6dcb57beed7c690e7eb61` |
| `hora_server/ephe/sepl_18.se1` | Sun and major planets | `ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66` |
| `hora_server/ephe/semo_18.se1` | Moon | `1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7` |
| `hora_server/ephe/sepl_24.se1` | Adjacent Sun/planet range, 2400–2999 | `dea65ffc3ee39125eb1427ecfd578a208be2dd021f49fdfd4b8a130ccd5244f0` |
| `hora_server/ephe/semo_24.se1` | Adjacent Moon range, 2400–2999 | `62260992014e61d655c13733bb2d415ac23e8013d8ecf1d7714c237ea8f5b250` |

The public API remains intentionally limited to 1800–2399. The adjacent file
pairs ensure that previous-sunrise and next-transition searches at the public
range edges never fall back to a different ephemeris.

The server starts in strict mode and checks the calculation flags returned by
Swiss Ephemeris. It returns `503 ephemeris_unavailable` instead of silently
using Moshier calculations if these files are absent or outside their range.
Set `SWISS_EPHEMERIS_STRICT=false` only when a documented fallback is desired.

Swiss Ephemeris and `pyswisseph` are dual/commercially licensed or available
under AGPL terms. Confirm the applicable license before deployment; a
proprietary network service may require the professional Swiss Ephemeris
license. See the [official licensing documentation](https://www.astro.com/swisseph/).
