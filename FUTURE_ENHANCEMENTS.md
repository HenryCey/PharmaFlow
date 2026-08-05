# PharmaFlow — Future Enhancements Backlog

Deliberate scope decisions made during development that are acceptable
for the current release but worth revisiting in a later version. Not a
bug list — see CHANGELOG.md's "Known Limitations" sections for those.

---

## Costing Method: "Last Cost Wins" (documented as of Sprint 4, v1.3.0)

**Current behavior:** When a Purchase Order is received (`apps/purchases/receiving_service.py`),
the drug's catalog `cost_price` and `selling_price` are overwritten with
the just-received batch's values. If a drug is received from multiple
suppliers or at different costs over time, the catalog price always
reflects only the *most recently received* batch — not an average, not
FIFO, and not supplier-specific.

**Why this is acceptable for Sprint 4:** There is no per-batch/FEFO-aware
pricing at POS yet (Sale still sells against the single catalog
`selling_price`), and Sprint 4's scope was completing the inventory
lifecycle (Supplier → Purchase Order → Goods Receipt → Ledger), not
costing methodology. This was a deliberate, flagged design decision, not
an oversight.

**Recommended future work (v2.x+):**
- **Weighted Average Cost** — recompute `cost_price` as a quantity-weighted
  average across all non-expired batches on hand, rather than replacing
  it outright.
- **FIFO costing** — track batches as discrete cost layers and consume the
  oldest batch's cost first when calculating Cost of Goods Sold.
- **Supplier-specific pricing** — allow the same drug to carry different
  cost/selling prices per supplier relationship.
- **Batch-aware selling** — POS/checkout selects which batch to sell from
  (e.g. First-Expiry-First-Out), rather than assuming a single current
  price for the whole drug.
- Any of the above would also require Reports (Sprint 5+) to calculate
  Cost of Goods Sold and profit against the correct costing method,
  rather than the simple "current catalog price" snapshot used today.

**Where this is also documented:** inline in
`apps/purchases/receiving_service.py`'s docstring, and will be repeated
in `CHANGELOG.md`'s Known Limitations for the v1.3.0 release.
