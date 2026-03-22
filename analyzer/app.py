"""
IndiaQuant Pro — Web Backend
Flask API serving TA engine + yfinance data
Run: pip install flask yfinance pandas && python app.py
"""

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json, math, os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ── Optional imports ──────────────────────────────────────
try:
    import yfinance as yf
    YF_OK = True
except ImportError:
    YF_OK = False

try:
    import pandas as pd
    PD_OK = True
except ImportError:
    PD_OK = False

# ═══════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════
QUICK_SYMS = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK",
    "SBIN","TATAMOTORS","BAJFINANCE","ADANIENT","WIPRO",
    "MARUTI","LTIM","AXISBANK","KOTAKBANK","SUNPHARMA",
    "TITAN","NESTLEIND","POWERGRID","NTPC","ONGC"
]

INDEX_SYMS = {
    "NIFTY 50":"^NSEI","SENSEX":"^BSESN",
    "BANKNIFTY":"^NSEBANK","NIFTY IT":"^CNXIT",
    "VIX":"^INDIAVIX","USD/INR":"INR=X"
}

CRYPTO_REGISTRY = {
    "BTC":("BTC-USD","Bitcoin","Layer 1","Store of Value"),
    "ETH":("ETH-USD","Ethereum","Layer 1","Smart Contracts"),
    "BNB":("BNB-USD","BNB","Exchange","CEX Token"),
    "SOL":("SOL-USD","Solana","Layer 1","High Speed"),
    "XRP":("XRP-USD","Ripple","Payment","Cross-border"),
    "ADA":("ADA-USD","Cardano","Layer 1","PoS Research"),
    "DOGE":("DOGE-USD","Dogecoin","Meme","Community"),
    "AVAX":("AVAX-USD","Avalanche","Layer 1","Multi-chain"),
    "DOT":("DOT-USD","Polkadot","Layer 0","Parachain"),
    "MATIC":("MATIC-USD","Polygon","Layer 2","ETH Scaling"),
    "LINK":("LINK-USD","Chainlink","Oracle","Data Feeds"),
    "LTC":("LTC-USD","Litecoin","Payment","Silver to BTC"),
    "UNI":("UNI-USD","Uniswap","DeFi","DEX"),
    "AAVE":("AAVE-USD","Aave","DeFi","Lending"),
    "ATOM":("ATOM-USD","Cosmos","Layer 0","IBC"),
    "NEAR":("NEAR-USD","NEAR Protocol","Layer 1","Sharding"),
    "APT":("APT-USD","Aptos","Layer 1","Move Lang"),
    "ARB":("ARB-USD","Arbitrum","Layer 2","ETH Scaling"),
    "OP":("OP-USD","Optimism","Layer 2","ETH Scaling"),
    "INJ":("INJ-USD","Injective","DeFi","Trading Chain"),
    "SUI":("SUI-USD","Sui","Layer 1","Move Lang"),
    "TON":("TON-USD","Toncoin","Layer 1","Telegram"),
    "SHIB":("SHIB-USD","Shiba Inu","Meme","Community"),
    "PEPE":("PEPE-USD","Pepe","Meme","Community"),
    "WIF":("WIF-USD","dogwifhat","Meme","Solana Meme"),
    "SFP":("SFP-USD","SafePal","Wallet","Hardware Wallet"),
    "SAFPAL":("SFP-USD","SafePal","Wallet","Hardware Wallet"),
    "TWT":("TWT-USD","Trust Wallet Token","Wallet","Trust Wallet"),
    "FET":("FET-USD","Fetch.ai","AI","Autonomous Agents"),
    "GRT":("GRT-USD","The Graph","Indexing","Web3 API"),
    "RUNE":("RUNE-USD","THORChain","Cross-chain","Native Swap"),
    "KAS":("KAS-USD","Kaspa","Layer 1","BlockDAG"),
    "SEI":("SEI-USD","Sei Network","Layer 1","Trading"),
    "FTM":("FTM-USD","Fantom","Layer 1","DAG"),
    "XLM":("XLM-USD","Stellar","Payment","Cross-border"),
    "VET":("VET-USD","VeChain","Supply Chain","Tracking"),
    "ALGO":("ALGO-USD","Algorand","Layer 1","PPoS"),
    "TRX":("TRX-USD","TRON","Layer 1","Content"),
    "BONK":("BONK-USD","Bonk","Meme","Solana Meme"),
    "XMR":("XMR-USD","Monero","Privacy","Anonymous"),
}

