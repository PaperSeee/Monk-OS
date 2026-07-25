#!/usr/bin/env python3
"""
MONK-OS — snapshot automatique du patrimoine (sans ouvrir l'app).

Lancé chaque soir par launchd (com.monkos.snapshot) : recalcule le
patrimoine avec les prix du jour et met à jour le point du mois en cours
(UPSERT par month_key). La valeur figée d'un mois est donc toujours celle
de son dernier jour — un point par mois, jour fixe, aucun trou possible,
même sans jamais ouvrir l'app.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import (  # noqa: E402
    get_lt_capital,
    get_portfolio_holdings,
    get_crypto_wallet,
    record_wealth_snapshot,
)


def yf_symbol(coin: str):
    c = coin.upper()
    if c in ("USDT", "USDC", "DAI", "BUSD"):
        return None  # stablecoin ≈ 1 USD, converti via EURUSD
    return f"{c}-EUR"


def fetch_price(symbol: str):
    try:
        import yfinance as yf
        h = yf.Ticker(symbol).history(period="2d")
        if not h.empty:
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    return None


def main() -> int:
    epargne = get_lt_capital()

    # Bourse ETF : parts × prix live (repli : montant investi)
    bourse = 0.0
    for tk, d in get_portfolio_holdings().items():
        px = fetch_price(tk)
        bourse += d["parts"] * px if px else d["invested"]

    # Crypto : quantité × cours EUR (stablecoins ≈ 1 USD → EUR)
    fx = fetch_price("EURUSD=X")
    usd_to_eur = (1 / fx) if fx else 0.92
    crypto = 0.0
    for w in get_crypto_wallet():
        sym = yf_symbol(w["coin"])
        if sym is None:
            crypto += w["qty"] * usd_to_eur
        else:
            px = fetch_price(sym)
            if px:
                crypto += w["qty"] * px

    total = epargne + bourse + crypto
    if total <= 0:
        print("snapshot ignoré : patrimoine nul (prix indisponibles ?)")
        return 0

    record_wealth_snapshot(total, epargne, bourse, crypto)
    print(f"snapshot OK : total={total:.0f}€ (épargne={epargne:.0f}, "
          f"bourse={bourse:.0f}, crypto={crypto:.0f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
