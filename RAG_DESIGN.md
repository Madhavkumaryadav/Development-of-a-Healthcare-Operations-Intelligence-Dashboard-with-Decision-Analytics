# RAG Design

This pass uses `src/report_store.py` and a local `reports/rag_index.json`
vector store. A query without a matching generated report returns an explicit
no-report answer. The answer path applies this guardrail:

> Answer only using the provided report excerpts. If they don't contain the
> answer, say so explicitly - do not guess or use outside knowledge.

The UI displays retrieved report text/IDs and stores the question, answer,
sources, rating, comment, and UTC timestamp in `reports/feedback.jsonl`.

After login, `app.py` automatically generates fresh PDF/JSON snapshots for
the five data-backed dashboards and indexes their JSON sections. The Home
page provides an explicit ZIP download containing those snapshots. Browsers
do not permit a server to silently download files on page load, so generation
and indexing are automatic while the download remains user-triggered.

This is retrieval indexing rather than model training: the local store is
replaced per stable dashboard report ID, and answers are produced only from
the indexed report excerpts.

Recommended chunk metadata includes `source_collection`, `record_ids`,
`date_range`, and `generated_at`. Build chunks from aggregated dashboard facts
and ML outputs rather than OCR so citations point back to structured data.

The generation prompt requires answers to use only supplied context and to
state when the data is insufficient. Create an Atlas Vector Search index on
`rag_chunks.embedding` before enabling retrieval.