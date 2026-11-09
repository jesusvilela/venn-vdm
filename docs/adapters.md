# Store adapters

<!-- docs-navigation:start -->
[Documentation](README.md) · [Get started](getting-started.md) · [Concepts](concepts.md) · [Venn vs Jev](venn-and-jev.md) · [Examples](../examples/README.md) · [Task recipes](cookbooks.md) · **Adapters** · [API](api.md) · [Results](evidence.md)

<details>
<summary>Browse all documentation</summary>

**Project home:** [Home](../README.md)

**Start here:** [Documentation overview](README.md) · [Getting started](getting-started.md) · [Installation](installation.md) · [Concepts](concepts.md) · [Venn vs Jev](venn-and-jev.md)

**Task guides:** [Task recipes](cookbooks.md) · **Store adapters** · [Outcome stores](outcome-api.md)

**Examples:** [Choose an example](../examples/README.md) · [Hot dog image classifier](../examples/hotdog/README.md) · [Precedent Desk](../examples/precedent_desk/README.md) · [Wine predictor](../examples/wine/README.md) · [Audio classifier](../examples/audio/README.md) · [Screen-only arena](arena-example.md) · [Demos and videos](demos.md)

**Reference:** [API reference](api.md) · [Design rationale](design.md) · [Venn 1 model card](model-card.md)

**Results and limits:** [Performance and cost](performance.md) · [VennSpace-1](benchmark.md) · [Results and evidence](evidence.md) · [Reproduction](reproduction.md) · [Semantic boundary findings](redteam.md) · [Limitations](limitations.md) · [Comparison video methods](same-memory-video.md) · [Comparison notebooks and renderer](../examples/same_memory_video/README.md)

**Project:** [Policies](policies.md) · [Licenses and attribution](licenses.md) · [Contributing to Venn](../CONTRIBUTING.md)

**Maintainers:** [Maintainer guide](maintainers/maintaining.md) · [Documentation site](maintainers/website.md) · [Release checklist](maintainers/release-checklist.md) · [Publishing the Python package](maintainers/pypi.md) · [Publishing the decision head](maintainers/publishing-the-head.md) · [Development evidence](maintainers/development-evidence.md) · [Comparative evaluation protocol](maintainers/evaluation-plan.md) · [License audit notes](maintainers/license-audit.md)

</details>

**Task guides / Store adapters**
<!-- docs-navigation:end -->

<!-- docs-contents:start -->
<details>
<summary>On this page</summary>

