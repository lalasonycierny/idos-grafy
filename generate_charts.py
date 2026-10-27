import pandas as pd
import plotly.express as px
import plotly.io as pio

# 1. Načítanie dát priamo z vašej URL
url = "https://github.io"
try:
    df = pd.read_csv(url)
except Exception as e:
    print(f"Nepodarilo sa načítať dáta z URL, skúšam lokálny súbor. Chyba: {e}")
    df = pd.read_csv("data/obsadenost_data.csv")

# 2. Úprava dátových typov
df['cas'] = pd.to_datetime(df['cas'])

# Zoskupíme dáta podľa času a vlaku, aby sme videli celkový počet voľných miest vo vlaku v danom momente
df_vlak = df.groupby(['cas', 'vlak', 'vlak_popis'])['volne'].sum().reset_index()

# 3. Vytvorenie interaktívneho grafu pomocou Plotly
fig = px.line(
    df_vlak, 
    x='cas', 
    y='volne', 
    color='vlak',
    hover_data=['vlak_popis'],
    title='Vývoj celkového počtu voľných miest vo vlakoch v čase',
    labels={'cas': 'Čas merania', 'volne': 'Počet voľných miest spolu', 'vlak': 'Vlak'}
)

# Úprava dizajnu grafu
fig.update_layout(
    template="plotly_dark",
    xaxis_title="Dátum a čas merania",
    yaxis_title="Celkovo voľných miest",
    legend_title="Spoje"
)

# 4. Generovanie výsledného HTML kódu pre GitHub Pages
html_content = f"""
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDOS - Grafy obsadenosti</title>
    <style>
        body {{
            background-color: #111;
            color: #eee;
            font-family: sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{ color: #fff; }}
        .container {{ width: 90%; max-width: 1200px; margin-top: 20px; }}
        .footer {{ margin-top: 40px; font-size: 0.8em; color: #888; }}
    </style>
</head>
<body>
    <h1>Aktuálne štatistiky voľných miest</h1>
    <p>Dáta sú automaticky aktualizované pomocou GitHub Actions.</p>
    
    <div class="container">
        {pio.to_html(fig, full_html=False, include_plotlyjs='cdn')}
    </div>

    <div class="footer">
        Posledná aktualizácia grafov: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M:%S')}
    </div>
</body>
</html>
"""

# Uloženie ako index.html (tento súbor GitHub Pages zobrazí ako hlavnú stránku)
with open("indexx.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Graf úspešne vygenerovaný do index.html")
