import requests
from datetime import datetime, timedelta
import pytz
import pandas as pd

def stookwijzer(lat: float, lon: float):
    """Haalt Stookwijzer-advies en 4 voorspellingen op (0h, +6h, +12h, +18h) voor opgegeven coördinaten."""

    # --- Coördinaten omzetten (EPSG:4326 → EPSG:28992) ---
    x0, y0, f0, l0 = 155000, 463000, 52.15517440, 5.38720621
    Rp, Rq = [0,1,2,0,1,3,1,0,2], [1,1,1,3,0,1,3,2,3]
    Rpq = [190094.945,-11832.228,-114.221,-32.391,-0.705,-2.34,-0.608,-0.008,0.148]
    Sp, Sq = [1,0,2,1,3,0,2,1,0,1], [0,2,0,2,0,1,2,1,4,4]
    Spq = [309056.544,3638.893,73.077,-157.984,59.788,0.433,-6.439,-0.032,0.092,-0.054]
    df, dl = 0.36*(lat-f0), 0.36*(lon-l0)
    x = x0 + sum(Rpq[i]*(df**Rp[i])*(dl**Rq[i]) for i in range(9))
    y = y0 + sum(Spq[i]*(df**Sp[i])*(dl**Sq[i]) for i in range(10))

    # --- Data ophalen via RIVM WMS ---
    bbox = f"{x}%2C{y}%2C{x+10}%2C{y+10}"
    url = (
        "https://data.rivm.nl/geo/alo/wms?service=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo"
        "&QUERY_LAYERS=stookwijzer_v2&LAYERS=stookwijzer_v2&info_format=application/json"
        "&feature_count=1&I=139&J=222&WIDTH=256&HEIGHT=256&CRS=EPSG:28992&BBOX=" + bbox
    )

    try:
        props = requests.get(url, timeout=10).json().get("features", [{}])[0].get("properties", {})
    except Exception as e:
        print("Fout bij ophalen Stookwijzer:", e)
        return None

    # --- Hulpfuncties ---
    get = lambda p: str(props.get(p, "")).strip()
    kleur = lambda a: {"0": "code_yellow", "1": "code_orange", "2": "code_red"}.get(a, "")

    # --- Basiswaarden ---
    pc4 = get("pc4")
    wind_bft, wind = get("wind_bft"), get("wind")
    wind_ms = round(float(wind), 1) if wind else ""
    lki = get("lki")
    runtime = get("model_runtime")

    # --- Voorspelling genereren ---
    forecast = []
    if runtime:
        try:
            dt = datetime.strptime(runtime, "%d-%m-%Y %H:%M").astimezone(pytz.timezone("Europe/Amsterdam"))
            for offset in range(0, 19, 6):  # 0h, +6h, +12h, +18h
                forecast.append({
                    "model_runtime": runtime,
                    "lat": lat,
                    "lon": lon,
                    "datetime": (dt + timedelta(hours=offset)).isoformat(),
                    "pc4": pc4,
                    "advies": kleur(get(f"advies_{offset}")),
                    "wind_bft": wind_bft,
                    "wind_ms": wind_ms,
                    "lki": lki,
                    "final": get(f"definitief_{offset}") == "True"
                })
        except Exception as e:
            print("Fout bij verwerken van runtime:", e)
            return None
    else:
        print("Geen model_runtime beschikbaar.")
        return None

    # --- Resultaat als DataFrame teruggeven ---
    return pd.DataFrame(forecast)

if __name__ == "__main__":
    LAT, LON = 52.089770561127374, 5.109876746789877
    df = stookwijzer(LAT, LON)
    if df is not None:
        csv_file = "stookwijzer_output.csv"
        # If file exists, append without header, else write with header
        if os.path.isfile(csv_file):
            df.to_csv(csv_file, mode='a', header=False, index=False)
        else:
            df.to_csv(csv_file, mode='w', header=True, index=False)
