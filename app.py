import os

import pandas as pd
import streamlit as st

from src.core.ai import SYSTEM_PROMPT, build_ai_prompt, call_ai_agent
from src.core.recon import normalize_df, reconcile_frames
from src.io.loaders import load_table_from_upload
from src.utils.parsing import parse_float

# ========================= PAGE CONFIG =========================
st.set_page_config(
    page_title="Bank Reconciliation AI Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
        placeholder="e.g., Oktober 2025",
    )

    col_opening1, col_opening2 = st.columns(2)
    with col_opening1:
        opening_bank_str = st.text_input(
            "Saldo Awal Bank", placeholder="e.g., 50.000.000"
        )
    with col_opening2:
        opening_book_str = st.text_input(
            "Saldo Awal Buku", placeholder="e.g., 50.000.000"
        )

    opening_bank = parse_float(opening_bank_str)
    opening_book = parse_float(opening_book_str)

    st.divider()
    st.caption("ℹ️ Semua konfigurasi siap di sidebar. Upload file di bawah untuk mulai!")

# ========================= MAIN CONTENT =========================

# STEP 1: Upload Files
st.markdown("### 📤 Step 1: Upload File")
st.markdown(
    "Upload file Rekening Koran Bank dan Buku Bank Anda (CSV atau Excel)"
)

col_bank, col_book = st.columns(2)

with col_bank:
    st.markdown("#### 🏦 Rekening Koran Bank")
    bank_file = st.file_uploader(
        "Upload Bank Statement",
        type=["csv", "xlsx", "xls"],
        key="bank_upload",
        label_visibility="collapsed",
    )

with col_book:
    st.markdown("#### 📓 Buku Bank / Pembukuan")
    book_file = st.file_uploader(
        "Upload Book Records",
        type=["csv", "xlsx", "xls"],
        key="book_upload",
        label_visibility="collapsed",
    )

# Load files
bank_df_raw = (
    load_table_from_upload(bank_file, "Bank Statement", "bank")
    if bank_file
    else None
)
book_df_raw = (
    load_table_from_upload(book_file, "Book Records", "book")
    if book_file
    else None
)

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
    st.markdown(
        "Pilih kolom mana yang berisi tanggal, deskripsi, dan amount dari "
        "masing-masing file"
    )

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
            key="run_button",
        )

    if run_button:
        api_key = api_key_input or os.getenv("OPENAI_API_KEY")

        if not api_key:
            st.error(
                "❌ API Key OpenAI belum diisi. Isi di sidebar atau set "
                "environment variable OPENAI_API_KEY."
            )
        else:
            try:
                with st.spinner(
                    "⏳ Sedang menganalisis data reconciliation..."
                ):
                    # Normalize
                    bank_df_norm = normalize_df(
                        bank_df_raw,
                        bank_date_col,
                        bank_desc_col,
                        bank_amount_col,
                        "bank",
                    )
                    book_df_norm = normalize_df(
                        book_df_raw,
                        book_date_col,
                        book_desc_col,
                        book_amount_col,
                        "book",
                    )

                    (
                        bank_df,
                        book_df,
                        bank_only,
                        book_only,
                        difference,
                    ) = reconcile_frames(bank_df_norm, book_df_norm)

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
                        "difference": difference,
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
    difference = results["difference"]
    ai_response = results["ai_response"]

    st.markdown("---")
    st.markdown("## 📊 Hasil Analisis Rekonsiliasi")

    # Summary metrics
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)

    with col_s1:
        st.metric("📋 Transaksi Bank", len(bank_df), delta="Total", delta_color="off")

    with col_s2:
        st.metric(
            "💰 Total Amount Bank",
            f"Rp {bank_df['amount'].sum():,.0f}",
            delta="Jumlah",
            delta_color="off",
        )

    with col_s3:
        st.metric("📋 Transaksi Buku", len(book_df), delta="Total", delta_color="off")

    with col_s4:
        st.metric(
            "💰 Total Amount Buku",
            f"Rp {book_df['amount'].sum():,.0f}",
            delta="Jumlah",
            delta_color="off",
        )

    status_color = "🟢" if difference == 0 else "🟠"
    st.markdown(
        f"### {status_color} Selisih Rekonsiliasi: Rp {difference:,.0f}"
    )

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        [
            f"🏦 Hanya di Bank ({len(bank_only)})",
            f"📓 Hanya di Buku ({len(book_only)})",
            "🧠 Rekomendasi AI",
        ]
    )

    with tab1:
        if bank_only.empty:
            st.success("✅ Tidak ada transaksi yang hanya muncul di bank.")
        else:
            st.warning(
                f"⚠️ Ditemukan {len(bank_only)} transaksi yang hanya ada di bank statement:"
            )

            bank_only_display = bank_only.copy()
            bank_only_display["amount"] = bank_only_display["amount"].apply(
                lambda x: f"Rp {x:,.0f}"
            )
            bank_only_display["date"] = pd.to_datetime(
                bank_only_display["date"]
            ).dt.strftime("%d-%m-%Y")

            st.dataframe(
                bank_only_display.rename(
                    columns={
                        "date": "Tanggal",
                        "description": "Deskripsi",
                        "amount": "Amount",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with tab2:
        if book_only.empty:
            st.success("✅ Tidak ada transaksi yang hanya muncul di buku.")
        else:
            st.warning(
                f"⚠️ Ditemukan {len(book_only)} transaksi yang hanya ada di buku bank:"
            )

            book_only_display = book_only.copy()
            book_only_display["amount"] = book_only_display["amount"].apply(
                lambda x: f"Rp {x:,.0f}"
            )
            book_only_display["date"] = pd.to_datetime(
                book_only_display["date"]
            ).dt.strftime("%d-%m-%Y")

            st.dataframe(
                book_only_display.rename(
                    columns={
                        "date": "Tanggal",
                        "description": "Deskripsi",
                        "amount": "Amount",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with tab3:
        st.markdown(ai_response)

        st.divider()
        col_export1, col_export2 = st.columns([1, 1])

        with col_export1:
            csv_bank = bank_only.to_csv(index=False)
            st.download_button(
                label="📥 Download Bank Only (CSV)",
                data=csv_bank,
                file_name=f"bank_only_{period_label}.csv",
                mime="text/csv",
            )

        with col_export2:
            csv_book = book_only.to_csv(index=False)
            st.download_button(
                label="📥 Download Book Only (CSV)",
                data=csv_book,
                file_name=f"book_only_{period_label}.csv",
                mime="text/csv",
            )

    st.divider()

    if st.button("🔄 Mulai Analisis Baru", use_container_width=True):
        st.session_state.results = None
        st.rerun()
else:
    if bank_file is None or book_file is None:
        st.info(
            "📤 Upload kedua file untuk memulai proses rekonsiliasi.",
            icon="ℹ️",
        )
