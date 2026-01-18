from memory_manager import MemoryManager
import numpy as np
import os
import shutil

def test_lancedb():
    db_path = "/tmp/test_lancedb"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    memory = MemoryManager(db_path=db_path)
    
    # Create some dummy embeddings (dolphin-mistral uses 4096)
    emb1 = [0.1] * 4096
    emb2 = [0.9] * 4096
    
    memory.store_interaction("user", "Hello first", emb1)
    memory.store_interaction("user", "Hello second", emb2)
    
    # Search for something similar to emb2
    hits = memory.retrieve_context(emb2, top_k=1)
    print(f"Top hit for emb2: {hits[0][0]} (dist: {hits[0][1]})")
    
    assert hits[0][0] == "Hello second"
    print("LanceDB test passed!")

if __name__ == "__main__":
    test_lancedb()
