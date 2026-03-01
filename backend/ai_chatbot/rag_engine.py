import os

KB_PATH = os.path.join(os.path.dirname(__file__), "kb")

def retrieve_context(query: str) -> str:
    query_words = query.lower().split()
    matches = []

    for file in os.listdir(KB_PATH):
        if file.endswith(".txt"):
            with open(os.path.join(KB_PATH, file), "r", encoding="utf-8") as f:
                content = f.read()
                if any(word in content.lower() for word in query_words):
                    matches.append(content)

    return "\n".join(matches[:2]) if matches else "General health guidance."
