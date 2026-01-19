import lancedb
import json
import numpy as np
import os
import pandas as pd

class MemoryManager:
    def __init__(self, db_path="~/.lancedb", dimension=None):
        self.db_path = os.path.expanduser(db_path)
        self.db = lancedb.connect(self.db_path)
        self.dimension = dimension
        self.table_name = f"interactions_{dimension}" if dimension else "interactions"
        if dimension:
            self._init_db()
        else:
            self.table = None

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
        if self.table is None or self.dimension != embedding_len:
            self.dimension = embedding_len
            self.table_name = f"interactions_{self.dimension}"
            self._init_db()

    def store_interaction(self, role, content, embedding, timestamp=None):
        import time
        self._ensure_initialized(len(embedding))
        
        if timestamp is None:
            timestamp = time.time()
        
        self.table.add([{
            "vector": embedding,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }])

    def retrieve_context(self, query_embedding, top_k=5):
        self._ensure_initialized(len(query_embedding))
        # Use cosine metric for scale-invariant similarity
        results = self.table.search(query_embedding).metric("cosine").limit(top_k).to_list()
        
        return [(r["content"], r["_distance"]) for r in results]