STOCK_DB = [
    ("RELIANCE","Reliance Industries","Energy","NSE"),
    ("TCS","Tata Consultancy Services","Technology","NSE"),
    ("HDFCBANK","HDFC Bank","Banking","NSE"),
    ("INFY","Infosys","Technology","NSE"),
    ("ICICIBANK","ICICI Bank","Banking","NSE"),
    ("HINDUNILVR","Hindustan Unilever","FMCG","NSE"),
    ("ITC","ITC Ltd","FMCG","NSE"),
    ("SBIN","State Bank of India","Banking","NSE"),
    ("BAJFINANCE","Bajaj Finance","NBFC","NSE"),
    ("BHARTIARTL","Bharti Airtel","Telecom","NSE"),
    ("KOTAKBANK","Kotak Mahindra Bank","Banking","NSE"),
    ("LT","Larsen & Toubro","Infrastructure","NSE"),
    ("AXISBANK","Axis Bank","Banking","NSE"),
    ("MARUTI","Maruti Suzuki","Auto","NSE"),
    ("SUNPHARMA","Sun Pharmaceutical","Pharma","NSE"),
    ("TATAMOTORS","Tata Motors","Auto","NSE"),
    ("WIPRO","Wipro","Technology","NSE"),
    ("TITAN","Titan Company","Consumer","NSE"),
    ("TECHM","Tech Mahindra","Technology","NSE"),
    ("HCLTECH","HCL Technologies","Technology","NSE"),
    ("NTPC","NTPC","Power","NSE"),
    ("ONGC","ONGC","Oil & Gas","NSE"),
    ("POWERGRID","Power Grid Corp","Power","NSE"),
    ("ADANIENT","Adani Enterprises","Conglomerate","NSE"),
    ("ZOMATO","Zomato","Technology","NSE"),
    ("NYKAA","FSN E-Commerce","Retail","NSE"),
    ("PAYTM","One 97 Communications","Fintech","NSE"),
    ("DMART","Avenue Supermarts","Retail","NSE"),
    ("HAL","Hindustan Aeronautics","Defence","NSE"),
    ("BEL","Bharat Electronics","Defence","NSE"),
    ("IRCTC","Indian Railway Catering","Tourism","NSE"),
    ("DLF","DLF","Real Estate","NSE"),
    ("NESTLEIND","Nestle India","FMCG","NSE"),
    ("LTIM","LTIMindtree","Technology","NSE"),
    ("BAJAJFINSV","Bajaj Finserv","Financial","NSE"),
    ("DRREDDY","Dr Reddy's Laboratories","Pharma","NSE"),
    ("CIPLA","Cipla","Pharma","NSE"),
    ("DIVISLAB","Divi's Laboratories","Pharma","NSE"),
    ("APOLLOHOSP","Apollo Hospitals","Healthcare","NSE"),
    ("HINDPETRO","Hindustan Petroleum","Oil & Gas","NSE"),
]

