import streamlit as st
import pandas as pd
import numpy as np
from modules import data_processing as dp
from modules import visualization as viz

# Configuration - modify these names if your dataset uses different column names
DATA_PATH = "Data New version.xlsx"  # path inside the repo
ZONE_COLUMN = "Zone de Santé"
MONTH_COLUMN = "Mois"

# Optional lists: if empty, the app will try to detect variables automatically
NOTIFICATION_VARIABLES = []
SENSITIZATION_VARIABLES = []
VACCINATION_VARIABLES = []
EBOLA_VARIABLES = []

st.set_page_config(page_title="CGPP MEAL Dashboard", page_icon="📊", layout="wide")
st.title("📊 CGPP MEAL Monitoring Dashboard")
st.caption("Suivi des indicateurs par Zone de Santé et par mois")

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

# Keep a copy of original
df = df_raw.copy()

# Basic info box
with st.expander("Informations sur le fichier", expanded=True):
    st.write(f"Chemin du fichier: {DATA_PATH}")
    st.write(f"Total lignes: {len(df)}")
    st.write(f"Total variables: {len(df.columns)}")
    missing = df.isna().sum().sum()
    st.write(f"Total valeurs manquantes: {missing}")

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

# Sidebar filters
st.sidebar.header("Filtres d'analyse")
selected_zones = st.sidebar.multiselect("Zone de Santé", options=sorted(df[ZONE_COLUMN].dropna().unique()), default=sorted(df[ZONE_COLUMN].dropna().unique()))
selected_months = st.sidebar.multiselect("Mois", options=dp.month_order_present(df, MONTH_COLUMN), default=dp.month_order_present(df, MONTH_COLUMN))

# Variable selector per module
st.sidebar.markdown("---")
st.sidebar.subheader("Sélection de variables")
sel_notification = st.sidebar.multiselect("Notification - variables", options=classified['notification'], default=classified['notification'][:3])
sel_sensit = st.sidebar.multiselect("Sensibilisation - variables", options=classified['sensitization'], default=classified['sensitization'][:3])
sel_vacc = st.sidebar.multiselect("Vaccination - variables", options=classified['vaccination'], default=classified['vaccination'][:3])
sel_ebola = st.sidebar.multiselect("Ebola - variables", options=classified['ebola'], default=classified['ebola'][:3])

# Filter dataframe
df_filtered = df[df[ZONE_COLUMN].isin(selected_zones) & df[MONTH_COLUMN].isin(selected_months)].copy()

# KPIs
with st.container():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Observations", f"{len(df_filtered):,}")
    c2.metric("Zones de Santé", f"{df_filtered[ZONE_COLUMN].nunique():,}")
    c3.metric("Mois couverts", f"{df_filtered[MONTH_COLUMN].nunique():,}")
    # Example KPIs (try to infer common vars)
    notif_guess = classified['notification_numeric'][:1]
    sens_guess = classified['sensitization_numeric'][:1]
    vacc_guess = classified['vaccination_numeric'][:1]
    if notif_guess:
        c4.metric("Notifications (ex.)", f"{int(df_filtered[notif_guess[0]].sum()):,}")

# Tabs for modules
tabs = st.tabs(["📢 Notification", "📣 Sensibilisation", "💉 Vaccination", "🦠 Ebola"]) 

# Notification tab
with tabs[0]:
    st.header("Tableau 1. Résumé - Notification")
    viz.display_summary_table(df_filtered, group_cols=[ZONE_COLUMN, MONTH_COLUMN], numeric_vars=sel_notification, qualitative_vars=[], month_col=MONTH_COLUMN)

# Sensitization tab
with tabs[1]:
    st.header("Tableau 2. Résumé - Sensibilisation")
    viz.display_summary_table(df_filtered, group_cols=[ZONE_COLUMN, MONTH_COLUMN], numeric_vars=sel_sensit, qualitative_vars=[], month_col=MONTH_COLUMN)

# Vaccination tab
with tabs[2]:
    st.header("Tableau 3. Résumé - Vaccination")
    viz.display_summary_table(df_filtered, group_cols=[ZONE_COLUMN, MONTH_COLUMN], numeric_vars=sel_vacc, qualitative_vars=[], month_col=MONTH_COLUMN)

# Ebola tab
with tabs[3]:
    st.header("Tableau 4. Résumé - Ebola")
    viz.display_summary_table(df_filtered, group_cols=[ZONE_COLUMN, MONTH_COLUMN], numeric_vars=sel_ebola, qualitative_vars=[], month_col=MONTH_COLUMN)

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
    "Notification": dp.aggregate_numeric(df_filtered, [ZONE_COLUMN, MONTH_COLUMN], sel_notification) if sel_notification else pd.DataFrame(),
    "Sensibilisation": dp.aggregate_numeric(df_filtered, [ZONE_COLUMN, MONTH_COLUMN], sel_sensit) if sel_sensit else pd.DataFrame(),
    "Vaccination": dp.aggregate_numeric(df_filtered, [ZONE_COLUMN, MONTH_COLUMN], sel_vacc) if sel_vacc else pd.DataFrame(),
    "Ebola": dp.aggregate_numeric(df_filtered, [ZONE_COLUMN, MONTH_COLUMN], sel_ebola) if sel_ebola else pd.DataFrame(),
}

if st.button("Télécharger les résultats (Excel)"):
    bytes_data = to_excel_bytes(export_tables)
    st.download_button(label="Télécharger Excel", data=bytes_data, file_name="cgpp_meal_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if st.button("Télécharger les résultats (CSV, Notification)") and not export_tables['Notification'].empty:
    st.download_button(label="Notification CSV", data=export_tables['Notification'].to_csv(index=False).encode('utf-8'), file_name="notification.csv", mime="text/csv")

st.write("Fin de l'application. Personnalisez les variables et la configuration en haut du fichier.")
