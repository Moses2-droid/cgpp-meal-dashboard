import pandas as pd
import numpy as np
import re

MONTHS_ORDER = [
    'Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'
]


def clean_dataframe(df: pd.DataFrame, zone_col: str, month_col: str) -> pd.DataFrame:
    df = df.copy()
    # Drop completely empty columns
    df.dropna(axis=1, how='all', inplace=True)

    # Trim whitespace from string columns
    for c in df.select_dtypes(include=['object']).columns:
        df[c] = df[c].astype(str).str.strip()
        df[c] = df[c].replace({'nan': pd.NA})

    # Normalize Yes/No (Oui/Non)
    df = _normalize_binary(df)

    # Try to coerce numeric-like columns
    for c in df.columns:
        if c in [zone_col, month_col]:
            continue
        # If many values look numeric, convert
        sample = df[c].dropna().astype(str).head(200)
        numeric_like = sample.str.match(r'^[-+]?\d*[\.,]?\d+$').sum()
        if len(sample) > 0 and (numeric_like / len(sample)) > 0.6:
            df[c] = df[c].astype(str).str.replace(',', '.')
            df[c] = pd.to_numeric(df[c], errors='coerce')

    # Derive month name if month_col is a date
    if month_col in df.columns:
        if np.issubdtype(df[month_col].dtype, np.datetime64):
            df[month_col] = df[month_col].dt.month.apply(lambda m: MONTHS_ORDER[m-1])
        else:
            # Attempt to parse if values look like dates
            try:
                parsed = pd.to_datetime(df[month_col], errors='coerce')
                if parsed.notna().sum() > 0:
                    df.loc[parsed.notna(), month_col] = parsed.dt.month.apply(lambda m: MONTHS_ORDER[m-1])
            except Exception:
                pass

    # Ensure month ordering categorical
    if month_col in df.columns:
        df[month_col] = pd.Categorical(df[month_col], categories=MONTHS_ORDER, ordered=True)

    return df


def _normalize_binary(df: pd.DataFrame) -> pd.DataFrame:
    replacements = {
        '^oui$': 'Oui', '^o$': 'Oui', '^yes$': 'Oui', '^1$': 'Oui',
        '^non$': 'Non', '^n$': 'Non', '^no$': 'Non', '^0$': 'Non'
    }
    for c in df.select_dtypes(include=['object']).columns:
        s = df[c].dropna().astype(str)
        if s.str.lower().isin(['oui','non','o','n','yes','no','1','0']).any():
            def map_val(v):
                if pd.isna(v):
                    return v
                for pat, rep in replacements.items():
                    if re.match(pat, str(v).strip(), flags=re.IGNORECASE):
                        return rep
                return v
            df[c] = df[c].apply(map_val)
    return df


def classify_variables(df: pd.DataFrame, zone_col: str, month_col: str,
                       notification_vars=None, sensitization_vars=None,
                       vaccination_vars=None, ebola_vars=None):
    # Start with empty lists
    notification_vars = notification_vars or []
    sensitization_vars = sensitization_vars or []
    vaccination_vars = vaccination_vars or []
    ebola_vars = ebola_vars or []

    cols = [c for c in df.columns if c not in [zone_col, month_col]]

    # Heuristics by keywords
    keywords = {
        'notification': ['notif', 'notification', 'cas', 'confirmed', 'suspect', 'fever', 'alerte'],
        'sensitization': ['sensibil', 'sensibi', 'sensit', 'awareness', 'sensitisation', 'personnes sensibilisées'],
        'vaccination': ['vaccin', 'vaccine', 'vaccinated', 'child', 'enfant', 'dose', 'vaccinés'],
        'ebola': ['ebola', 'ebol', 'ebolavirus']
    }

    classified = {'notification': [], 'sensitization': [], 'vaccination': [], 'ebola': []}

    for c in cols:
        lc = c.lower()
        assigned = False
        for cat, keys in keywords.items():
            for k in keys:
                if k in lc:
                    classified[cat].append(c)
                    assigned = True
                    break
            if assigned:
                break
        if not assigned:
            # numeric -> notification by default, else sensitization
            if pd.api.types.is_numeric_dtype(df[c]) or df[c].dtype.name == 'Int64':
                classified['notification'].append(c)
            else:
                classified['sensitization'].append(c)

    # Respect user-provided lists
    for name, lst in [('notification', notification_vars), ('sensitization', sensitization_vars), ('vaccination', vaccination_vars), ('ebola', ebola_vars)]:
        if lst:
            classified[name] = [c for c in lst if c in df.columns]

    # Also provide numeric-only lists for KPI estimation
    classified_out = {
        'notification': classified['notification'],
        'sensitization': classified['sensitization'],
        'vaccination': classified['vaccination'],
        'ebola': classified['ebola'],
        'notification_numeric': [c for c in classified['notification'] if pd.api.types.is_numeric_dtype(df[c])],
        'sensitization_numeric': [c for c in classified['sensitization'] if pd.api.types.is_numeric_dtype(df[c])],
        'vaccination_numeric': [c for c in classified['vaccination'] if pd.api.types.is_numeric_dtype(df[c])],
        'ebola_numeric': [c for c in classified['ebola'] if pd.api.types.is_numeric_dtype(df[c])],
    }
    return classified_out


def month_order_present(df: pd.DataFrame, month_col: str):
    if month_col not in df.columns:
        return []
    uniq = [m for m in MONTHS_ORDER if m in df[month_col].unique()]
    # Fallback to sorted unique
    if not uniq:
        uniq = sorted(df[month_col].dropna().unique())
    return uniq


def aggregate_numeric(df: pd.DataFrame, group_cols, numeric_vars):
    if not numeric_vars:
        return pd.DataFrame()
    agg = df.groupby(group_cols)[numeric_vars].sum(min_count=1).reset_index()
    # Ensure month ordering
    return agg


def frequency_table(df: pd.DataFrame, group_cols, qualitative_var):
    # Returns a table with counts and percentages per group
    g = df.dropna(subset=[qualitative_var]).groupby(group_cols + [qualitative_var]).size().reset_index(name='Effectif')
    denom = df.dropna(subset=[qualitative_var]).groupby(group_cols).size().reset_index(name='Total')
    merged = g.merge(denom, on=group_cols)
    merged['Pourcentage'] = (merged['Effectif'] / merged['Total']) * 100
    return merged