# ═══════════════════════════════════════════════════════════
#  TA ENGINE (pure Python, no tkinter dependency)
# ═══════════════════════════════════════════════════════════
class TAEngine:
    @staticmethod
    def ema(series, period):
        k = 2 / (period + 1)
        result = [series[0]]
        for v in series[1:]:
            result.append(v * k + result[-1] * (1 - k))
        return result

    @staticmethod
    def sma(series, period):
        result = []
        for i in range(len(series)):
            if i < period - 1: result.append(None)
            else: result.append(sum(series[i-period+1:i+1]) / period)
        return result

    @staticmethod
    def rsi(series, period=14):
        if len(series) < period + 1: return [50.0] * len(series)
        gains = losses = 0
        for i in range(1, period + 1):
            d = series[i] - series[i-1]
            if d >= 0: gains += d
            else: losses -= d
        avg_gain, avg_loss = gains/period, losses/period
        result = [None] * period
        result.append(100 - 100/(1 + avg_gain/(avg_loss or 1e-9)))
        for i in range(period+1, len(series)):
            d = series[i] - series[i-1]
            avg_gain = (avg_gain*(period-1)+(d if d>0 else 0))/period
            avg_loss = (avg_loss*(period-1)+(-d if d<0 else 0))/period
            result.append(100 - 100/(1 + avg_gain/(avg_loss or 1e-9)))
        return result

    @staticmethod
    def macd(series):
        e12 = TAEngine.ema(series, 12)
        e26 = TAEngine.ema(series, 26)
        line = [a-b for a,b in zip(e12,e26)]
        signal = TAEngine.ema(line, 9)
        hist = [a-b for a,b in zip(line,signal)]
        return line, signal, hist

    @staticmethod
    def bollinger(series, period=20):
        sma_vals = TAEngine.sma(series, period)
        upper, lower, mid = [], [], []
        for i, m in enumerate(sma_vals):
            if m is None:
                upper.append(None); lower.append(None); mid.append(None)
            else:
                sl = series[i-period+1:i+1]
                std = math.sqrt(sum((x-m)**2 for x in sl)/period)
                upper.append(m+2*std); lower.append(m-2*std); mid.append(m)
        return upper, lower, mid

    @staticmethod
    def atr(highs, lows, closes, period=14):
        tr = []
        for i in range(len(closes)):
            if i == 0: tr.append(highs[i]-lows[i])
            else: tr.append(max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])))
        return TAEngine.sma(tr, period)

    @staticmethod
    def vwap(closes, volumes):
        cv = vv = 0; result = []
        for c, v in zip(closes, volumes):
            cv += c*v; vv += v
            result.append(cv/(vv or 1))
        return result

    @staticmethod
    def stochastic(highs, lows, closes, period=14):
        result = []
        for i in range(len(closes)):
            if i < period-1: result.append(None)
            else:
                hh = max(highs[i-period+1:i+1]); ll = min(lows[i-period+1:i+1])
                result.append((closes[i]-ll)/(hh-ll or 1)*100)
        return result

    @staticmethod
    def williams_r(highs, lows, closes, period=14):
        result = []
        for i in range(len(closes)):
            if i < period-1: result.append(None)
            else:
                hh = max(highs[i-period+1:i+1]); ll = min(lows[i-period+1:i+1])
                result.append((hh-closes[i])/(hh-ll or 1)*-100)
        return result

    @staticmethod
    def adx(highs, lows, closes, period=14):
        if len(closes) < period*2: return 20.0, 20.0, 20.0
        dm_plus  = [max(highs[i]-highs[i-1],0) if highs[i]-highs[i-1]>lows[i-1]-lows[i] else 0 for i in range(1,len(closes))]
        dm_minus = [max(lows[i-1]-lows[i],0) if lows[i-1]-lows[i]>highs[i]-highs[i-1] else 0 for i in range(1,len(closes))]
        tr = [max(highs[i]-lows[i],abs(highs[i]-closes[i-1]),abs(lows[i]-closes[i-1])) for i in range(1,len(closes))]
        sm_tr = sum(tr[:period]); sm_p = sum(dm_plus[:period]); sm_m = sum(dm_minus[:period])
        di_p_list, di_m_list, dx_list = [], [], []
        for i in range(period, len(tr)):
            sm_tr=sm_tr-sm_tr/period+tr[i]; sm_p=sm_p-sm_p/period+dm_plus[i]; sm_m=sm_m-sm_m/period+dm_minus[i]
            dip=100*sm_p/(sm_tr or 1); dim=100*sm_m/(sm_tr or 1)
            di_p_list.append(dip); di_m_list.append(dim)
            dx_list.append(100*abs(dip-dim)/(dip+dim or 1))
        adx_val = sum(dx_list[-period:])/period if dx_list else 20.0
        return adx_val, (di_p_list[-1] if di_p_list else 20.0), (di_m_list[-1] if di_m_list else 20.0)

    @classmethod
    def full_analysis(cls, closes, volumes, highs, lows):
        n = len(closes)
        if n < 5: return None
        rsi_vals = cls.rsi(closes, 14)
        e9  = cls.ema(closes, 9);  e21 = cls.ema(closes, 21)
        e50 = cls.ema(closes, min(50,n-1)); e200 = cls.ema(closes, min(200,n-1))
        macd_line, macd_sig, macd_hist = cls.macd(closes)
        bb_upper, bb_lower, bb_mid = cls.bollinger(closes, 20)
        vwap_vals = cls.vwap(closes, volumes)
        atr_vals  = cls.atr(highs, lows, closes, 14)
        stoch_k   = cls.stochastic(highs, lows, closes, 14)
        will_r    = cls.williams_r(highs, lows, closes, 14)
        adx_val, di_plus, di_minus = cls.adx(highs, lows, closes, 14)

        lc=closes[-1]; lr=rsi_vals[-1] or 50; lm=macd_hist[-1]; pm=macd_hist[-2] if n>1 else 0
        le9=e9[-1]; le21=e21[-1]; le50=e50[-1]; le200=e200[-1]
        lv=vwap_vals[-1]; la=atr_vals[-1] or 1
        lst=stoch_k[-1]; lw=will_r[-1]
        lbu=bb_upper[-1]; lbl=bb_lower[-1]; lbm=bb_mid[-1]
        avg_vol=sum(volumes[-20:])/max(len(volumes[-20:]),1); cur_vol=volumes[-1]

        bull=bear=0; signals=[]
        def sc(cond,w,bm,sm):
            nonlocal bull,bear
            if cond: bull+=w; signals.append(("bull",bm))
            else: bear+=w; signals.append(("bear",sm))

        sc(lr<50,2,"RSI<50 oversold","RSI>50 overbought")
        sc(lr<30,1,"RSI oversold bounce","RSI overbought zone")
        sc(lm>0 and pm<=0,3,"MACD bullish cross","MACD bearish cross")
        sc(lm>0,1,"MACD histogram +","MACD histogram -")
        sc(lc>le9,2,"Price above EMA9","Price below EMA9")
        sc(le9>le21,2,"EMA9>EMA21 uptrend","EMA9<EMA21 downtrend")
        sc(lc>le50,1,"Above EMA50","Below EMA50")
        sc(lc>le200,1,"Above EMA200","Below EMA200")
        sc(lc>lv,1,"Price above VWAP","Price below VWAP")
        sc(lbl is not None and lc<lbl,2,"BB oversold bounce","BB overbought")
        sc(lst is not None and lst<20,1,"Stoch oversold","Stoch overbought")
        sc(cur_vol>avg_vol*1.3 and lc>closes[-2],1,"Volume breakout","Volume breakdown")
        sc(di_plus>di_minus,1,"DI+ > DI- bullish","DI- > DI+ bearish")

        total=bull+bear or 1; score=round(bull/total*100)
        if score>=75:   sig,act="BUY","STRONG BUY"
        elif score>=58: sig,act="BUY","BUY"
        elif score<=25: sig,act="SELL","STRONG SELL"
        elif score<=42: sig,act="SELL","SELL"
        else:           sig,act="HOLD","HOLD"

        support=min(lows[-20:]) if len(lows)>=20 else min(lows)
        resist =max(highs[-20:]) if len(highs)>=20 else max(highs)
        sl_dist=la*1.5
        sl_price=lc-sl_dist if sig=="BUY" else lc+sl_dist
        t1=lc+sl_dist*2.5 if sig=="BUY" else lc-sl_dist*2.5
        t2=lc+sl_dist*4.5 if sig=="BUY" else lc-sl_dist*4.5
        t3=lc+sl_dist*7.0 if sig=="BUY" else lc-sl_dist*7.0
        pclose=closes[-2] if n>1 else lc
        pivot=(highs[-1]+lows[-1]+pclose)/3
        r1=2*pivot-lows[-1]; s1=2*pivot-highs[-1]
        r2=pivot+(highs[-1]-lows[-1]); s2=pivot-(highs[-1]-lows[-1])

        obv=[0]
        for i in range(1,n):
            if closes[i]>closes[i-1]: obv.append(obv[-1]+volumes[i])
            elif closes[i]<closes[i-1]: obv.append(obv[-1]-volumes[i])
            else: obv.append(obv[-1])
        obv_trend="Rising" if obv[-1]>obv[-2] else "Falling"

        # Options suggestion
        step=50 if lc>10000 else 10 if lc>1000 else 5 if lc>100 else 2.5
        atm=round(lc/step)*step
        itm=atm-step if sig=="BUY" else atm+step
        otm=atm+step if sig=="BUY" else atm-step
        atm_prem=round(la*0.45,1)
        lot=15 if lc>5000 else 25 if lc>2000 else 50 if lc>500 else 100 if lc>100 else 250

        # Position sizing
        capital=500000; risk_amt=capital*0.01; sl_pts=abs(lc-sl_price)
        qty=max(1,int(risk_amt/max(sl_pts,0.01)))

        return {
            "signal":sig,"action":act,"score":score,"bull":bull,"bear":bear,
            "signals":signals,"rsi":lr,"macd_line":macd_line[-1],"macd_sig":macd_sig[-1],
            "macd_hist":lm,"prev_hist":pm,"ema9":le9,"ema21":le21,"ema50":le50,"ema200":le200,
            "vwap":lv,"atr":la,"bb_upper":lbu,"bb_lower":lbl,"bb_mid":lbm,
            "stoch_k":lst,"williams_r":lw,"adx":adx_val,"di_plus":di_plus,"di_minus":di_minus,
            "support":support,"resist":resist,"sl_price":sl_price,"t1":t1,"t2":t2,"t3":t3,
            "pivot":pivot,"r1":r1,"s1":s1,"r2":r2,"s2":s2,
            "vol_ratio":cur_vol/max(avg_vol,1),"obv_trend":obv_trend,
            # OHLC for charts
            "ema9_arr":e9[-100:],"ema21_arr":e21[-100:],"vwap_arr":vwap_vals[-100:],
            # Trade levels
            "entry":lc,"lot":lot,"atm":atm,"itm":itm,"otm":otm,"atm_prem":atm_prem,
            "qty":qty,"invest":qty*lc,"max_loss":risk_amt,
            "t1_profit":qty*abs(t1-lc),"t2_profit":qty*abs(t2-lc),
        }

