import lancedb
import json
import numpy as np
import os
import pandas as pd

class MemoryManager:
    def __init__(self, db_path="~/.lancedb"):
        self.db_path = os.path.expanduser(db_path)
        self.db = lancedb.connect(self.db_path)
        self.table_name = "interactions"
        self._init_db()

    def _init_db(self):
        if self.table_name not in self.db.table_names():
            # Initial schema
            # We need at least one record to define the schema if not using a pydantic model
            # Let's use a dummy record with 4096 dimensions (default for many LLMs including dolphin-mistral)
            dummy_emb = [0.0] * 4096
            data = [{
                "vector": dummy_emb,
                "role": "system",
                "content": "Database initialized",
                "timestamp": 0.0
            }]
            self.db.create_table(self.table_name, data=data)
        self.table = self.db.open_table(self.table_name)

    def store_interaction(self, role, content, embedding, timestamp=None):
        import time
        if timestamp is None:
            timestamp = time.time()
        
        self.table.add([{
            "vector": embedding,
            "role": role,
            "content": content,
            "timestamp": timestamp
        }])

    def retrieve_context(self, query_embedding, top_k=5):
        # LanceDB returns sorted results by distance
        results = self.table.search(query_embedding).limit(top_k).to_list()
        
        # Convert distance to a similarity-like score if needed, 
        # but LanceDB's search is already sorted by closest match.
        # We can just return the content.
        return [(r["content"], r["_distance"]) for r in results]
