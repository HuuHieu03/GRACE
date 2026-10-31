# Files to use from B0_offline_final/

For the exported Bước 0 outputs, use these exact join files:

- `devign_test_join_exact.csv`
- `reveal_test_join_exact.csv`
- `devign_validation_join_partial.csv` (only 2,724/2,732 validation rows)

The older `*_join.csv` / `*_join_grouped.csv` files elsewhere in the original archive are retained as source artifacts; their `p_gate` may be from an earlier checkpoint audit. The `*_join_exact.csv` files in this folder replace `p_gate` from verified `xpre[:,5]` and match `code_sha256` by ID. For ReVeal the old grouped join differed by as much as 0.0487 in p_gate, so do not use it for the final analysis.

Validation remains incomplete: 8 Devign and 77 ReVeal expert outputs need recovery. The JSON complementarity analyses and historical metric reproduction are therefore not final.
