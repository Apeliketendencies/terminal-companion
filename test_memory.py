from memory_manager import MemoryManager
import numpy as np
import os

def test_memory():
    db_path = "/tmp/test_memory.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    memory = MemoryManager(db_path=db_path)
    
    # Create some dummy embeddings
    emb1 = [0.1] * 4096 # Adjust size to match model if needed, but similarity works on any size
    emb2 = [0.9] * 4096
    
    memory.store_interaction("user", "Hello first", emb1)
    memory.store_interaction("user", "Hello second", emb2)
    
    # Search for something similar to emb2
    hits = memory.retrieve_context(emb2, top_k=1)
    print(f"Top hit for emb2: {hits[0][0]} (score: {hits[0][1]})")
    
    assert hits[0][0] == "Hello second"
    print("Memory test passed!")

if __name__ == "__main__":
    test_memory()
