import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

# 1. Načítanie dát priamo z vašej URL adresy repozitára
url = "https://github.io"
try:
    df = pd.read_csv(url)
except Exception as e:
    print(f"Nepodarilo sa načítať dáta z URL, skúšam lokálny súbor. Chyba: {e}")
    df = pd.read_csv("data/obsadenost_data.csv")

# 2. Úprava dátových typov
df['cas'] = pd.to_datetime(df['cas'])
df['den'] = pd.to_datetime(df['den']).dt.date

# --- GRAF 1: Časový vývoj voľných miest ---
df_vlak = df.groupby(['cas', 'vlak', 'vlak_popis'])['volne'].sum().reset_index()
fig1 = px.line(
    df_vlak, 
    x='cas', 
    y='volne', 
    color='vlak',
    hover_data=['vlak_popis'],
    title='Vývoj celkového počtu voľných miest vo vlakoch v čase',
    labels={'cas': 'Čas merania', 'volne': 'Počet voľných miest spolu', 'vlak': 'Vlak'}
)
fig1.update_layout(template="plotly_dark", xaxis_title="Dátum a čas", yaxis_title="Voľné miesta")

# --- GRAF 2: Plnenie vozňov (Heatmap) ---
idx_last = df.groupby(['den', 'vlak', 'vozen'])['cas'].idxmax()
df_last = df.loc[idx_last].copy()

kapacity = df.groupby(['vlak', 'vozen'])['volne'].max().reset_index().rename(columns={'volne': 'kapacita'})
df_last = df_last.merge(kapacity, on=['vlak', 'vozen'], how='left')
df_last['obsadenost_pct'] = ((df_last['kapacita'] - df_last['volne']) / df_last['kapacita'] * 100).clip(lower=0).round(0)

df_heatmap = df_last.groupby(['vlak', 'vozen'])['obsadenost_pct'].mean().unstack().fillna(0)

fig2 = px.imshow(
    df_heatmap,
    labels=dict(x="Vozeň", y="Vlak", color="Obsadenosť (%)"),
    x=df_heatmap.columns,
    y=df_heatmap.index,
    color_continuous_scale="Viridis",
    title="Priemerná obsadenosť vozňov pri poslednom meraní (%)"
)
fig2.update_layout(template="plotly_dark")

# --- GRAF 3: Predaj miest podľa hodiny dňa ---
df['hodina'] = df['cas'].dt.hour
df_sorted = df.sort_values(['vlak', 'vozen', 'cas'])
df_sorted['zmena'] = df_sorted.groupby(['vlak', 'vozen'])['volne'].diff()

df_predaj = df_sorted.dropna(subset=['zmena']).copy()
df_predaj['obsadene'] = df_predaj['zmena'].apply(lambda x: abs(x) if x < 0 else 0)
df_predaj['uvolnene'] = df_predaj['zmena'].apply(lambda x: x if x > 0 else 0)

df_hodiny = df_predaj.groupby('hodina')[['obsadene', 'uvolnene']].mean().reset_index()

fig3 = go.Figure()
fig3.add_trace(go.Bar(x=df_hodiny['hodina'], y=df_hodiny['obsadene'], name='Obsadené miesta', marker_color='crimson'))
fig3.add_trace(go.Bar(x=df_hodiny['hodina'], y=df_hodiny['uvolnene'], name='Uvoľnené miesta (Storná)', marker_color='lightseagreen'))
fig3.update_layout(
    template="plotly_dark",
    barmode='group',
    title='Priemerná dynamika zmien kapacity podľa hodiny dňa',
    xaxis_title='Hodina dňa',
    yaxis_title='Priemerný počet miest',
    xaxis=dict(tickmode='linear', tick0=0, dtick=1)
)

# --- ŠTATISTIKA 4: Uvoľnené miesta (Storná) - Tabuľka ---
df_storna = df_predaj[df_predaj['zmena'] > 0].sort_values('cas', ascending=False).head(15)
storna_rows = ""
for _, r in df_storna.iterrows():
    storna_rows += f"<tr><td>{r['cas'].strftime('%d.%m. %H:%M')}</td><td>{r['vlak']}</td><td>{r['vozen']}</td><td>+{int(r['zmena'])} miesta</td></tr>"

# --- Generovanie výsledného HTML ---
html_content = f"""
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDOS - Pokročilé štatistiky obsadenosti</title>
    <style>
        body {{
            background-color: #111;
            color: #eee;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{ color: #fff; margin-bottom: 5px; }}
        h2 {{ color: #f0a500; margin-top: 40px; width: 90%; max-width: 1200px; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        p {{ color: #bbb; }}
        .container {{ width: 90%; max-width: 1200px; margin-top: 10px; }}
        table {{
            width: 90%; max-width: 1200px;
            border-collapse: collapse;
            margin-top: 15px;
            background-color: #1a1a1a;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{ background-color: #2c2c2c; color: #f0a500; }}
        tr:hover {{ background-color: #252525; }}
        .footer {{ margin-top: 60px; font-size: 0.8em; color: #888; text-align: center; width: 100%; }}
    </style>
</head>
<body>
    <h1>Súhrnné štatistiky obsadenosti vlakov</h1>
    <p>Interaktívne prehľady generované automaticky z dát vášho repozitára.</p>
    
    <h2>1. Časový vývoj voľných miest</h2>
    <div class="container">
        {pio.to_html(fig1, full_html=False, include_plotlyjs='cdn')}
    </div>

    <h2>2. Plnenie jednotlivých vozňov</h2>
    <div class="container">
        {pio.to_html(fig2, full_html=False, include_plotlyjs='false')}
    </div>

    <h2>3. Dynamika nákupov a storna počas dňa</h2>
    <div class="container">
        {pio.to_html(fig3, full_html=False, include_plotlyjs='false')}
    </div>

    <h2>4. Posledné zaznamenané uvoľnenia miest (Storná)</h2>
    <table>
        <thead>
            <tr>
                <th>Čas detekcie</th>
                <th>Vlak</th>
                <th>Vozeň</th>
                <th>Počet vrátených miest</th>
            </tr>
        </thead>
        <tbody>
            {storna_rows if storna_rows else '<tr><td colspan="4">Žiadne nedávne storná neboli zaznamenané.</td></tr>'}
        </tbody>
    </table>

    <div class="footer">
        Vygenerované prostredníctvom GitHub Actions skriptu <br>
        Posledná aktualizácia: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M:%S')}
    </div>
</body>
</html>
"""

with open("indexx.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("Všetky pokročilé grafy boli úspešne zapísané do indexx.html")