- [Supported stores](#supported-stores)
- [Indexed or exact search](#indexed-or-exact-search)
- [Install and prepare your data](#install-and-prepare-your-data)
- [Shared usage](#shared-usage)
- [FAISS](#faiss)
- [PostgreSQL and pgvector](#postgresql-and-pgvector)
- [Qdrant](#qdrant)
- [Weaviate](#weaviate)
- [LanceDB](#lancedb)
- [Microsoft Azure AI Search](#microsoft-azure-ai-search)
- [Operational limits and validation](#operational-limits-and-validation)

</details>
<!-- docs-contents:end -->

Connect an existing vector store to Venn without copying it into a new database.
Adapters read application-owned vectors and outcomes; the application owns the
client, credentials, schema, writes and connection lifetime.

## Supported stores

| Backend | Batch reader | Outcome search | Search and visibility |
| --- | --- | --- | --- |
| FAISS | `FaissAdapter` | `FaissOutcomeAdapter` | App-supplied squared-L2 index; app serializes reads and writes. |
| PostgreSQL / pgvector | `PgVectorAdapter` | `PgVectorOutcomeAdapter` | Filtered squared L2; visibility follows the cursor's transaction. |
| Qdrant | `QdrantAdapter` | `QdrantOutcomeAdapter` | Index-based filtered search by default; outcome collections require an unnamed Euclidean vector. |
| Weaviate | `WeaviateAdapter` | `WeaviateOutcomeAdapter` | Filtered nearest vectors; backend metric and replication semantics apply. |
| LanceDB | `LanceDBAdapter` | `LanceDBOutcomeAdapter` | Prefiltered squared L2; outcome queries check out the latest table version. |
| Microsoft Azure AI Search | `AzureSearchAdapter` | `AzureSearchOutcomeAdapter` | Configured vector index with prefilters by default; indexing is eventually consistent. |

Use a **batch reader** to stream stored vectors into a sweep or other
vector-consuming workflow. Its `batches(batch_size=...)` method yields dictionaries
with `ids`, float32 `vectors`, optional `outcomes`, `profile` and `revision`.
Batch readers require the pinned 768-dimensional text profile.

Use an **outcome adapter** with `OutcomeService` to choose among actions using
their nearest recorded cases. Each search applies the option and metadata
constraints before top-k. Outcome adapters carry a complete `VectorTag`;
they can use other supported representations when the stored and query tags
match exactly. Registration does not copy the store into a snapshot.

## Indexed or exact search

Outcome searches should normally use the store's vector index as the corpus
grows. An exhaustive scan can be reasonable below roughly 5,000-10,000 vectors
or when measuring exact recall, but that is a workload guideline, not an
automatic cutoff. Dimension, filter selectivity, hardware and latency targets
also matter. Venn does not count the collection on every request or switch
search modes behind the application's back.

`AzureSearchOutcomeAdapter` defaults to `exhaustive=False`, allowing the
configured vector index to serve the query. Use an HNSW vector profile for
indexed approximate search; an `exhaustiveKnn` profile still scans.
Set `exhaustive=True` explicitly for a small corpus or an exact reference run.
`QdrantOutcomeAdapter` similarly defaults to `exact=False`; set `exact=True`
to force a full exact search. Both modes retain option and metadata prefilters.

For pgvector, Weaviate and LanceDB, the adapter leaves index use to the backend:
provision a compatible vector index and tune its search parameters. Their
planners may still scan a small or highly selective subset. FAISS uses the
app-supplied index on unfiltered queries; its current metadata-filtered path
builds an exact eligible subset instead. That filtered path is not a scalable
ANN search; use smaller app-owned partitions or a filter-aware database for
large filtered collections.

Indexed approximate search trades recall for speed and can change which cases,
and therefore which outcome, Venn returns. Measure recall and decision quality
against exact search on representative queries before deployment. Batch readers
are different: they intentionally visit every stored row rather than perform
nearest-neighbor search.

## Install and prepare your data

FAISS is included in the base installation. From a source checkout, install
the other clients with:

```bash
python -m pip install -e ".[adapters]"
```

See [installation](installation.md) for Python and PyTorch setup. Import adapter
classes from `venn.adapters`.

The examples below open existing, populated stores. They do not create services,
indexes or credentials. Each stored case has:

| Field | Example type | Meaning |
| --- | --- | --- |
| `id` | String | Unique case identifier. |
| `embedding` | 768 floats | Vector from the exact pinned text reader and protocol. |
| `option` | String | The action taken, such as `billing` or `technical`. |
| `outcome` | Number | The observed utility of that action. Higher is better in these examples. |
| `tenant` | String | Application metadata used by the example equality filter. |

Change the fields, options and filters to match your application. A dimension
match alone does not establish compatibility: adapters trust the profile/tag
you declare; they do not prove which reader produced existing vectors.
Follow [profile compatibility](concepts.md#profiles-and-compatibility) before
connecting a store. These adapters do not generate embeddings or write feedback.

## Shared usage

Run this setup before one of the backend examples. Export one compatible query
vector to `query-vector.npy`, with shape `(768,)`; it must use the same pinned
reader and protocol as the stored cases. Do not query a production index with
arbitrary synthetic vectors.

```python
import numpy as np

from venn import OutcomeService, TEXT_TAG, VENN_1

pin = {"profile": VENN_1.id, "revision": VENN_1.revision}
query_vector = np.load("query-vector.npy", allow_pickle=False)


def scan(adapter):
    for batch in adapter.batches(batch_size=256):
        print(batch["ids"], batch["vectors"].shape)
        # Consume this batch before requesting the next one.


def decide(adapter):
    service = OutcomeService()
    store = service.register_store(adapter)
    result = service.decide_batch(
        [{"vector": query_vector.tolist(), "tag": TEXT_TAG.to_dict()}],
        {"route": {
            "type": "nearest_outcome",
            "store": store,
            "options": ["billing", "technical"],
            "filters": {"tenant": "demo"},
            "k": 3,
        }},
    )
    print(result["results"][0]["answers"]["route"])
```

`decide` runs without a trained head or reader download because the query is
already embedded. Its answer includes per-option support, outcome means and
evidence IDs. Empty or insufficiently supported options are not evidence.
See [outcome stores](outcome-api.md) for `min_support`, minimizing costs,
exploration and the HTTP setup.

## FAISS

For this example, `case-vectors.npy` holds an `(N, 768)` array and
`case-metadata.json` holds an aligned list of `id`, `option`, `outcome` and
`tenant` dictionaries in exactly the same row order.

```python
import json

import faiss

from venn.adapters import FaissAdapter, FaissOutcomeAdapter

vectors = np.ascontiguousarray(
    np.load("case-vectors.npy", allow_pickle=False), dtype=np.float32
)
with open("case-metadata.json", encoding="utf-8") as source:
    cases = json.load(source)
if len(vectors) != len(cases):
    raise ValueError("Vectors and metadata must have the same row count")

index = faiss.IndexFlatL2(VENN_1.dimensions)
index.add(vectors)
scan(FaissAdapter(
    index, [case["id"] for case in cases],
    [case["outcome"] for case in cases], **pin,
))

partitions = {}
for option in ("billing", "technical"):
    positions = [i for i, case in enumerate(cases) if case["option"] == option]
    option_index = faiss.IndexFlatL2(VENN_1.dimensions)
    option_index.add(np.ascontiguousarray(vectors[positions]))
    partitions[option] = {
        "index": option_index,
        "ids": [cases[i]["id"] for i in positions],
        "outcomes": [cases[i]["outcome"] for i in positions],
        "metadata": [{"tenant": cases[i]["tenant"]} for i in positions],
    }

decide(FaissOutcomeAdapter(partitions, tag=TEXT_TAG))
```

Batch indexes must support vector reconstruction. Outcome indexes must use
squared L2 and have aligned ID, outcome and optional metadata lists per option.
The application must update those lists and indexes together and serialize
reads and writes. Filtered reads build an exact eligible subset before search.
The flat indexes in this example are intended for small collections. For large
unfiltered collections, supply a suitable ANN index instead; see
[indexed or exact search](#indexed-or-exact-search) for the filtered-path limit.

## PostgreSQL and pgvector

Provision PostgreSQL with the `vector` extension and a populated `cases` table
whose `embedding` column is `vector(768)`. Set `DATABASE_URL` to your connection
string. The example uses a server-side cursor for bounded batch reads and a
regular cursor for outcome queries.

```python
import os

import psycopg
from pgvector.psycopg import register_vector

from venn.adapters import PgVectorAdapter, PgVectorOutcomeAdapter

with psycopg.connect(os.environ["DATABASE_URL"]) as connection:
    register_vector(connection)
    with connection.cursor(name="venn_scan") as cursor:
        scan(PgVectorAdapter(cursor, "cases", outcome_column="outcome", **pin))
    with connection.cursor() as cursor:
        decide(PgVectorOutcomeAdapter(cursor, "cases", tag=TEXT_TAG))
```

Use `id_column`, `vector_column` and `outcome_column` to rename fields; the
outcome adapter also accepts `option_column`. Table and column names must be
simple identifiers, not SQL expressions or dotted schema paths. Filter values
are SQL parameters. Choose transaction isolation and commit boundaries to
provide the visibility your application needs; a retained snapshot can hide
external writes.

## Qdrant

Set `QDRANT_URL` and, if required, `QDRANT_API_KEY`. The populated `cases`
collection must use an **unnamed**, 768-dimensional **Euclidean** vector for
outcome searches, with `option`, `outcome` and `tenant` in each point's payload.

```python
import os
from contextlib import closing

from qdrant_client import QdrantClient

from venn.adapters import QdrantAdapter, QdrantOutcomeAdapter

with closing(QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ.get("QDRANT_API_KEY"),
)) as client:
    scan(QdrantAdapter(client, "cases", outcome_key="outcome", **pin))
    decide(QdrantOutcomeAdapter(client, "cases", tag=TEXT_TAG))
```

The batch reader also supports named vectors through `vector_name`.
`QdrantOutcomeAdapter` does not: it checks for an unnamed Euclidean collection
matching the tag. Complete application writes with `wait=True` before depending
on their visibility. Outcomes permit the backend vector index by default and
report squared distances. Set `exact=True` on the outcome adapter to force
exhaustive search for small collections or an exact reference measurement.

## Weaviate

This example connects to a local Weaviate instance at the SDK's default HTTP
and gRPC ports. Use an application-configured authenticated client for a remote
deployment. The existing `Cases` collection must hold a single default vector
from the pinned reader, with `option`, `outcome` and `tenant` properties.

```python
import weaviate

from venn.adapters import WeaviateAdapter, WeaviateOutcomeAdapter

with weaviate.connect_to_local() as client:
    collection = client.collections.use("Cases")
    scan(WeaviateAdapter(collection, outcome_key="outcome", **pin))
    decide(WeaviateOutcomeAdapter(collection, tag=TEXT_TAG))
```

The batch reader can select a named vector with `vector_name`. The outcome
adapter uses the collection's default vector search and has no named-vector
selector. Change property names through `outcome_key` and, for outcomes,
`option_key`. Distances retain the collection's metric semantics. Replication
consistency controls when writes become visible.

## LanceDB

Set `LANCEDB_URI` to your database. The existing `cases` table needs an
`embedding` vector column containing 768-element vectors, plus the shared
metadata fields above.

```python
import os

import lancedb

from venn.adapters import LanceDBAdapter, LanceDBOutcomeAdapter

table = lancedb.connect(os.environ["LANCEDB_URI"]).open_table("cases")
scan(LanceDBAdapter(
    table, vector_column="embedding", outcome_column="outcome", **pin,
))
decide(LanceDBOutcomeAdapter(table, vector_column="embedding", tag=TEXT_TAG))
```

Use `id_column`, `vector_column`, `outcome_column` and, for outcomes,
`option_column` to match your schema. Outcome queries check out the latest
table version before a fresh prefiltered L2 search. Complete the app's writes
first; the adapter does not write or manage transactions.

## Microsoft Azure AI Search

Set `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX` and `AZURE_SEARCH_KEY`.
Supply an existing synchronous `SearchClient`; an application-owned Microsoft
Entra credential can also be used instead of the API key shown here.

```python
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from venn.adapters import AzureSearchAdapter, AzureSearchOutcomeAdapter

with SearchClient(
    endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
    index_name=os.environ["AZURE_SEARCH_INDEX"],
    credential=AzureKeyCredential(os.environ["AZURE_SEARCH_KEY"]),
) as client:
    scan(AzureSearchAdapter(client, outcome_field="outcome", **pin))
    decide(AzureSearchOutcomeAdapter(client, tag=TEXT_TAG))
```

Default fields are `id`, `embedding`, `option` and `outcome`. Rename them with
`id_field`, `vector_field`, `outcome_field` and, for outcomes, `option_field`.
Only simple top-level field names are supported.

For batch scans, vectors must be retrievable and the unique string key must
be filterable and sortable. Scans advance by key, not skip offset, return at
most 1,000 documents per batch, and are not snapshots.

For outcomes, the vector field's dimensions and reader must match the declared
tag. ID and outcome fields must be retrievable; option and metadata fields
must be filterable scalars. Equality filters support strings, numbers, booleans
and nulls. The adapter sends one vector query per option and state,
with `preFilter`, no text search and no hybrid score fusion. It does not configure
or inspect the index schema. The default `exhaustive=False` uses the index's
configured algorithm; `exhaustive=True` explicitly opts into brute-force search.

Distances use Azure's inverse vector score, `(1 - score) / score`: this is
cosine distance for a cosine index; other metrics retain the backend's scale,
not a promised squared-L2 unit. Indexing is eventually consistent. A successful
upload is not a search-visibility guarantee: poll filtered search until the
expected cases are visible before relying on them for subsequent decisions.

## Operational limits and validation

Batch readers are not snapshot exporters. Keep the underlying corpus stable
or record its version when using scans for an evaluation. Do not compare
distance magnitudes across backends with different metric conventions.

Only the FAISS outcome adapter implements the optional float16 exact-key
`exact_match` utility override, and only when configured with float16 query keys.
This override is different from the Azure `exhaustive` and Qdrant `exact`
nearest-neighbor search controls.
Compiling an outcome store into a head additionally requires an adapter with
`export()`; the provided FAISS outcome adapter supplies it.

From a development checkout, run adapter contracts with:

```bash
python -m pip install -e ".[dev,adapters]"
python -m pytest -q tests/test_adapters_mcp.py tests/test_outcome_api.py tests/test_azure_search_adapter.py
```

These include optional local Qdrant and LanceDB checks and Azure's real SDK
against a test HTTP transport. They do not replace integration validation
against a provisioned PostgreSQL, Weaviate or Azure AI Search service.
Validate your deployment's schema, permissions, filters and write visibility
before using its results.

<!-- docs-pager:start -->
---

[← Previous: Task recipes](cookbooks.md) · [Next: Outcome stores →](outcome-api.md) · [Documentation home](README.md)
<!-- docs-pager:end -->
