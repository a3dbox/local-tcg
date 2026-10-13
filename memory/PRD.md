# PokéBinder — PRD

## Original problem statement
Build me a web app docker project that I can use and my 7 year old can use to search, filter, view and track all past and future Pokémons and tcg cards, it should know about all variants and have images and price information. It should be possible to record owned cards, define sets to collect and help with knowing what's left to complete, it should have a way to quickly scan real Pokémon cards and recognise and open up the page for the card and have batch mode for scanning lots of cards into a collection quickly, search all the features of other online and mobile app version of this type of software for further reference and ideas for implementation, fully functional one shot to download, build in docker and host on local hardware, accounts so collections are kept separate.

## User choices
- Data: pokemontcg.io requested but down (HTTP 500) → TCGdex (free, no key, variants + TCGplayer/Cardmarket prices)
- Recognition: local/server-side (OpenCV card detection + Tesseract OCR + perceptual-hash fingerprint DB; optional Ollama vision LLM)
- Auth: email/password JWT (Bearer tokens, refresh)
- Same UI for everyone

## Architecture
- FastAPI backend: server.py (routes), auth.py, tcgdex.py (API client + Mongo cache), scanner.py (recognition + fingerprint index), models.py, database.py
- React frontend (Tailwind/shadcn), pages: Login, Dashboard, Search, CardDetail, Sets, SetDetail, Collection, Goals, Wishlist, Pokédex, PokemonCards, Scan, Settings
- Docker: docker-compose.yml (mongo, backend, frontend/nginx, optional caddy https profile), Caddyfile, .env.example, README.md

## Implemented (2026-06)
- Accounts with separate collections, admin seeding, brute-force lockout
- Card search with name/type/category/set/rarity/sort filters, load more
- Card detail: variants with per-variant owned qty and prices, full TCGplayer/Cardmarket price tables, attacks, wishlist, other printings
- Sets by series with owned progress; set detail with base/full/master progress, goals, owned/missing filter, quick add, cost to complete
- Goals, Wishlist, Collection (stats, value, sort, variant filter, CSV export, price refresh), Dashboard
- Pokédex (PokeAPI, 1025 species) → all cards for a Pokémon
- Scanner: single (auto-open card page) & batch (auto-capture, dedupe, variant/qty edit, bulk add), photo upload fallback for HTTP
- Fingerprint index builder (tracked sets / single set / all)
- Tested: 20/20 backend, 14/14 frontend flows

## Iteration 2 (2026-06)
- Binder view (9-pocket flippable pages), Family trading (compare, duplicates, give cards, activity), Price history (daily card & collection snapshots, charts)

## Iteration 3 (2026-06)
- Prices in GBP (Cardmarket EUR→GBP preferred, TCGplayer USD→GBP fallback, ECB rates via frankfurter.dev)
- Admin account management (/admin): create/edit/reset password/role/delete users
- Set icons in set drop-downs (pokemontcg.io symbol CDN, logo fallback)
- Custom sets (rule-based: name/dex/type/category/rarity/set/illustrator + hand-picked + exclusions)
- Storage locations (binder/case/box/deck/bulk) with per-copy placements, move, unassigned view, duplicates filter, scan destination
- Camera: auto-snap on steady+sharp frame, torch, camera switch, zoom, beep/vibrate, improved card edge detection
- Unit tests: backend 88 (pytest, fake TCGdex, throwaway DB), frontend 13 (jest)

## Backlog
- P1: Holo vs reverse-holo detection from photo; price history charts; binder page view
- P2: Import CSV; grading/condition values; trade list sharing between family accounts; multi-language cards
