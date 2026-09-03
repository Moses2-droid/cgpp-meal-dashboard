import streamlit as st
import pandas as pd
import numpy as np
from modules import data_processing as dp
from modules import visualization as viz

# Configuration - modify these names if your dataset uses different column names
DATA_PATH = "Data New version.xlsx"  # path inside the repo
ZONE_COLUMN = "1.3. Zone de santé"
MONTH_COLUMN = "1.21. Mois du Rapport"
YEAR_COLUMN= "1.22. Année du rapport"

@st.cache_data
def load_data(path: str):
    try:
        df = pd.read_excel(path, engine="openpyxl")
        return df
    except Exception as e:
        try:
            df = pd.read_csv(path)
            return df
        except Exception:
            raise e

# Load data
try:
    df_raw = load_data(DATA_PATH)
except Exception as e:
    st.error(f"Impossible de charger le fichier de données: {e}")
    st.stop()

colonnes_bool = df_raw.select_dtypes(include="bool").columns
# Convertir True → 1 et False → 0
df_raw[colonnes_bool] = df_raw[colonnes_bool].astype(int)
# Optional lists: if empty, the app will try to detect variables automatically
NOTIFICATION_VARIABLES = df_raw.iloc[:, 38:110].select_dtypes(include="int").columns.tolist()
SENSITIZATION_VARIABLES = df_raw.iloc[:, [154] + list(range(156, 172)) + list(range(176, 192))+list(range(301, 305))].columns.tolist()
VACCINATION_VARIABLES =df_raw.iloc[:, list(range(1196, 1221))+[1223]].columns.tolist()
EBOLA_VARIABLES = df_raw.iloc[:, list(range(77, 82))+[159]].columns.tolist()
#st.markdown(NOTIFICATION_VARIABLES)
st.set_page_config(page_title="CGPP MEAL Dashboard", page_icon="📊", layout="wide")
st.title("📊 CGPP MEAL Monitoring Dashboard")
st.caption("Suivi des indicateurs par Zone de Santé et par mois")

# Keep a copy of original
df = df_raw.copy()

# Ensure configured columns exist; if not, ask user to map them
cols = list(df.columns)
if ZONE_COLUMN not in cols or MONTH_COLUMN not in cols:
    st.warning("Les noms de colonnes par défaut pour Zone ou Mois ne sont pas présents. Veuillez mapper les colonnes ci-dessous.")
    zone_col = st.selectbox("Colonne Zone de Santé", options=[None] + cols, index=0)
    month_col = st.selectbox("Colonne Mois", options=[None] + cols, index=0)
    if zone_col:
        ZONE_COLUMN = zone_col
    if month_col:
        MONTH_COLUMN = month_col

# Clean data
df = dp.clean_dataframe(df, zone_col=ZONE_COLUMN, month_col=MONTH_COLUMN)

# Automatic classification
classified = dp.classify_variables(df, zone_col=ZONE_COLUMN, month_col=MONTH_COLUMN,
                                   notification_vars=NOTIFICATION_VARIABLES,
                                   sensitization_vars=SENSITIZATION_VARIABLES,
                                   vaccination_vars=VACCINATION_VARIABLES,
                                   ebola_vars=EBOLA_VARIABLES)

# Analysis / Inventory of variables
st.markdown("---")
st.header("Analyse automatique des variables (inventaire)")
cols_to_inspect = [c for c in df.columns if c not in [ZONE_COLUMN, MONTH_COLUMN]]
var_rows = []
for c in cols_to_inspect:
    dtype = str(df[c].dtype)
    is_numeric = pd.api.types.is_numeric_dtype(df[c])
    # fallback numeric detection
    if not is_numeric:
        sample = df[c].dropna().astype(str).head(200)
        if len(sample) > 0:
            numeric_like = sample.str.match(r'^[-+]?\d*[\.,]?\d+$').sum()
            if (numeric_like / len(sample)) > 0.6:
                is_numeric = True
    uniq = int(df[c].nunique(dropna=True))
    sample_vals = ", ".join(df[c].dropna().astype(str).unique()[:5].tolist())
    suggested = None
    for cat in ['notification', 'sensitization', 'vaccination', 'ebola']:
        if c in classified.get(cat, []):
            suggested = cat
            break
    if not suggested:
        suggested = 'notification' if is_numeric else 'sensitization'
    var_rows.append({
        'variable': c,
        'dtype': dtype,
        'is_numeric': is_numeric,
        'n_unique': uniq,
        'sample_values': sample_vals,
        'suggested_category': suggested
    })

