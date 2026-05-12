import chromadb

from backend.knowledge.schemas import KnowledgeSnippet


def retrieve(
    champion: str | None = None,
    lane_opponent: str | None = None,
    fed_enemy: str | None = None,
    collection: chromadb.Collection = None,
    top_k: int = 3,
    *,
    query: str | None = None,
    performance_collection: chromadb.Collection | None = None,
    n_results: int = 3,
) -> list[KnowledgeSnippet]:
    effective_n = n_results if n_results != 3 else top_k
    if query is None:
        query = _build_query(champion or "", lane_opponent, fed_enemy)
    results = collection.query(query_texts=[query], n_results=effective_n)
    snippets: list[KnowledgeSnippet] = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        snippets.append(KnowledgeSnippet(
            source=meta["source"],
            content=doc,
            relevance=meta.get("relevance", "medium"),
        ))
    if performance_collection is not None and champion is not None:
        try:
            perf_results = performance_collection.query(
                query_texts=[query],
                n_results=2,
                where={"champion": champion},
            )
            for doc, meta in zip(perf_results["documents"][0], perf_results["metadatas"][0]):
                snippets.append(KnowledgeSnippet(
                    source="personal_history",
                    content=doc,
                    relevance=meta.get("relevance", "medium"),
                ))
        except Exception:
            pass
    return snippets


def _build_query(champion: str, lane_opponent: str | None, fed_enemy: str | None) -> str:
    parts = [f"{champion} gameplan win condition early game"]
    if lane_opponent:
        parts.append(f"matchup against {lane_opponent} tips")
    if fed_enemy:
        parts.append(f"most fed enemy {fed_enemy} how to play against")
    return " ".join(parts)
