# src/core/recon.py
from typing import Literal, Tuple

import pandas as pd


def normalize_df(
    df: pd.DataFrame,
    date_col: str,
    desc_col: str,
    amount_col: str,
    source_label: Literal["bank", "book"],
) -> pd.DataFrame:
    """
    Normalize raw dataframe into a standard schema:
    columns: date (datetime), description (str), amount (float), source (str).
    """
    out = df[[date_col, desc_col]].copy()
    out.columns = ["date", "description"]

    raw_amount = df[amount_col]

    if pd.api.types.is_numeric_dtype(raw_amount):
        amount = raw_amount
    else:
        amount = pd.to_numeric(raw_amount, errors="coerce")

        # If still all NaN, try to derive from debit/credit style tables
        if amount.isna().all():
            debit_candidates = [
                "Debit (Keluar dari Rekening)",
                "Debit",
                "Debit (Keluar)",
            ]
            credit_candidates = [
                "Kredit (Masuk ke Rekening)",
                "Kredit",
                "Kredit (Masuk)",
            ]

            debit_col = next((c for c in debit_candidates if c in df.columns), None)
            credit_col = next((c for c in credit_candidates if c in df.columns), None)

            if debit_col and credit_col:
                debit_series = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
                credit_series = pd.to_numeric(
                    df[credit_col], errors="coerce"
                ).fillna(0)

                if source_label == "bank":
                    # bank: credit = masuk, debit = keluar
                    amount = credit_series - debit_series
                else:
                    # book: debit = kas masuk, credit = kas keluar
                    amount = debit_series - credit_series

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["amount"] = pd.to_numeric(amount, errors="coerce")
    out = out.dropna(subset=["amount"])
    out["source"] = source_label
    return out


def reconcile_frames(
    bank_df: pd.DataFrame,
    book_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, float]:
    """
    Perform simple reconciliation:
    - outer join on date & amount
    - identify bank_only and book_only
    - compute difference between totals

    Returns:
        bank_df_norm, book_df_norm, bank_only, book_only, difference
    """
    bank_df_norm = bank_df.copy()
    book_df_norm = book_df.copy()

    merged = pd.merge(
        bank_df_norm,
        book_df_norm,
        on=["date", "amount"],
        how="outer",
        suffixes=("_bank", "_book"),
        indicator=True,
    )

    bank_only = (
        merged[merged["_merge"] == "left_only"][["date", "description_bank", "amount"]]
        .rename(columns={"description_bank": "description"})
        .reset_index(drop=True)
    )

    book_only = (
        merged[merged["_merge"] == "right_only"][["date", "description_book", "amount"]]
        .rename(columns={"description_book": "description"})
        .reset_index(drop=True)
    )

    total_bank = bank_df_norm["amount"].sum()
    total_book = book_df_norm["amount"].sum()
    difference = float(abs(total_bank - total_book))

    return bank_df_norm, book_df_norm, bank_only, book_only, difference
