# 🧠 AI Bank Reconciliation Agent — Product Roadmap

## 🎯 Product Vision
Enable accountants and finance teams to complete bank reconciliations **faster, more accurately, and consistently** — without relying on spreadsheet work or repetitive manual reviews.

The goal is **not to replace accountants**, but to provide a reliable AI assistant that:
- speeds up daily work,
- standardizes reconciliation steps,
- ensures compliance and traceability across periods.

---

## 📌 Current Status — `v0.1` (MVP)
**Working features:**
- Upload bank statements & book records (CSV/Excel).
- Column mapping UI.
- Automatic data normalization.
- Transaction matching (exact match on `date + amount`).
- Detection of `bank-only` and `book-only` transactions.
- AI-powered reconciliation explanation (structured and educational).
- CSV export for unmatched transactions.
- Modular code structure via `src/` — ready for scaling.

---

## 🚧 Next Iteration — `v0.2`
**Goal:** improve accuracy and flexibility of reconciliation.

| Priority | Feature | Purpose |
|----------|---------|---------|
| ⭐⭐⭐ | Date / amount tolerance (± days / ± amount) | Handle small mismatches |
| ⭐⭐⭐ | Auto-tagging reasons (fees, interest, timing) | Faster review workflow |
| ⭐⭐ | PDF export of reconciliation summary | Attach to audit reports |
| ⭐⭐ | Date format templates | Support varied file formats |
| ⭐ | Reconciliation log trail | Compliance / audit trail |

---

## 🔜 Planned Enhancements — `v0.3`
**Goal:** usable across multiple companies and institutions.
- Fuzzy matching for description similarity.
- Bank-specific templates (BRI, BCA, Mandiri, BSI, etc.).
- Saved configurations per bank format.
- Reason auto-tagging (fee / timing difference / deposit in transit / etc).
- Excel/PDF reconciliation report with journal suggestions.

---

## 🧱 Towards SaaS Architecture — `v0.4`
**Goal:** make the core reconciliation engine reusable.
- Extract logic into standalone Python package (`pip install ai-bank-recon`).
- Build FastAPI backend for API usage.
- Streamlit becomes frontend layer only.
- Optional AI models (Claude / Azure OpenAI / local model).
- Ready for ERP / Telegram / Google Sheets integrations.

---

## 🧭 Long-Term Vision — `v1.0+`
**Goal:** production-ready reconciliation assistant.
- Role-based user layers (staff → supervisor → manager).
- Auto-journaling to bookkeeping systems (SQL/Excel).
- Collaboration flow (comment / approve / lock).
- ERP or Telegram Bot integration.
- Accuracy scoring: AI vs manual reconciliation.

---

## 📎 Developer Notes
### Current Structure

ai-bank-recon/
├─ app.py
├─ src/
│ ├─ core/
│ ├─ io/
│ └─ utils/
├─ data_samples/
└─ README.md


### Coding Principles
- UI should stay minimal — real logic lives in `src/`.
- Every new feature must be unit-testable (not tied to UI events).
- Streamlit = presentation layer only.
- Think maintainability and modularity first.

---

## 🧠 Feature Parking Lot (Ideas for later)
- Multiple account reconciliation (batch).
- Reconciliation quality score (AI vs human).
- Auto-detection of late bookkeeping entries.
- Export audit-friendly reconciliation packet.
- Synthetic training datasets for model fine-tuning.

---

## 💡 New Contributors — Start Here
**First tasks:**
1. Run `app.py` → understand end-to-end workflow.
2. Explore folder `src/` → learn modular structure.
3. Review `v0.2` targets → pick one feature.
4. Create a branch → make a small PR.

---

**🪙 Motto**  
> Reconciliation should not be a late-night task.

**📩 Development Discussion**  
Use GitHub Issues or Discussions tab.
