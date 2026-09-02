import streamlit as st
import pandas as pd
import plotly.express as px


def display_summary_table(df: pd.DataFrame, group_cols, numeric_vars, qualitative_vars, month_col=None):
    # Numeric aggregation
    if numeric_vars:
        num_table = df.groupby(group_cols)[numeric_vars].sum(min_count=1).reset_index()
        st.subheader("Tableau quantitatif")
        st.dataframe(num_table, use_container_width=True)
        # Example chart: monthly evolution for first numeric var
        if month_col and numeric_vars:
            first = numeric_vars[0]
            st.subheader(f"Évolution mensuelle: {first}")
            fig = px.line(df.groupby([month_col])[first].sum().reset_index(), x=month_col, y=first, markers=True)
            st.plotly_chart(fig, use_container_width=True)

    # Qualitative tables
    if qualitative_vars:
        st.subheader("Tableau qualitatif")
        for v in qualitative_vars:
            freq = df.dropna(subset=[v]).groupby(group_cols + [v]).size().reset_index(name='Effectif')
            denom = df.dropna(subset=[v]).groupby(group_cols).size().reset_index(name='Total')
            merged = freq.merge(denom, on=group_cols)
            merged['Pourcentage'] = (merged['Effectif'] / merged['Total']) * 100
            st.write(f"Variable: {v}")
            st.dataframe(merged, use_container_width=True)
            # Plot
            fig = px.bar(merged, x=v, y='Pourcentage', color=group_cols[0], barmode='group')
            st.plotly_chart(fig, use_container_width=True)
