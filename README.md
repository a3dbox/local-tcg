# PokéBinder — self-hosted Pokémon TCG collection tracker

Search every Pokémon TCG card (past + newly released), see all variants, images and prices
(TCGplayer USD + Cardmarket EUR), track owned cards per account, set goals (base / full / master set),
see what's missing and the cost to complete, keep a wishlist, browse a full Pokédex, and **scan real cards**
(single or batch) with recognition that runs on your own server.

## Run it with Docker

```bash
cp .env.example .env        # edit JWT_SECRET, ADMIN_PASSWORD, SERVER_HOST (your server's LAN IP)
docker compose up -d --build
```
Open `http://<your-server-ip>:8080`, log in with the admin account or create an account for each family member
(every account has its own private collection, goals and wishlist).

### Live camera on phones (HTTPS)
Browsers only allow the live camera over HTTPS (or `localhost`). Over plain HTTP the scanner still works with
**Take photo / Upload photos** (opens the phone camera app; batch mode accepts many photos at once).
For the live camera + auto batch scanning on your LAN, set `SERVER_HOST` in `.env` to your server IP and run:
```bash
docker compose --profile https up -d --build
```
Then open `https://<SERVER_HOST>:8443` and accept the self-signed certificate warning once.

## How the scanner works (all local)
1. OpenCV finds the card in the photo and straightens it.
2. Tesseract OCR reads the collector number (e.g. `136/189`) and the name.
3. The number narrows candidates to sets with that card count; the name is used as a fallback.
4. A perceptual-hash "fingerprint" of the photo (whole card + artwork + colour) is compared with fingerprints of
   official card images, which picks the exact printing (the same Pokémon in different sets has different art/borders).
5. Fingerprints are stored in MongoDB and grow as you scan. **Settings → Scanner card database** can pre-index your
   tracked sets or all ~20k cards for faster, more robust matching (even when the number can't be read).
6. Optional: set `OLLAMA_URL` (e.g. `http://192.168.1.10:11434`) and `OLLAMA_MODEL` (e.g. `qwen2.5vl` or `llava`) to have a
   local vision LLM read the name/number as an extra signal.

Note: Holo vs Reverse Holo of the same card share the same artwork, so the scanner suggests the first variant —
change it in the batch queue or on the card page.

## Data sources
- Cards, sets, variants, prices: [TCGdex](https://tcgdex.dev) (free, no key) — cached in MongoDB.
- Pokédex: [PokeAPI](https://pokeapi.co).

## Dev layout
- `backend/` FastAPI (`server.py`, `auth.py`, `tcgdex.py`, `scanner.py`), `requirements.docker.txt` for the image
- `frontend/` React (CRA + Tailwind), served by nginx which proxies `/api` to the backend