# ═══════════════════════════════════════════════════════════
#  DATA FETCHER
# ═══════════════════════════════════════════════════════════
def fetch_ohlcv(symbol, period="5d", interval="1m"):
    if not YF_OK: return None, "yfinance not installed"
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty: return None, f"No data for {symbol}"
        return df, None
    except Exception as e:
        return None, str(e)

def df_to_lists(df):
    closes  = [float(x) for x in df["Close"].tolist()]
    opens   = [float(x) for x in df["Open"].tolist()] if "Open" in df.columns else closes
    highs   = [float(x) for x in df["High"].tolist()] if "High" in df.columns else closes
    lows    = [float(x) for x in df["Low"].tolist()]  if "Low"  in df.columns else closes
    volumes = [int(x)   for x in df["Volume"].tolist()]
    dates   = [str(d)[:16] for d in df.index.tolist()]
    return closes, opens, highs, lows, volumes, dates

def resolve_crypto(raw):
    up = raw.strip().upper()
    if up in CRYPTO_REGISTRY: return up, CRYPTO_REGISTRY[up][0]
    for k,v in CRYPTO_REGISTRY.items():
        if up in k.upper() or k.upper() in up: return k, v[0]
    lo = raw.strip().lower()
    for k,v in CRYPTO_REGISTRY.items():
        if v[1].lower().startswith(lo): return k, v[0]
    for k,v in CRYPTO_REGISTRY.items():
        if lo in v[1].lower(): return k, v[0]
    return up, f"{up}-USD"

