import frappe
import os
import json
import math

# Global cache for intent embeddings (In-Memory)
_INTENT_EMBEDDINGS = None


def get_brain_embedding(text):
    """
    Wrapper to safely call Brain's embedding service.
    Returns None if Brain is not installed.
    """
    if "brain" not in frappe.get_installed_apps():
        return None

    try:
        from brain.services.llm_service import embed_text

        return embed_text(text)
    except ImportError:
        return None
    except Exception as e:
        print(f"⚠️ Brain Service Error: {e}")
        return None


def semantic_search(query, shop_id, top_k=3):
    """
    Performs semantic search for the query within the shop's products using pgvector.
    Using Centralized Brain Service for embeddings.
    """
    # 1. Get embedding for query
    query_vector = get_brain_embedding(query)
    if not query_vector:
        return []

    # 2. SQL Search with Vector Distance
    try:
        # We use <=> operator for Cosine Distance (lower is better).
        # Note: pgvector expects the vector as a string representation in SQL unless passed as list param
        # frappe.db.sql with %s handles lists for some drivers, but explicit
        # string var is safer for vector type

        # Determine if we need to format the vector as string
        vector_str = str(query_vector)

        results = frappe.db.sql(
            """
            SELECT
                name, uuid, item_name as title, description,
                (embedding <=> %s) as distance
            FROM "tabItem"
            WHERE
                shop = %s
                AND disabled = 0
                AND embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT %s
        """,
            (vector_str, shop_id, top_k),
            as_dict=True,
        )

        final_results = []
        for r in results:
            # Convert distance to similarity score
            # Cosine Distance = 1 - Cosine Similarity
            similarity = 1 - float(r["distance"])

            if similarity < 0.3:  # Threshold
                continue

            final_results.append(
                {
                    "name": r["name"],
                    "uuid": r["uuid"],
                    "title": r["title"],
                    "score": similarity,
                }
            )

        return final_results

    except Exception as e:
        frappe.log_error(f"PaaS Vector Search Failed: {e}")
        return []


# --- NLP & Intent Logic ---


def cosine_similarity(v1, v2):
    """
    Manual Cosine Similarity implementation.
    v1, v2: List[float]
    """
    if not v1 or not v2:
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))

    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0

    return dot_product / (norm_v1 * norm_v2)


def load_intents_from_config():
    """
    Loads intents from rokct/ai_config/customer_intents.json
    """
    try:
        # Robust way: Get path relative to the 'brain' app module (where config
        # lives)
        path = frappe.get_app_path(
            "brain", "ai_config", "customer_intents.json"
        )
    except Exception:
        return get_fallback_intents()

    if not os.path.exists(path):
        return get_fallback_intents()

    try:
        with open(path, "r") as f:
            data = json.load(f)
            anchors = data.get("anchors", {})

            # Convert "key": "word1 word2" -> "key": ["word1", "word2"]
            prototypes = {}
            for key, val in anchors.items():
                prototypes[key] = val.split(" ")

            return prototypes
    except Exception as e:
        print(f"❌ Failed to parse intent config: {e}")
        return get_fallback_intents()


def get_fallback_intents():
    return {
        "action_buy": ["buy", "order", "purchase", "get", "add"],
        "action_find": ["find", "search", "show", "list", "view"],
        "action_track": ["track", "where", "status"],
        "misc_greeting": ["hi", "hello", "menu"],
    }


def get_intent_embeddings():
    global _INTENT_EMBEDDINGS
    if _INTENT_EMBEDDINGS:
        return _INTENT_EMBEDDINGS

    prototypes = load_intents_from_config()

    _INTENT_EMBEDDINGS = {}
    print("🧠 Indexing Intent Prototypes via Brain Service...")

    for intent, sentences in prototypes.items():
        try:
            # Batch embedding via Brain Service
            vectors = get_brain_embedding(sentences)
            if vectors and isinstance(vectors, list):
                _INTENT_EMBEDDINGS[intent] = vectors
            else:
                # Fallback empty
                _INTENT_EMBEDDINGS[intent] = []
        except Exception as e:
            print(f"⚠️ Failed to embed intent '{intent}': {e}")
            _INTENT_EMBEDDINGS[intent] = []

    return _INTENT_EMBEDDINGS


def classify_intent(text):
    """
    Classifies text into one of the INTENT_PROTOTYPES keys.
    Returns (intent, score).
    """
    intent_map = get_intent_embeddings()
    if not intent_map:
        return "unknown", 0.0

    # Embed query
    query_emb = get_brain_embedding(text)
    if not query_emb:
        return "unknown", 0.0

    best_intent = "unknown"
    best_score = 0.0

    for intent, prototypes in intent_map.items():
        # Compute similarity with all prototypes for this intent
        # prototypes is a List[List[float]]
        max_score = 0.0

        for p_vec in prototypes:
            score = cosine_similarity(query_emb, p_vec)
            if score > max_score:
                max_score = score

        if max_score > best_score:
            best_score = max_score
            best_intent = intent

    return best_intent, best_score


def extract_entity(text, intent):
    """
    Extracts the 'entity' (keywords) from the text by removing common action words/stopwords.
    Simple heuristic since we don't have a NER model.
    """
    # Common stopwords/action words to strip
    STOP_PHRASES = [
        "i want to",
        "i want",
        "can i get",
        "give me",
        "buy",
        "purchase",
        "order",
        "find",
        "search for",
        "show me",
        "looking for",
        "get",
        "add to cart",
        "please",
        "some",
        "a",
        "an",
        "the",
    ]

    clean_text = text.lower().strip()

    # Simple iterative strip (not perfect but fast)
    # Sort phrases by length desc to remove longest first ("i want to" before
    # "i want")
    sorted_stops = sorted(STOP_PHRASES, key=len, reverse=True)

    for phrase in sorted_stops:
        if clean_text.startswith(phrase + " "):
            clean_text = clean_text[len(phrase) + 1:]
        elif clean_text.startswith(phrase):
            clean_text = clean_text[len(phrase):]

    return clean_text.strip()


def search_global_shops(query):
    """
    Searches for Shops matching the query (Name or Category or Description).
    """
    # 1. SQL Search (Simple/Fuzzy)
    t_shop = frappe.qb.DocType("Shop")
    t_shop_category = frappe.qb.DocType("Shop Category")

    # Subquery for category matching
    subquery = (
        frappe.qb.from_(t_shop_category)
        .select(t_shop_category.parent)
        .where(t_shop_category.name.like(f"%{query}%"))
    )

    shops = (
        frappe.qb.from_(t_shop)
        .select(
            t_shop.name,
            t_shop.uuid,
            t_shop.description,
            t_shop.logo_img,
            t_shop.back_img,
        )
        .where(t_shop.status == "Approved")
        .where((t_shop.shop_type != "Ecommerce") & (t_shop.is_ecommerce == 0))
        .where(
            (t_shop.name.like(f"%{query}%"))
            | (t_shop.description.like(f"%{query}%"))
            | (t_shop.uuid.isin(subquery))
        )
        .limit(5)
    ).run(as_dict=True)

    return shops
