import chromadb

from backend.knowledge.schemas import KnowledgeSnippet


def retrieve(
    champion: str,
    lane_opponent: str | None,
    fed_enemy: str | None,
    collection: chromadb.Collection,
    top_k: int = 3,
) -> list[KnowledgeSnippet]:
    query = _build_query(champion, lane_opponent, fed_enemy)
    results = collection.query(query_texts=[query], n_results=top_k)
    snippets: list[KnowledgeSnippet] = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        snippets.append(KnowledgeSnippet(
            source=meta["source"],
            content=doc,
            relevance=meta.get("relevance", "medium"),
        ))
    return snippets


def _build_query(champion: str, lane_opponent: str | None, fed_enemy: str | None) -> str:
    parts = [f"{champion} gameplan win condition early game"]
    if lane_opponent:
        parts.append(f"matchup against {lane_opponent} tips")
    if fed_enemy:
        parts.append(f"most fed enemy {fed_enemy} how to play against")
    return " ".join(parts)
