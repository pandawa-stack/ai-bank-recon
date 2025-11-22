import os
import textwrap
from typing import Optional

import pandas as pd
import streamlit as st
from openai import OpenAI

# ========================= PAGE CONFIG =========================
st.set_page_config(
    page_title="Bank Reconciliation AI Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

# ========================= HELPER FUNCTIONS =========================
@st.cache_resource(show_spinner=False)
def get_client(api_key: str):
    return OpenAI(api_key=api_key)

def call_ai_agent(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str = "gpt-4.1-mini",
) -> str:
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

def normalize_df(
    df: pd.DataFrame,
    date_col: str,
    desc_col: str,
    amount_col: str,
    source_label: str,
) -> pd.DataFrame:
    out = df[[date_col, desc_col]].copy()
    out.columns = ["date", "description"]
    
    raw_amount = df[amount_col]
    
    if pd.api.types.is_numeric_dtype(raw_amount):
        amount = raw_amount
    else:
        amount = pd.to_numeric(raw_amount, errors="coerce")
        
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
                credit_series = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
                
                if source_label == "bank":
                    amount = credit_series - debit_series
                else:
                    amount = debit_series - credit_series
    
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["amount"] = pd.to_numeric(amount, errors="coerce")
    out = out.dropna(subset=["amount"])
    out["source"] = source_label
    return out

def build_ai_prompt(
    bank_df: pd.DataFrame,
    book_df: pd.DataFrame,
    bank_only: pd.DataFrame,
    book_only: pd.DataFrame,
    period_label: str,
    opening_bank: Optional[float],
    opening_book: Optional[float],
) -> str:
    def df_to_csv_snippet(df: pd.DataFrame, max_rows: int = 30) -> str:
        if df.empty:
            return "(tidak ada)"
        if len(df) > max_rows:
            trimmed = df.head(max_rows)
            csv_text = trimmed.to_csv(index=False)
            csv_text += f"\n# NOTE: hanya {max_rows} baris pertama yang ditampilkan dari total {len(df)} baris.\n"
            return csv_text
        return df.to_csv(index=False)
    
    bank_summary = f"Total baris bank: {len(bank_df)}, total amount bank: {bank_df['amount'].sum():,.2f}"
    book_summary = f"Total baris buku: {len(book_df)}, total amount buku: {book_df['amount'].sum():,.2f}"
    
    opening_info = []
    if opening_bank is not None:
        opening_info.append(f"Saldo awal bank (menurut rekening koran): {opening_bank:,.2f}")
    if opening_book is not None:
        opening_info.append(f"Saldo awal buku (menurut pembukuan): {opening_book:,.2f}")
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
{df_to_csv_snippet(bank_only)}

Transaksi yang HANYA ADA di BUKU BANK / PEMBUKUAN (book_only):
Format kolom: date, description, amount
{df_to_csv_snippet(book_only)}

Tugas Anda:
1. Ikuti langkah-langkah rekonsiliasi bank best practice seperti di system prompt.
2. Klasifikasikan transaksi BANK-ONLY dan BOOK-ONLY.
3. Sarankan jurnal penyesuaian yang perlu dibuat di PEMBUKUAN.
4. Jelaskan mana saja yang sebaiknya diperlakukan sebagai perbedaan waktu (timing difference).
5. Berikan checklist langkah berikutnya untuk akuntan (maksimal 7 bullet).

Jawab dalam Bahasa Indonesia, dengan heading dan bullet yang jelas.
"""
    return textwrap.dedent(prompt).strip()

def parse_float(value: str) -> Optional[float]:
    if not value:
        return None
    value = value.strip().replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(value)
    except:
        return None

def load_table_from_upload(uploaded_file, label: str, key_prefix: str) -> Optional[pd.DataFrame]:
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

# ========================= SESSION STATE =========================
if "step" not in st.session_state:
    st.session_state.step = 1

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

if "results" not in st.session_state:
    st.session_state.results = None

# ========================= HEADER =========================
col_header1, col_header2 = st.columns([0.75, 0.25])
with col_header1:
    st.markdown("# 💰 Bank Reconciliation AI Agent")
    st.markdown("*Analisis rekonsiliasi bank otomatis dengan kekuatan AI*")

with col_header2:
    st.info("🚀 Powered by OpenAI GPT-4", icon="⚡")

st.markdown("---")

# ========================= SIDEBAR CONFIGURATION =========================
with st.sidebar:
    st.markdown("## ⚙️ Konfigurasi")
    
    api_key_input = st.text_input(
        "🔑 OpenAI API Key",
        type="password",
        placeholder="sk-...",
        value=st.session_state.api_key,
    )
    st.session_state.api_key = api_key_input
    
    st.caption("💡 Atau set `OPENAI_API_KEY` di environment variable")
    
    model_name = st.selectbox(
        "🤖 Model AI",
        options=["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
        index=0,
    )
    
    st.divider()
    
    st.markdown("### 📅 Periode & Saldo Awal")
    period_label = st.text_input(
        "Label Periode",
        value="November 2025",
        placeholder="e.g., Oktober 2025"
    )
    
    col_opening1, col_opening2 = st.columns(2)
    with col_opening1:
        opening_bank_str = st.text_input("Saldo Awal Bank", placeholder="e.g., 50.000.000")
    with col_opening2:
        opening_book_str = st.text_input("Saldo Awal Buku", placeholder="e.g., 50.000.000")
    
    opening_bank = parse_float(opening_bank_str)
    opening_book = parse_float(opening_book_str)
    
    st.divider()
    st.caption("ℹ️ Semua konfigurasi siap di sidebar. Upload file di bawah untuk mulai!")

# ========================= MAIN CONTENT =========================

# STEP 1: Upload Files
st.markdown("### 📤 Step 1: Upload File")
st.markdown("Upload file Rekening Koran Bank dan Buku Bank Anda (CSV atau Excel)")

col_bank, col_book = st.columns(2)

with col_bank:
    st.markdown("#### 🏦 Rekening Koran Bank")
    bank_file = st.file_uploader(
        "Upload Bank Statement",
        type=["csv", "xlsx", "xls"],
        key="bank_upload",
        label_visibility="collapsed"
    )

with col_book:
    st.markdown("#### 📓 Buku Bank / Pembukuan")
    book_file = st.file_uploader(
        "Upload Book Records",
        type=["csv", "xlsx", "xls"],
        key="book_upload",
        label_visibility="collapsed"
    )

# Load files
bank_df_raw = load_table_from_upload(bank_file, "Bank Statement", "bank") if bank_file else None
book_df_raw = load_table_from_upload(book_file, "Book Records", "book") if book_file else None

# Show preview jika file sudah diupload
if bank_file or book_file:
    st.divider()
    
    if bank_df_raw is not None:
        with st.expander("📊 Preview: Rekening Koran Bank", expanded=True):
            st.dataframe(bank_df_raw.head(10), use_container_width=True)
    
    if book_df_raw is not None:
        with st.expander("📊 Preview: Buku Bank", expanded=True):
            st.dataframe(book_df_raw.head(10), use_container_width=True)

# STEP 2: Column Mapping
if bank_df_raw is not None and book_df_raw is not None:
    st.markdown("---")
    st.markdown("### 🧩 Step 2: Mapping Kolom")
    st.markdown("Pilih kolom mana yang berisi tanggal, deskripsi, dan amount dari masing-masing file")
    
    col_map1, col_map2 = st.columns(2)
    
    with col_map1:
        st.markdown("#### 🏦 Bank Statement")
        bank_date_col = st.selectbox(
            "Tanggal",
            bank_df_raw.columns.tolist(),
            key="bank_date_col",
        )
        bank_desc_col = st.selectbox(
            "Deskripsi",
            bank_df_raw.columns.tolist(),
            key="bank_desc_col",
        )
        bank_amount_col = st.selectbox(
            "Amount/Nominal",
            bank_df_raw.columns.tolist(),
            key="bank_amount_col",
        )
    
    with col_map2:
        st.markdown("#### 📓 Book Records")
        book_date_col = st.selectbox(
            "Tanggal",
            book_df_raw.columns.tolist(),
            key="book_date_col",
        )
        book_desc_col = st.selectbox(
            "Deskripsi",
            book_df_raw.columns.tolist(),
            key="book_desc_col",
        )
        book_amount_col = st.selectbox(
            "Amount/Nominal",
            book_df_raw.columns.tolist(),
            key="book_amount_col",
        )
    
    # STEP 3: Run Analysis
    st.markdown("---")
    st.markdown("### 🚀 Step 3: Jalankan Analisis")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        run_button = st.button(
            "▶️ Analisis Rekonsiliasi Sekarang",
            type="primary",
            use_container_width=True,
            key="run_button"
        )
    
    if run_button:
        api_key = api_key_input or os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            st.error("❌ API Key OpenAI belum diisi. Isi di sidebar atau set environment variable OPENAI_API_KEY.")
        else:
            try:
                with st.spinner("⏳ Sedang menganalisis data reconciliation..."):
                    # Normalize dataframes
                    bank_df = normalize_df(bank_df_raw, bank_date_col, bank_desc_col, bank_amount_col, "bank")
                    book_df = normalize_df(book_df_raw, book_date_col, book_desc_col, book_amount_col, "book")
                    
                    # Merge untuk cari matching transactions
                    merged = pd.merge(
                        bank_df,
                        book_df,
                        on=["date", "amount"],
                        how="outer",
                        suffixes=("_bank", "_book"),
                        indicator=True,
                    )
                    
                    bank_only = merged[merged["_merge"] == "left_only"][
                        ["date", "description_bank", "amount"]
                    ].rename(columns={"description_bank": "description"}).reset_index(drop=True)
                    
                    book_only = merged[merged["_merge"] == "right_only"][
                        ["date", "description_book", "amount"]
                    ].rename(columns={"description_book": "description"}).reset_index(drop=True)
                    
                    ai_prompt = build_ai_prompt(
                        bank_df=bank_df,
                        book_df=book_df,
                        bank_only=bank_only,
                        book_only=book_only,
                        period_label=period_label,
                        opening_bank=opening_bank,
                        opening_book=opening_book,
                    )
                    
                    ai_response = call_ai_agent(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=ai_prompt,
                        api_key=api_key,
                        model=model_name,
                    )
                    
                    st.session_state.results = {
                        "bank_df": bank_df,
                        "book_df": book_df,
                        "bank_only": bank_only,
                        "book_only": book_only,
                        "ai_response": ai_response,
                    }
                
                st.success("✅ Analisis selesai!")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Terjadi error: {e}")

# ========================= RESULTS SECTION =========================
if st.session_state.results is not None:
    results = st.session_state.results
    bank_df = results["bank_df"]
    book_df = results["book_df"]
    bank_only = results["bank_only"]
    book_only = results["book_only"]
    ai_response = results["ai_response"]
    
    st.markdown("---")
    st.markdown("## 📊 Hasil Analisis Rekonsiliasi")
    
    # Summary metrics
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        st.metric(
            "📋 Transaksi Bank",
            len(bank_df),
            delta="Total",
            delta_color="off"
        )
    
    with col_s2:
        st.metric(
            "💰 Total Amount Bank",
            f"Rp {bank_df['amount'].sum():,.0f}",
            delta="Jumlah",
            delta_color="off"
        )
    
    with col_s3:
        st.metric(
            "📋 Transaksi Buku",
            len(book_df),
            delta="Total",
            delta_color="off"
        )
    
    with col_s4:
        st.metric(
            "💰 Total Amount Buku",
            f"Rp {book_df['amount'].sum():,.0f}",
            delta="Jumlah",
            delta_color="off"
        )
    
    # Difference calculation
    difference = abs(bank_df['amount'].sum() - book_df['amount'].sum())
    status_color = "🟢" if difference == 0 else "🟠"
    
    st.markdown(f"### {status_color} Selisih Rekonsiliasi: Rp {difference:,.0f}")
    
    st.divider()
    
    # Detailed Results Tabs
    tab1, tab2, tab3 = st.tabs([
        f"🏦 Hanya di Bank ({len(bank_only)})",
        f"📓 Hanya di Buku ({len(book_only)})",
        "🧠 Rekomendasi AI"
    ])
    
    with tab1:
        if bank_only.empty:
            st.success("✅ Tidak ada transaksi yang hanya muncul di bank.")
        else:
            st.warning(f"⚠️ Ditemukan {len(bank_only)} transaksi yang hanya ada di bank statement:")
            
            bank_only_display = bank_only.copy()
            bank_only_display['amount'] = bank_only_display['amount'].apply(lambda x: f"Rp {x:,.0f}")
            bank_only_display['date'] = pd.to_datetime(bank_only_display['date']).dt.strftime('%d-%m-%Y')
            
            st.dataframe(
                bank_only_display.rename(columns={
                    'date': 'Tanggal',
                    'description': 'Deskripsi',
                    'amount': 'Amount'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    with tab2:
        if book_only.empty:
            st.success("✅ Tidak ada transaksi yang hanya muncul di buku.")
        else:
            st.warning(f"⚠️ Ditemukan {len(book_only)} transaksi yang hanya ada di buku bank:")
            
            book_only_display = book_only.copy()
            book_only_display['amount'] = book_only_display['amount'].apply(lambda x: f"Rp {x:,.0f}")
            book_only_display['date'] = pd.to_datetime(book_only_display['date']).dt.strftime('%d-%m-%Y')
            
            st.dataframe(
                book_only_display.rename(columns={
                    'date': 'Tanggal',
                    'description': 'Deskripsi',
                    'amount': 'Amount'
                }),
                use_container_width=True,
                hide_index=True
            )
    
    with tab3:
        st.markdown(ai_response)
        
        # Export button
        st.divider()
        col_export1, col_export2 = st.columns([1, 1])
        
        with col_export1:
            # Export bank_only
            csv_bank = bank_only.to_csv(index=False)
            st.download_button(
                label="📥 Download Bank Only (CSV)",
                data=csv_bank,
                file_name=f"bank_only_{period_label}.csv",
                mime="text/csv"
            )
        
        with col_export2:
            # Export book_only
            csv_book = book_only.to_csv(index=False)
            st.download_button(
                label="📥 Download Book Only (CSV)",
                data=csv_book,
                file_name=f"book_only_{period_label}.csv",
                mime="text/csv"
            )
    
    st.divider()
    
    # Reset button
    if st.button("🔄 Mulai Analisis Baru", use_container_width=True):
        st.session_state.results = None
        st.rerun()

else:
    if bank_file is None or book_file is None:
        st.info("📤 Upload kedua file untuk memulai proses rekonsiliasi.", icon="ℹ️")