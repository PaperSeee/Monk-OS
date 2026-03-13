# 🏰 MONK-OS v3 — Life & Wealth OS

**Premium fintech dashboard for managing long-term capital, mid-term trading, and risky investments.**

---

## 🚀 Quick Start

### MacOS / Linux (Recommended)

**Direct Python launcher (auto-opens browser):**
```bash
python3 launch.py
```

**Or using shell script:**
```bash
./monk-os.sh
```

### Windows

```bash
python launch.py
```

---

## 📋 Requirements

- **Python 3.8+**
- **Streamlit** — Install with:
  ```bash
  pip install streamlit yfinance
  ```

---

## 🏗️ Architecture

**MONK-OS v3** is a multipage Streamlit application with 3 main modules:

### 📊 Dashboard (app.py)
- Central hub with real-time KPI aggregation
- Navigation to all 3 investment pillars
- Unified currency & timezone settings

### 📈 MT Trading (pages/_2_MT_Trading.py)
- Prop firm challenge management
- Challenge funding & payout tracking
- USD-exclusive pricing

### 💰 Risk Investments (pages/_3_CT_Business.py)
- Crypto & speculative asset tracking
- Real-time gains/losses calculation
- Performance % monitoring

---

## 💾 Data Storage

All data persists locally in SQLite:
```
~/monk_os_data.db
```

No cloud sync, no external APIs for data storage.

---

## 🎨 Design

- **Dark theme** optimized for fintech dashboards
- **Uniform card design** for consistency
- **Real-time metrics** with color-coded performance
- **Responsive layout** for desktop

---

## 📱 Local-Only

- **No account required**
- **No authentication** (local machine trusted)
- **No data collection**
- **Portable** — Move the folder anywhere, works immediately

---

## 🛠️ Troubleshooting

### "Port 8503 is already in use"
```bash
# Find what's using port 8503
lsof -i :8503

# Kill it
kill -9 <PID>

# Or use a different port in launch.py
```

### "Streamlit not found"
```bash
pip install streamlit yfinance
```

### "Database errors"
The app auto-migrates. If issues persist, delete and restart:
```bash
rm ~/monk_os_data.db
python3 launch.py
```

---

## 📄 License

Personal use only.

---

**Built with ❤️ for independent wealth builders.**
