import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import re

# 1. Načítanie dát
url = "https://github.io"
try:
    df = pd.read_csv(url)
except Exception as e:
    print(f"Nepodarilo sa načítať dáta z URL, skúšam lokálny súbor. Chyba: {e}")
    df = pd.read_csv("data/obsadenost_data.csv")

# Úprava dátových typov
df['cas'] = pd.to_datetime(df['cas'])
df['den'] = pd.to_datetime(df['den'])
df['hodina'] = df['cas'].dt.hour
df['den_v_tyzdni'] = df['den'].dt.day_name()

# Pomocná tabuľka pre stabilný prepočet kapacity a indexov
idx_last = df.groupby(['den', 'vlak', 'vozen'])['cas'].idxmax()
df_last = df.loc[idx_last].copy()

kapacity = df.groupby(['vlak', 'vozen'])['volne'].max().reset_index().rename(columns={'volne': 'kapacita'})
df_last = df_last.merge(kapacity, on=['vlak', 'vozen'], how='left')
df_last['obsadenost_pct'] = ((df_last['kapacita'] - df_last['volne']) / df_last['kapacita'] * 100).clip(lower=0).round(0)

# Výpočet dynamiky (obsadené/uvoľnené miesta)
df_sorted = df.sort_values(['vlak', 'vozen', 'cas'])
df_sorted['zmena'] = df_sorted.groupby(['vlak', 'vozen'])['volne'].diff()
df_predaj = df_sorted.dropna(subset=['zmena']).copy()
df_predaj['obsadene'] = df_predaj['zmena'].apply(lambda x: abs(x) if x < 0 else 0)
df_predaj['uvolnene'] = df_predaj['zmena'].apply(lambda x: x if x > 0 else 0)

# ==============================================================================
# GRAFY Z PÔVODNÉHO NÁVRHU
# ==============================================================================

# G1: Vývoj voľných miest
df_vlak = df.groupby(['cas', 'vlak', 'vlak_popis'])['volne'].sum().reset_index()
fig1 = px.line(df_vlak, x='cas', y='volne', color='vlak', hover_data=['vlak_popis'], title='Vývoj celkového počtu voľných miest vo vlakoch v čase')
fig1.update_layout(template="plotly_dark", xaxis_title="Dátum a čas", yaxis_title="Voľné miesta")

# G2: Plnenie vozňov (Heatmap)
df_heatmap = df_last.groupby(['vlak', 'vozen'])['obsadenost_pct'].mean().unstack().fillna(0)
fig2 = px.imshow(df_heatmap, labels=dict(x="Vozeň", y="Vlak", color="Obsadenosť (%)"), color_continuous_scale="Viridis", title="Priemerná obsadenosť vozňov pri poslednom meraní (%)")
fig2.update_layout(template="plotly_dark")

# G3: Predaj miest podľa hodiny dňa
df_hodiny = df_predaj.groupby('hodina')[['obsadene', 'uvolnene']].mean().reset_index()
fig3 = go.Figure()
fig3.add_trace(go.Bar(x=df_hodiny['hodina'], y=df_hodiny['obsadene'], name='Obsadené miesta', marker_color='crimson'))
fig3.add_trace(go.Bar(x=df_hodiny['hodina'], y=df_hodiny['uvolnene'], name='Uvoľnené miesta', marker_color='lightseagreen'))
fig3.update_layout(template="plotly_dark", barmode='group', title='Priemerná dynamika zmien kapacity podľa hodiny dňa', xaxis_title='Hodina dňa', yaxis_title='Priemerný počet miest', xaxis=dict(tickmode='linear', tick0=0, dtick=1))

# ==============================================================================
# DOPLNENIE 4 NOVÝCH NÁVRHOV ŠTATISTÍK
# ==============================================================================

# NÁVRH 1: Detekcia kritických dní
poradie_dni = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
sk_dni = {'Monday': 'Pondelok', 'Tuesday': 'Utorok', 'Wednesday': 'Streda', 'Thursday': 'Štvrtok', 'Friday': 'Piatok', 'Saturday': 'Sobota', 'Sunday': 'Nedeľa'}

