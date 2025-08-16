# clear_cache.py
import chromadb
from trend_assistant import config

print("Attempting to clear the ChromaDB cache...")

try:
    client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
    print(
        f"Client initialized. Current collections: {[c.name for c in client.list_collections()]}"
    )

    client.delete_collection(name=config.CHROMA_COLLECTION_NAME)
    print(f"SUCCESS: Collection '{config.CHROMA_COLLECTION_NAME}' has been deleted.")

except Exception as e:
    print(f"An error occurred: {e}")
    print("This may be because the collection does not exist, which is okay.")

print("Cache clearing process finished.")
