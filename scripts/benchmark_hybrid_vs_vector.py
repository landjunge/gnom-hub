"""Realistic bench v2: MENTIONS korrekt + hash-based embeddings."""
import sys, time, shutil
sys.path.insert(0, 'src')
import numpy as np
from gnom_hub.memory_tkg.kuzu_backend import KuzuDBBackend
from gnom_hub.memory_tkg.models import Entity, Fact, Mention
from gnom_hub.memory_tkg.retrieval_engine import RetrievalEngine

def real_embed(text, dim=384):
    import hashlib
    h = hashlib.sha512(text.encode("utf-8")).digest()
    vec = np.zeros(dim, dtype=np.float32)
    for i in range(dim):
        vec[i] = (h[i % len(h)] ^ h[(i * 7 + 13) % len(h)]) / 255.0
    return vec / np.linalg.norm(vec)

TOPICS = {
    "KuzuDB": ["backend", "graph", "hnsw"],
    "FAISS": ["index", "similarity"],
    "TKG": ["curator", "extraction"],
    "Hub": ["startup", "thundering"],
    "Prompts": ["showbox", "worker"],
    "Routing": ["generalag", "soulag"],
}

tmpdir = '/tmp/realistic_bench_v2.kuzu'
shutil.rmtree(tmpdir, ignore_errors=True)
db = KuzuDBBackend(tmpdir)

# Seed entities
topic_to_eid = {t: f"e_{t.lower()}" for t in TOPICS}
for topic, terms in TOPICS.items():
    db.upsert_entity(Entity(id=topic_to_eid[topic], name=topic, type="concept", importance=0.8))

# Generate 100 facts WITH MENTIONS
import random
random.seed(42)
all_facts = []
for i in range(100):
    topic = random.choice(list(TOPICS.keys()))
    related = random.choice(TOPICS[topic])
    other = random.choice(list(TOPICS.keys()))
    templates = [
        f"During the {topic} implementation we discovered that {related} had issues with {other}.",
        f"The {topic} subsystem uses {related} for {other} processing.",
        f"Performance issue: {topic} + {related} combination was 5x slower than expected.",
        f"Refactoring: replaced {related} in {topic} with better alternative.",
        f"Documentation: {topic} requires {related} setup for {other} to work.",
    ]
    text = random.choice(templates)
    fid = f"f_{i:03d}"
    all_facts.append((fid, text, topic))
    db.upsert_fact(Fact(id=fid, text=text, embedding=real_embed(text),
                        importance=random.uniform(0.3, 0.9),
                        valid_at=time.time() - random.randint(0, 30*86400)))
    # Add mention of the topic entity (and sometimes related too)
    db.add_mention(Mention(fact_id=fid, entity_id=topic_to_eid[topic], confidence=1.0))
    if random.random() > 0.5:
        db.add_mention(Mention(fact_id=fid, entity_id=topic_to_eid[other], confidence=0.7))

print(f"📊 DB seeded: 100 facts + mentions across 6 topics")

gold_queries = [
    ("KuzuDB backend performance", "KuzuDB"),
    ("FAISS index fallback issue", "FAISS"),
    ("TKG curator extraction", "TKG"),
    ("Hub startup thundering herd", "Hub"),
    ("Prompts showbox format", "Prompts"),
    ("Routing generalag default", "Routing"),
    ("KuzuDB cypher schema", "KuzuDB"),
    ("FAISS similarity cosine", "FAISS"),
    ("TKG bitemporal memory", "TKG"),
    ("Hub subprocess waisen", "Hub"),
    ("Prompts worker showbox", "Prompts"),
    ("Routing soulag delegation", "Routing"),
    ("KuzuDB vector hnsw", "KuzuDB"),
    ("FAISS tfidf fallback", "FAISS"),
    ("TKG entity relation", "TKG"),
    ("Hub registry lock", "Hub"),
    ("Prompts json format", "Prompts"),
    ("Routing general soul", "Routing"),
    ("KuzuDB embedded graph", "KuzuDB"),
    ("TKG curator extraction pipeline", "TKG"),
]

# Test 1: Vector-only
print("\n🔍 Test 1: Vector-only")
engine = RetrievalEngine(db, cache_size=0)
v_hits = 0; v_lats = []
for query, gold in gold_queries:
    emb = real_embed(query)
    t0 = time.time()
    r = db.search_facts_by_vector(emb, k=5)
    v_lats.append((time.time()-t0)*1000)
    if any(gold in f.text for f in r): v_hits += 1
print(f"  Precision@5: {v_hits/20:.0%} ({v_hits}/20) | Avg: {np.mean(v_lats):.1f}ms")

# Test 2: Hybrid WITH gold symbols
print("\n🔍 Test 2: Hybrid (with gold symbols)")
h_hits = 0; h_lats = []
for query, gold in gold_queries:
    t0 = time.time()
    r = engine.query(query, symbols=[gold.lower()], k=5)
    h_lats.append((time.time()-t0)*1000)
    if any(gold in sf.fact.text for sf in r.facts): h_hits += 1
print(f"  Precision@5: {h_hits/20:.0%} ({h_hits}/20) | Avg: {np.mean(h_lats):.1f}ms")

# Test 3: Hybrid WITHOUT symbols (honest)
print("\n🔍 Test 3: Hybrid honest (no symbols)")
hh_hits = 0; hh_lats = []
for query, gold in gold_queries:
    t0 = time.time()
    r = engine.query(query, symbols=None, k=5)
    hh_lats.append((time.time()-t0)*1000)
    if any(gold in sf.fact.text for sf in r.facts): hh_hits += 1
print(f"  Precision@5: {hh_hits/20:.0%} ({hh_hits}/20) | Avg: {np.mean(hh_lats):.1f}ms")

print("\n" + "="*60)
print(f"VECTOR:    {v_hits}/20 ({v_hits/20:.0%})  {np.mean(v_lats):.1f}ms")
print(f"HYBRID+:   {h_hits}/20 ({h_hits/20:.0%})  {np.mean(h_lats):.1f}ms")
print(f"HYBRID:    {hh_hits}/20 ({hh_hits/20:.0%})  {np.mean(hh_lats):.1f}ms")
print("="*60)