# ═══════════════════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "IndiaQuant Pro",
        "short_name": "IndiaQuant",
        "description": "Live NSE/BSE & Crypto Analyzer",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#07090f",
        "theme_color": "#00ff9d",
        "orientation": "portrait-primary",
        "icons": [
            {"src":"/static/icons/icon-192.png","sizes":"192x192","type":"image/png"},
            {"src":"/static/icons/icon-512.png","sizes":"512x512","type":"image/png"}
        ]
    })

@app.route("/api/search")
def api_search():
    q = request.args.get("q","").strip().upper()
    if not q: return jsonify([])
    lo = q.lower()
    results = []
    # Stocks
    for sym,name,sector,mkt in STOCK_DB:
        if q in sym or lo in name.lower():
            results.append({"sym":sym,"name":name,"sector":sector,"type":"stock","yf":sym+".NS"})
    # Crypto
    for sym,(yf_t,name,cat,use) in CRYPTO_REGISTRY.items():
        if sym=="SAFPAL": continue
        if q in sym or lo in name.lower():
            results.append({"sym":sym,"name":name,"sector":cat,"type":"crypto","yf":yf_t})
    return jsonify(results[:12])

@app.route("/api/analyze/stock")
def api_analyze_stock():
    sym    = request.args.get("sym","").strip().upper()
    ex     = request.args.get("ex","NS")
    period = request.args.get("period","5d")
    interval = request.args.get("interval","1m")
    if not sym: return jsonify({"error":"Symbol required"}), 400

    full_sym = sym if "." in sym else f"{sym}.{ex}"

    # Intraday
    df_i, err = fetch_ohlcv(full_sym, period, interval)
    if err: return jsonify({"error": err}), 400
    closes,opens,highs,lows,volumes,dates = df_to_lists(df_i)

    # Swing
    df_s, _ = fetch_ohlcv(full_sym, "3mo", "1d")
    sc,so,sh,sl_s,sv,sd = df_to_lists(df_s) if df_s is not None else ([],[],[],[],[],[])

    ta  = TAEngine.full_analysis(closes,  volumes, highs,  lows)
    sta = TAEngine.full_analysis(sc, sv, sh, sl_s) if sc else None

    # Info
    info = {}
    try:
        tk_obj = yf.Ticker(full_sym)
        info = tk_obj.info or {}
    except Exception:
        pass

    lc   = closes[-1]
    prev = closes[-2] if len(closes)>1 else lc

    return jsonify({
        "sym": full_sym, "lc": lc, "prev": prev,
        "pct": (lc-prev)/prev*100 if prev else 0,
        "day_high": float(df_i["High"].max()),
        "day_low":  float(df_i["Low"].min()),
        "intra": {
            "dates":dates[-200:],"closes":closes[-200:],
            "opens":opens[-200:],"highs":highs[-200:],"lows":lows[-200:],
            "volumes":volumes[-200:]
        },
        "swing": {
            "dates":sd[-300:],"closes":sc[-300:],
            "opens":so[-300:],"highs":sh[-300:],"lows":sl_s[-300:],
            "volumes":sv[-300:]
        } if sc else None,
        "ta":  ta,
        "sta": sta,
        "info": {
            "longName":    info.get("longName",""),
            "sector":      info.get("sector",""),
            "industry":    info.get("industry",""),
            "marketCap":   info.get("marketCap"),
            "trailingPE":  info.get("trailingPE"),
            "trailingEps": info.get("trailingEps"),
            "dividendYield":info.get("dividendYield"),
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow":  info.get("fiftyTwoWeekLow"),
            "beta": info.get("beta"),
            "volume":      info.get("volume"),
            "previousClose":info.get("previousClose"),
        }
    })

