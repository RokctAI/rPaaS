# API Reference: ai_search

Source file: `paas/whatsapp/api/ai_search.py`

## Documented Module Functions

### `def get_brain_embedding(text)`
Wrapper to safely call Brain's embedding service.
Returns None if Brain is not installed.

### `def semantic_search(query, shop_id, top_k=3)`
Performs semantic search for the query within the shop's products using pgvector.
Using Centralized Brain Service for embeddings.
bypass_sql

### `def cosine_similarity(v1, v2)`
Manual Cosine Similarity implementation.
v1, v2: List[float]

### `def load_intents_from_config()`
Loads intents from rokct/ai_config/customer_intents.json

### `def classify_intent(text)`
Classifies text into one of the INTENT_PROTOTYPES keys.
Returns (intent, score).

### `def extract_entity(text, intent)`
Extracts the 'entity' (keywords) from the text by removing common action words/stopwords.
Simple heuristic since we don't have a NER model.

### `def search_global_shops(query)`
Searches for Shops matching the query (Name or Category or Description).
