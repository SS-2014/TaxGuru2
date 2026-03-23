"""
TaxGuru — Vector Database Layer
Uses ChromaDB for:
1. Semantic search over tax law sections (RAG retrieval)
2. User profile similarity (find similar taxpayers for recommendations)
"""

import json
import hashlib
from typing import Optional

# ChromaDB may not be available in all environments
# Falls back to keyword search if not installed
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


class TaxVectorDB:
    """Vector database for tax law semantic search and user similarity"""

    def __init__(self, persist_dir: str = "./taxguru_vectordb"):
        self.persist_dir = persist_dir
        self.client = None
        self.tax_law_collection = None
        self.user_profiles_collection = None

        if CHROMA_AVAILABLE:
            self._init_chromadb()

    def _init_chromadb(self):
        """Initialize ChromaDB with persistent storage"""
        try:
            self.client = chromadb.Client()  # In-memory for Streamlit Cloud
            # Use default embedding function (all-MiniLM-L6-v2)
            self.ef = embedding_functions.DefaultEmbeddingFunction()

            # Create tax law collection
            self.tax_law_collection = self.client.get_or_create_collection(
                name="tax_law_sections",
                embedding_function=self.ef,
                metadata={"description": "Indian Income Tax Act sections and provisions"}
            )

            # Create user profiles collection
            self.user_profiles_collection = self.client.get_or_create_collection(
                name="user_profiles",
                embedding_function=self.ef,
                metadata={"description": "Anonymous taxpayer profiles for similarity matching"}
            )
        except Exception as e:
            print(f"ChromaDB initialization failed: {e}. Falling back to keyword search.")
            self.client = None

    def index_knowledge_base(self, knowledge_base: list):
        """Index the tax knowledge base into vector DB"""
        if not self.tax_law_collection:
            return False

        # Check if already indexed
        if self.tax_law_collection.count() > 0:
            return True  # Already indexed

        documents = []
        metadatas = []
        ids = []

        for entry in knowledge_base:
            # Create a rich document combining title and content
            doc_text = f"{entry['title']}\n\nSection: {entry['section']}\n\n{entry['content']}"
            documents.append(doc_text)
            metadatas.append({
                "section": entry["section"],
                "category": entry["category"],
                "applies_to": ",".join(entry["applies_to"]),
                "title": entry["title"],
                "last_updated": entry["last_updated"],
                "source": entry["source"],
            })
            ids.append(entry["id"])

        try:
            self.tax_law_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            return True
        except Exception as e:
            print(f"Indexing failed: {e}")
            return False

    def search_tax_law(self, query: str, n_results: int = 5,
                       taxpayer_type: str = None, category: str = None) -> list:
        """Semantic search over tax law provisions"""
        if not self.tax_law_collection:
            # Fallback to keyword search
            return self._keyword_search(query, taxpayer_type, category)

        where_filters = {}
        if taxpayer_type:
            where_filters["applies_to"] = {"$contains": taxpayer_type}
        if category:
            where_filters["category"] = category

        try:
            results = self.tax_law_collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filters if where_filters else None,
            )

            formatted = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    formatted.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'id': results['ids'][0][i] if results['ids'] else '',
                    })
            return formatted
        except Exception as e:
            print(f"Vector search failed: {e}")
            return self._keyword_search(query, taxpayer_type, category)

    def _keyword_search(self, query: str, taxpayer_type: str = None,
                        category: str = None) -> list:
        """Fallback keyword search when ChromaDB is not available"""
        from knowledge_base import TAX_KNOWLEDGE_BASE
        query_lower = query.lower()
        results = []

        for entry in TAX_KNOWLEDGE_BASE:
            if taxpayer_type and taxpayer_type not in entry['applies_to'] and 'all' not in entry['applies_to']:
                continue
            if category and entry['category'] != category:
                continue

            # Simple relevance scoring
            score = 0
            words = query_lower.split()
            for word in words:
                if word in entry['title'].lower():
                    score += 3
                if word in entry['content'].lower():
                    score += 1
                if word in entry['section'].lower():
                    score += 5

            if score > 0:
                results.append({
                    'content': f"{entry['title']}\n\nSection: {entry['section']}\n\n{entry['content']}",
                    'metadata': {
                        'section': entry['section'],
                        'category': entry['category'],
                        'title': entry['title'],
                        'source': entry['source'],
                    },
                    'distance': 1.0 / (score + 1),  # Lower is better
                    'id': entry['id'],
                })

        results.sort(key=lambda x: x['distance'])
        return results[:5]

    def add_user_profile(self, profile: dict, tax_result: dict) -> str:
        """Add an anonymous user profile for similarity matching"""
        # Generate anonymous ID
        profile_hash = hashlib.sha256(
            json.dumps(profile, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]

        # Create a text representation of the profile (no PII)
        profile_text = f"""Taxpayer type: {profile.get('taxpayer_type', 'unknown')}
Age bracket: {'senior' if profile.get('age', 30) >= 60 else 'working_age'}
Income bracket: {self._income_bracket(profile.get('gross_salary', 0) + profile.get('business_income', 0))}
Has HRA: {'yes' if profile.get('hra_received', 0) > 0 else 'no'}
Has home loan: {'yes' if profile.get('section_24b', 0) > 0 else 'no'}
Has ESOPs: {'yes' if profile.get('esop_perquisite', 0) > 0 else 'no'}
Trades F&O: {'yes' if profile.get('trading_income', 0) != 0 else 'no'}
Has capital gains: {'yes' if (profile.get('stcg_equity', 0) + profile.get('ltcg_equity', 0)) > 0 else 'no'}
Regime chosen: {tax_result.get('recommended', 'new')}
Effective tax rate: {tax_result.get('effective_rate', 0)}%"""

        if self.user_profiles_collection:
            try:
                self.user_profiles_collection.add(
                    documents=[profile_text],
                    metadatas=[{
                        'taxpayer_type': profile.get('taxpayer_type', 'unknown'),
                        'income_bracket': self._income_bracket(
                            profile.get('gross_salary', 0) + profile.get('business_income', 0)),
                        'regime': tax_result.get('recommended', 'new'),
                    }],
                    ids=[profile_hash],
                )
            except Exception:
                pass  # Silently handle duplicates

        return profile_hash

    def find_similar_users(self, profile: dict, n_results: int = 5) -> list:
        """Find similar taxpayer profiles for recommendations"""
        if not self.user_profiles_collection or self.user_profiles_collection.count() == 0:
            return []

        query_text = f"""Taxpayer type: {profile.get('taxpayer_type', 'unknown')}
Income bracket: {self._income_bracket(profile.get('gross_salary', 0) + profile.get('business_income', 0))}
Has ESOPs: {'yes' if profile.get('esop_perquisite', 0) > 0 else 'no'}
Trades F&O: {'yes' if profile.get('trading_income', 0) != 0 else 'no'}"""

        try:
            results = self.user_profiles_collection.query(
                query_texts=[query_text],
                n_results=n_results,
            )
            return results.get('documents', [[]])[0]
        except Exception:
            return []

    def _income_bracket(self, total_income: float) -> str:
        """Categorize income into bracket for similarity matching"""
        if total_income <= 500000:
            return "up_to_5L"
        elif total_income <= 1000000:
            return "5L_to_10L"
        elif total_income <= 1500000:
            return "10L_to_15L"
        elif total_income <= 2000000:
            return "15L_to_20L"
        elif total_income <= 3000000:
            return "20L_to_30L"
        elif total_income <= 5000000:
            return "30L_to_50L"
        else:
            return "above_50L"

    def get_stats(self) -> dict:
        """Get vector DB statistics"""
        stats = {'chroma_available': CHROMA_AVAILABLE}
        if self.tax_law_collection:
            stats['tax_law_entries'] = self.tax_law_collection.count()
        if self.user_profiles_collection:
            stats['user_profiles'] = self.user_profiles_collection.count()
        return stats
