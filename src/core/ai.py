# src/core/ai.py
import textwrap
from typing import Optional

import pandas as pd
from openai import OpenAI
import streamlit as st


SYSTEM_PROMPT = """
You are a senior accountant and bank reconciliation expert.
Your job is to guide and explain bank reconciliation based on best practice.

Best-practice steps you MUST follow mentally when analysing the data:
1) Check period consistency and opening balances (if provided).
2) Compare bank statement vs cash book for the same period.
3) Identify transactions that appear in BOTH records (matched).
4) Identify transactions that exist in BANK ONLY (likely: bank charges, interest income, auto-debit, direct customer deposits, etc.).
5) Identify transactions that exist in BOOK ONLY (likely: deposits in transit, outstanding checks/payments, timing differences).
6) For BANK-ONLY items: propose journal entries needed in the BOOK side.
7) For BOOK-ONLY items: decide which are timing differences (no journal) vs potential errors that need correction.
8) At the end, produce a clear checklist of next actions for the human accountant.

Style:
- Respond in Bahasa Indonesia.
- Jelaskan dengan struktur yang rapi (judul & bullet).
- Fokus pada penjelasan praktis, bukan teori panjang.
- Jangan mengarang angka baru di luar data yang diberikan.
"""


@st.cache_resource(show_spinner=False)
def get_client(api_key: str) -> OpenAI:
    """Create and cache OpenAI client."""
    return OpenAI(api_key=api_key)


def call_ai_agent(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str = "gpt-4.1-mini",
) -> str:
    """Call OpenAI chat completion and return plain text response."""
    client = get_client(api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def _df_to_csv_snippet(df: pd.DataFrame, max_rows: int = 30) -> str:
    """Convert dataframe to CSV snippet, limiting rows for prompt size."""
    if df.empty:
        return "(tidak ada)"
    if len(df) > max_rows:
        trimmed = df.head(max_rows)
        csv_text = trimmed.to_csv(index=False)
        csv_text += (
            f"\n# NOTE: hanya {max_rows} baris pertama yang ditampilkan "
            f"dari total {len(df)} baris.\n"
        )
        return csv_text
    return df.to_csv(index=False)


def build_ai_prompt(
    bank_df: pd.DataFrame,
    book_df: pd.DataFrame,
    bank_only: pd.DataFrame,
    book_only: pd.DataFrame,
    period_label: str,
    opening_bank: Optional[float],
    opening_book: Optional[float],
) -> str:
    """Build structured prompt for the AI reconciliation explanation."""
    bank_summary = (
        f"Total baris bank: {len(bank_df)}, "
        f"total amount bank: {bank_df['amount'].sum():,.2f}"
    )
    book_summary = (
        f"Total baris buku: {len(book_df)}, "
        f"total amount buku: {book_df['amount'].sum():,.2f}"
    )

    opening_info = []
    if opening_bank is not None:
        opening_info.append(
            f"Saldo awal bank (menurut rekening koran): {opening_bank:,.2f}"
        )
    if opening_book is not None:
        opening_info.append(
            f"Saldo awal buku (menurut pembukuan): {opening_book:,.2f}"
        )
    opening_text = "\n".join(opening_info) if opening_info else "Saldo awal tidak diisi."

    prompt = f"""
Konteks rekonsiliasi bank:

Periode: {period_label}
Ringkasan:
- {bank_summary}
- {book_summary}
- {opening_text}

Transaksi yang HANYA ADA di REKENING KORAN (bank_only):
Format kolom: date, description, amount
{_df_to_csv_snippet(bank_only)}

Transaksi yang HANYA ADA di BUKU BANK / PEMBUKUAN (book_only):
Format kolom: date, description, amount
{_df_to_csv_snippet(book_only)}

Tugas Anda:
1. Ikuti langkah-langkah rekonsiliasi bank best practice seperti di system prompt.
2. Klasifikasikan transaksi BANK-ONLY dan BOOK-ONLY.
3. Sarankan jurnal penyesuaian yang perlu dibuat di PEMBUKUAN.
4. Jelaskan mana saja yang sebaiknya diperlakukan sebagai perbedaan waktu (timing difference).
5. Berikan checklist langkah berikutnya untuk akuntan (maksimal 7 bullet).

Jawab dalam Bahasa Indonesia, dengan heading dan bullet yang jelas.
"""
    return textwrap.dedent(prompt).strip()
