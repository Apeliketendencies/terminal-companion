import lancedb
import json
import numpy as np
import os
import pandas as pd

class MemoryManager:
    def __init__(self, db_path="~/.lancedb", model_name="default", dimension=None):
        self.db_path = os.path.expanduser(db_path)
        self.db = lancedb.connect(self.db_path)
        self.model_name = self._sanitize_model_name(model_name)
        self.dimension = dimension
        self.table_name = f"interactions_{self.model_name}_{dimension}" if dimension else None
        if dimension:
            self._init_db()
        else:
            self.table = None

    def _sanitize_model_name(self, name):
        # Replace characters that might be invalid in table names
        return name.replace(":", "_").replace("/", "_").replace("-", "_").replace(".", "_")

    def _init_db(self):
        if not self.dimension:
            return

        if self.table_name not in self.db.table_names():
            # Initial schema based on detected dimension
            dummy_emb = [0.0] * self.dimension
            data = [{
                "vector": dummy_emb,
                "role": "system",
                "content": "Database initialized",
                "timestamp": 0.0
            }]
            self.db.create_table(self.table_name, data=data)
        self.table = self.db.open_table(self.table_name)

    def _ensure_initialized(self, embedding_len):
        if embedding_len == 0:
            return
        if self.table is None or self.dimension != embedding_len:
            self.dimension = embedding_len
            self.table_name = f"interactions_{self.model_name}_{self.dimension}"
            self._init_db()

    def store_interaction(self, role, content, embedding, timestamp=None):
        import time
        if not embedding or len(embedding) == 0:
            return
            
        self._ensure_initialized(len(embedding))
        if self.table is None:
            return
            
        if timestamp is None:
            timestamp = time.time()
        
        self.table.add([{
            "vector": embedding,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }])

    def retrieve_context(self, query_embedding, top_k=5):
        if query_embedding is None or len(query_embedding) == 0:
            return []
        self._ensure_initialized(len(query_embedding))
        # Use cosine metric for scale-invariant similarity
        results = self.table.search(query_embedding).metric("cosine").limit(top_k).to_list()
        
        return [(r["content"], r["_distance"]) for r in results]