df_dni = df_last.groupby('den_v_tyzdni')['obsadenost_pct'].mean().reindex(poradie_dni).reset_index()
df_dni['den_v_tyzdni'] = df_dni['den_v_tyzdni'].map(sk_dni)

fig4 = px.bar(df_dni, x='den_v_tyzdni', y='obsadenost_pct', title='Kritické dni: Priemerná finálna obsadenosť vlaku podľa dňa v týždni', color='obsadenost_pct', color_continuous_scale='Reds', labels={'den_v_tyzdni': 'Deň v týždni', 'obsadenost_pct': 'Obsadenosť (%)'})
fig4.update_layout(template="plotly_dark")

# NÁVRH 2: Časový predstih nákupu
def extrahuj_hodiny_pred_odchodom(popis):
    match = re.search(r'(\d{2}):(\d{2})', str(popis))
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

df_predstih = df_predaj.merge(df[['cas', 'vlak', 'vlak_popis']].drop_duplicates(subset=['cas', 'vlak']), on=['cas', 'vlak'], how='left')

predstihy_list = []
for idx, row in df_predstih.iterrows():
    h, m = extrahuj_hodiny_pred_odchodom(row['vlak_popis_x'])
    if h is not None:
        cas_odchodu = row['cas'].replace(hour=h, minute=m, second=0)
        if cas_odchodu < row['cas']:
            cas_odchodu += pd.Timedelta(days=1)
        
        rozdiel_hodin = (cas_odchodu - row['cas']).total_seconds() / 3600.0
        if rozdiel_hodin >= 0:
            predstihy_list.append((rozdiel_hodin, row['obsadene']))

df_res_predstih = pd.DataFrame(predstihy_list, columns=['hodiny_pred', 'obsadene'])

def kategorizuj_cas(h):
    if h <= 1: return 'Menej ako 1h pred odchodom'
    elif h <= 4: return '1h až 4h pred odchodom'
    elif h <= 12: return '4h až 12h pred odchodom'
    elif h <= 24: return '12h až 24h pred odchodom'
    else: return 'Viac ako 24h vopred'

df_res_predstih['Kategória predstihu'] = df_res_predstih['hodiny_pred'].apply(kategorizuj_cas)
df_pie_data = df_res_predstih.groupby('Kategória predstihu')['obsadene'].sum().reset_index()

fig5 = px.pie(df_pie_data, values='obsadene', names='Kategória predstihu', title='Kedy cestujúci nakupujú (Rozdelenie predstihu nákupu lístkov)')
fig5.update_layout(template="plotly_dark")

# NÁVRH 3: Porovnanie časových kategórií dňa
def kategoria_dna(popis):
    h, _ = extrahuj_hodiny_pred_odchodom(popis)
    if h is None: return 'Neznáme'
    if 4 <= h < 10: return 'Ranná špička (04:00 - 10:00)'
    elif 10 <= h < 16: return 'Cezdeň (10:00 - 16:00)'
    elif 16 <= h < 21: return 'Poobedná špička (16:00 - 21:00)'
    else: return 'Nočné spoje (21:00 - 04:00)'

df_last['kategoria_dna'] = df_last['vlak_popis'].apply(kategoria_dna)
df_kat_dna = df_last.groupby('kategoria_dna')['obsadenost_pct'].mean().reset_index()

fig6 = px.bar(df_kat_dna, x='kategoria_dna', y='obsadenost_pct', title='Vyťaženosť spojov podľa kategórie dennej hodiny odchodu', text_auto=True, color='kategoria_dna')
fig6.update_layout(template="plotly_dark", showlegend=False)

# NÁVRH 4: Index stability / fluktuácie
df_fluktuacia = df_predaj.groupby('vlak').agg(
    celkove_obsadene=('obsadene', 'sum'),
    celkove_stornovane=('uvolnene', 'sum')
).reset_index()

