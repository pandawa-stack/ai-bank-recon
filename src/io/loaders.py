# src/io/loaders.py
from typing import Optional

import pandas as pd
import streamlit as st


def load_table_from_upload(
    uploaded_file,
    label: str,
    key_prefix: str,
) -> Optional[pd.DataFrame]:
    """
    Load a CSV/XLS/XLSX file uploaded via Streamlit file_uploader
    and return a pandas DataFrame.
    """
    if uploaded_file is None:
        return None

    filename = uploaded_file.name.lower()

    try:
        if filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
            return df

        if filename.endswith((".xlsx", ".xls")):
            xls = pd.ExcelFile(uploaded_file)
            sheet_name = st.selectbox(
                f"Pilih sheet untuk {label}",
                xls.sheet_names,
                key=f"{key_prefix}_sheet_select",
            )
            df = xls.parse(sheet_name)
            return df

        st.error(f"Format file {label} tidak didukung. Gunakan CSV atau Excel.")
        return None
    except Exception as e:
        st.error(f"Gagal membaca file {label}: {e}")
        return None
