
def to_float(price) -> float:
    try:
        return float(price)
    except (TypeError, ValueError):
        return 0.0

def format_price(price) -> str:
    try:
        return f"{float(price):.2f} €".replace(".", ",")
    except (TypeError, ValueError):
        return f"{price} €"