var_df = pd.DataFrame(var_rows)
st.dataframe(var_df, use_container_width=True)

# Show summary of classified counts
st.write("**Mapping automatique (résumé)**")
st.write({k: len(v) for k, v in classified.items() if isinstance(v, list)})

# Sidebar filters
st.sidebar.header("Filtres d'analyse")
selected_zones = st.sidebar.multiselect("Zone de Santé", options=sorted(df[ZONE_COLUMN].dropna().unique()), default=sorted(df[ZONE_COLUMN].dropna().unique()))
selected_year = st.sidebar.selectbox("Année",options=sorted(df[YEAR_COLUMN].dropna().unique()))
selected_months = st.sidebar.multiselect("Mois", options=dp.month_order_present(df, MONTH_COLUMN), default=dp.month_order_present(df, MONTH_COLUMN))

# Theme Selector
st.sidebar.markdown("---")
st.sidebar.subheader("Sélection de Thème")
# Filter dataframe
df_filtered = df[df[ZONE_COLUMN].isin(selected_zones) & df[MONTH_COLUMN].isin(selected_months)&(df[YEAR_COLUMN]==selected_year)].copy()

# Tabs for modules
tabs = st.tabs(["📢 Notification", "📣 Sensibilisation", "🦠 Ebola","💉 Vaccination"])

# Notification tab
with tabs[0]:
    numeric_vars=df_filtered[NOTIFICATION_VARIABLES].select_dtypes(include=["int"]).columns.tolist()
    summary_notif=df_filtered.groupby([ZONE_COLUMN, MONTH_COLUMN, YEAR_COLUMN])[numeric_vars].sum().reset_index().T
    st.dataframe(summary_notif)
# Sensitization tab
with tabs[1]:
    numeric_vars=df_filtered[SENSITIZATION_VARIABLES].select_dtypes(include=["int"]).columns.tolist()
    st.header("Tableau 2. Résumé - Sensibilisation Nombres et Thèmes")
    summary_sensit=df_filtered.groupby([ZONE_COLUMN, MONTH_COLUMN, YEAR_COLUMN])[numeric_vars].sum().reset_index().T
    st.dataframe(summary_sensit)
# Vaccination tab
with tabs[2]:
    st.header("Tableau 3. Résumé - Vaccination")
    numeric_vars=df_filtered[EBOLA_VARIABLES].select_dtypes(include=["int"]).columns.tolist()
    st.header("Tableau 2. Résumé - Sensibilisation Nombres et Thèmes")
    summary_EB=df_filtered.groupby([ZONE_COLUMN, MONTH_COLUMN, YEAR_COLUMN])[numeric_vars].sum().reset_index().T
    st.dataframe(summary_EB)

# Ebola tab
with tabs[3]:
    st.header("Tableau 4. Résumé - Ebola")
    numeric_vars=df_filtered[VACCINATION_VARIABLES].select_dtypes(include=["int"]).columns.tolist()
    st.header("Tableau 2. Résumé - Sensibilisation Nombres et Thèmes")
    summary_v=df_filtered.groupby([ZONE_COLUMN, MONTH_COLUMN, YEAR_COLUMN])[numeric_vars].sum().reset_index().T
    st.dataframe(summary_v)

# Export section
st.markdown("---")
st.header("📥 Export des résultats")

def to_excel_bytes(dfs: dict):
    from io import BytesIO
    with BytesIO() as b:
        with pd.ExcelWriter(b, engine="openpyxl") as writer:
            for name, table in dfs.items():
                table.to_excel(writer, sheet_name=name[:31], index=False)
        return b.getvalue()

export_tables = {
    "Notification": summary_notif ,
    "Sensibilisation":  summary_sensit,
    "Vaccination":  summary_v,
    "Ebola":  summary_EB,
}

if st.button("Télécharger les résultats (Excel)"):
    bytes_data = to_excel_bytes(export_tables)
    st.download_button(label="Télécharger Excel", data=bytes_data, file_name="cgpp_meal_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if st.button("Télécharger les résultats (CSV, Notification)") and not export_tables['Notification'].empty:
    st.download_button(label="Notification CSV", data=export_tables['Notification'].to_csv(index=False).encode('utf-8'), file_name="notification.csv", mime="text/csv")

st.write("Fin de l'application. Personnalisez les variables et la configuration en haut du fichier.")