df_fluktuacia['Index fluktuácie (%)'] = ((df_fluktuacia['celkove_stornovane'] / (df_fluktuacia['celkove_obsadene'] + 1)) * 100).round(1)
df_fluktuacia = df_fluktuacia.sort_values(by='Index fluktuácie (%)', ascending=False)

fig7 = px.bar(df_fluktuacia, x='vlak', y='Index fluktuácie (%)', title='Index stability: Ktoré vlaky trpia najväčším počtom stornovaných lístkov?', text_auto=True)
fig7.update_layout(template="plotly_dark")

# --- Tabuľka storn ---
df_storna = df_predaj[df_predaj['zmena'] > 0].sort_values('cas', ascending=False).head(15)
storna_rows = ""
for _, r in df_storna.iterrows():
    # OPRAVENÉ: Tu museli byť jednoduché zátvorky pre korektné vloženie hodnôt
    storna_rows += f"<tr><td>{r['cas'].strftime('%d.%m. %H:%M')}</td><td>{r['vlak']}</td><td>{r['vozen']}</td><td>+{int(r['zmena'])} miesta</td></tr>"

# --- Generovanie výsledného HTML ---
# POZNÁMKA: CSS štýly zostávajú v {{ }} aby ich f-string ignoroval, 
# ale Plotly objekty a tabuľka majú teraz klasické { }, aby sa reálne vyhodnotili.
html_content = f"""
<!DOCTYPE html>
<html lang="sk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IDOS - Pokročilé štatistiky obsadenosti</title>
    <style>
        body {{ background-color: #111; color: #eee; font-family: sans-serif; margin: 0; padding: 20px; display: flex; flex-direction: column; align-items: center; }}
        h1 {{ color: #fff; }}
        h2 {{ color: #f0a500; margin-top: 40px; width: 90%; max-width: 1200px; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .container {{ width: 90%; max-width: 1200px; margin-top: 10px; }}
        table {{ width: 90%; max-width: 1200px; border-collapse: collapse; margin-top: 15px; background-color: #1a1a1a; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background-color: #2c2c2c; color: #f0a500; }}
    </style>
</head>
<body>
    <h1>Súhrnné štatistiky obsadenosti vlakov</h1>
    <div class="container">{pio.to_html(fig1, full_html=False, include_plotlyjs='cdn')}</div>
    <h2>2. Plnenie jednotlivých vozňov</h2>
    <div class="container">{pio.to_html(fig2, full_html=False, include_plotlyjs=False)}</div>
    <h2>3. Dynamika nákupov a storna počas dňa</h2>
    <div class="container">{pio.to_html(fig3, full_html=False, include_plotlyjs=False)}</div>
    <h2>4. Vyťaženosť v dňoch týždňa (Návrh 1)</h2>
    <div class="container">{pio.to_html(fig4, full_html=False, include_plotlyjs=False)}</div>
    <h2>5. Kedy ľudia kupujú lístky pred odchodom (Návrh 2)</h2>
    <div class="container">{pio.to_html(fig5, full_html=False, include_plotlyjs=False)}</div>
    <h2>6. Vyťaženosť spojov podľa kategórie dňa (Návrh 3)</h2>
    <div class="container">{pio.to_html(fig6, full_html=False, include_plotlyjs=False)}</div>
    <h2>7. Index fluktuácie a storna lístkov (Návrh 4)</h2>
    <div class="container">{pio.to_html(fig7, full_html=False, include_plotlyjs=False)}</div>
    <h2>8. Posledné zaznamenané uvoľnenia miest (Storná)</h2>
    <table>
        <thead><tr><th>Čas detekcie</th><th>Vlak</th><th>Vozeň</th><th>Počet vrátených miest</th></tr></thead>
        <tbody>{storna_rows if storna_rows else '<tr><td colspan="4">Žiadne nedávne storná.</td></tr>'}</tbody>
    </table>
</body>
</html>
"""

with open("indexx.html", "w", encoding="utf-8") as f:
    f.write(html_content)
print("Súbor indexx.html bol úspešne vygenerovaný s funkčnými grafmi!")
