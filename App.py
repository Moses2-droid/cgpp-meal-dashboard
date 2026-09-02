import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="CGPP MEAL Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CGPP MEAL Dashboard")
# Chargement des données
if st.button(
    "🔄 Importer les données depuis Ona",
    type="primary",
    use_container_width=True
):
    data = pd.read_excel("Data New version.xlsx")
# st.dataframe(data.head(20), use_container_width=True)