@app.route("/api/analyze/crypto")
def api_analyze_crypto():
    raw    = request.args.get("sym","BTC")
    period = request.args.get("period","1mo")
    interval = request.args.get("interval","1h")

    canon, yf_sym = resolve_crypto(raw)

    # Try candidates
    df = None
    for candidate in [yf_sym, f"{canon}-USD", f"{canon}USDT=X"]:
        df_try, _ = fetch_ohlcv(candidate, period, interval)
        if df_try is not None and not df_try.empty:
            df = df_try; yf_sym = candidate; break

    if df is None:
        return jsonify({"error": f"No data for {raw}. Try exact Yahoo ticker e.g. BTC-USD"}), 400

    closes,opens,highs,lows,volumes,dates = df_to_lists(df)
    ta = TAEngine.full_analysis(closes, volumes, highs, lows)
    reg = CRYPTO_REGISTRY.get(canon, (yf_sym, canon, "Crypto", ""))

    lc   = closes[-1]
    prev = closes[-2] if len(closes)>1 else lc

    return jsonify({
        "sym": canon, "yf_sym": yf_sym,
        "name": reg[1], "category": reg[2], "use_case": reg[3],
        "lc": lc, "prev": prev,
        "pct": (lc-prev)/prev*100 if prev else 0,
        "ohlcv": {
            "dates":dates[-300:],"closes":closes[-300:],
            "opens":opens[-300:],"highs":highs[-300:],"lows":lows[-300:],
            "volumes":volumes[-300:]
        },
        "ta": ta
    })

