# H2: shared candidate archive and offline selection comparison

Status (2026-10-22): Kaggle version 1 COMPLETE; results downloaded and all 100
full-bank searches, rankings and selections replayed locally. R1 changes 0/100
choices; active evidence and same-family candidates are available for 36/100
queries, and R1 falls back for 64/100. See
[the audited report](results_2026-10-22/report.md). No LLM was called.

Post-H2 follow-up: [technical audit and independent review preparation](followup_2026-10-22/report.md).
The 58-query Unknown inventory and 100-case relevance packet are prepared;
independent reviewer sheets remain unfilled.

E1.3 follow-up: [syntax exclusions and output-role implementation](../sink_evidence_v13/report.md).
The experimental extractor passed 63 focused tests together with review tooling,
E1.2 and H2 policy regressions. It preserves recognized sites on canonical100
and fresh validation50; no production/reranker integration or new H2 run yet.
Current project status: [H2/E1.3 progress](../../progress/v1.0.0_2026-10-22_h2_and_e13_progress.md).

Notebook: https://www.kaggle.com/code/huuhieu3333/grace-h2-shared-top50-r0-r1

Frozen execution commit: `827aab9b50039647f2f1136dee3c6a1fa5640374`.
Notebook deployment commit: `e559873`. Submission command:
`kaggle kernels push -p kaggle_notebooks/retrieval_h2 -t 7200`.
The API initially accepted version 1 as QUEUED; its final status is COMPLETE.

The notebook in `kaggle_notebooks/retrieval_h2` clones this Git repository and
checks out an exact committed revision. It reads the tracked compact CPG gzip
and canonical query split directly; no dataset upload or ZIP is required.
Deploy with `kaggle kernels push -p kaggle_notebooks/retrieval_h2`, then inspect
`kaggle kernels status huuhieu3333/grace-h2-shared-top50-r0-r1`.
Both tokenizer and safetensors weights use pinned CodeT5 revisions; no LLM
service or credentials are used. Source labels remain outside ranking.

The installed Transformers version must support T5EncoderModel and safetensors
or the original PyTorch checkpoint. PyTorch-bin loading may require a current
PyTorch version; the loader fails rather than silently initializing weights.
Download failures or incompatible dependencies stop execution. GPU memory
errors can be handled by lowering `--batch-size`; the completed embedding
batches are checkpointed. Preserve both NPY and adjacent JSON files when
resuming. Resume requires the same model assets, device, input order and code.

Local command (explicit directories containing weights and tokenizer/config):

```powershell
python scripts/run_retrieval_h2.py --model C:/path/to/weights --tokenizer C:/path/to/tokenizer --device cpu --batch-size 8
```

Protocol: exactly 21,854 train functions and canonical 100 dev queries; genuine
CodeT5 768-dimensional attention-mask mean embeddings, maximum 512 tokens,
no normalization, exact Euclidean L2 top 50. L2 ties retain train row order.
Opaque row IDs replace source names. Graph inputs retain node type/label and
counts, excluding filenames and node IDs. Source labels are written separately
to `private_source_map.json` for traceability and are never consulted by policy.

Both arms use the same E1.2-adapted score:
`0.3*(0.7*code_jaccard + 0.3*graph_similarity) + 0.7*security`, where security is
`0.35*sink + 0.25*legacy_sanitizer + 0.20*legacy_memory + 0.20*legacy_clues`.
Sink similarity uses only active E1.2 callsites:
`0.6*API_jaccard + 0.4*family_jaccard`; empty sets score zero.
Legacy non-sink subcomponents retain their four-decimal rounding. Final scores
are rounded to four decimals; ties retain L2 order. This is an experimental
adapter, not a replay of the original B2 implementation.

R0 selects the first ranked candidate. R1 selects the first candidate in that
same ranking with an active family shared with the query; otherwise R1 falls
back to R0. Unknown calls and conditional-only evidence do not force matches.
Both choose one example. E1.2 does not prove runtime execution or effective
guards. Legacy memory similarity still rewards equal absent flags; that
limitation is shared by both arms. Compact graphs are approximate, not full CPGs.

Outputs under `h2_output`:

- `shared_top50.json`: identical candidate pool, distances, scores, callsite
  evidence, complete R0 order, both choices and fallback reasons per query.
- `summary.json`: evidence coverage, eligible-candidate availability, choice
  changes, conditional-only queries and fallback counts. These are selection
  diagnostics, not accuracy/F1 or independently assessed relevance.
- `manifest.json`, embedding sidecars: input/source/model asset hashes,
  tokenizer vocabulary check, pooling configuration and resumable progress.
- `private_source_map.json`: restricted source-to-opaque mapping.

After execution, inspect these outputs and conduct relevance review before
deciding whether to run the paired LLM prediction experiment. Do not reuse the
earlier label-conditioned B3 review as independent validation of this policy.
