def fmt_currency(value, symbol="₹", decimals=2):
    try:
        return f"{symbol}{value:,.{decimals}f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"

def fmt_pct(value, decimals=2):
    try:
        return f"{value*100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "0.00%"