@app.route("/api/indexes")
def api_indexes():
    result = {}
    for name, yf_sym in INDEX_SYMS.items():
        try:
            df, _ = fetch_ohlcv(yf_sym, "5d", "1d")
            if df is not None and not df.empty:
                c = [float(x) for x in df["Close"].tolist()]
                lc = c[-1]; prev = c[-2] if len(c)>1 else lc
                result[name] = {"price": lc, "pct": (lc-prev)/prev*100}
        except Exception:
            pass
    return jsonify(result)

@app.route("/api/watchlist/prices")
def api_watchlist_prices():
    syms = request.args.get("syms","").split(",")
    result = {}
    for sym in syms:
        sym = sym.strip()
        if not sym: continue
        try:
            full = sym if "." in sym else f"{sym}.NS"
            df, _ = fetch_ohlcv(full, "5d", "1d")
            if df is not None and not df.empty:
                c = [float(x) for x in df["Close"].tolist()]
                v = [int(x) for x in df["Volume"].tolist()]
                h = [float(x) for x in df["High"].tolist()]
                l = [float(x) for x in df["Low"].tolist()]
                lc=c[-1]; prev=c[-2] if len(c)>1 else lc
                ta = TAEngine.full_analysis(c,v,h,l) if len(c)>5 else None
                result[sym] = {"price":lc,"pct":(lc-prev)/prev*100,"signal":ta["action"] if ta else ""}
        except Exception:
            pass
    return jsonify(result)

@app.route("/api/symbols/quick")
def api_quick_syms():
    return jsonify({"stocks": QUICK_SYMS, "crypto": list(CRYPTO_REGISTRY.keys())[:20]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
