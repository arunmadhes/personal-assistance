# IndiaQuant Pro — Web PWA

Mobile-first Progressive Web App for NSE/BSE & Crypto analysis.

## Run Locally
```bash
pip install flask flask-cors yfinance pandas gunicorn
python app.py
# Open http://localhost:5000
```

## Deploy to Railway (FREE — recommended)
1. Go to https://railway.app and sign up free
2. Click "New Project" → "Deploy from GitHub"
3. Upload this folder or connect your GitHub repo
4. Railway auto-detects Python + Procfile and deploys
5. Get your URL like: https://indiaquant.up.railway.app

## Deploy to Render (FREE alternative)
1. Go to https://render.com → New Web Service
2. Connect repo, set Build Command: `pip install -r requirements.txt`
3. Set Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Free tier URL: https://indiaquant.onrender.com

## Install as Phone App (PWA)
### Android (Chrome)
1. Open your deployed URL in Chrome
2. Tap the 3-dot menu → "Add to Home screen"
3. Tap "Add" → App icon appears on home screen
4. Opens full-screen like a native app

### iPhone (Safari)
1. Open your URL in Safari
2. Tap the Share button (box with arrow)
3. Scroll down → "Add to Home Screen"
4. Tap "Add"

## Features
- Live NSE/BSE stock analysis (intraday + swing)
- 40+ crypto coins including SFP, WIF, PEPE
- Candlestick charts with EMA overlays
- Entry/Exit signals with targets and stop loss
- NSE Options CE/PE suggestions
- Position sizing (1% risk rule)
- Crypto trade signals with R:R ratios
- Watchlist with live prices
- Live market indexes strip
- Auto-refresh capability
- Works offline (cached shell)

## Files
- app.py — Flask backend + TA engine + API routes
- templates/index.html — Full PWA frontend
- static/sw.js — Service worker for offline
- static/icons/ — PWA icons
- requirements.txt — Python dependencies
- Procfile — For Railway/Render deployment
