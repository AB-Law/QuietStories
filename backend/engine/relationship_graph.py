"""
Relationship graph for tracking entity relationships with structured data.

This module provides an in-memory graph structure for tracking relationships
between entities, enabling the LLM to query and understand social dynamics
without parsing text memories.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RelationshipEdge:
    """Represents a relationship between two entities"""

    from_entity: str
    to_entity: str
    relationship_type: str
    sentiment: float  # -1.0 to 1.0 (negative to positive)
    strength: float = 1.0  # 0.0 to 1.0 (how strong the relationship is)
    last_updated: datetime = field(default_factory=datetime.now)
    evidence: List[str] = field(
        default_factory=list
    )  # Memory IDs that support this relationship
    metadata: Dict[str, Any] = field(default_factory=dict)


class RelationshipGraph:
    """
    In-memory graph for tracking entity relationships.

    Provides structured relationship data that can be queried by the LLM
    for better understanding of social dynamics and character interactions.
    """

    def __init__(self):
        """Initialize empty relationship graph"""
        self.nodes: Set[str] = set()
        self.edges: Dict[Tuple[str, str], RelationshipEdge] = {}
        self.reverse_edges: Dict[str, List[Tuple[str, str]]] = defaultdict(lambda: [])
        self.enrichment_queue: List[Dict[str, Any]] = []

    def add_relationship(
        self,
        from_entity: str,
        to_entity: str,
        relationship_type: str,
        sentiment: float,
        strength: float = 1.0,
        evidence: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Add or update a relationship between two entities.

        Args:
            from_entity: Entity initiating the relationship
            to_entity: Entity receiving the relationship
            relationship_type: Type of relationship (trust, fear, love, rivalry, etc.)
            sentiment: Sentiment score (-1.0 to 1.0)
            strength: Relationship strength (0.0 to 1.0)
            evidence: List of memory IDs supporting this relationship
            metadata: Additional relationship metadata

        Returns:
            True if relationship was added/updated, False otherwise
        """
        # Normalize entity names
        from_entity = from_entity.lower().strip()
        to_entity = to_entity.lower().strip()

        # Don't create self-relationships
        if from_entity == to_entity:
            return False

        # Create edge key (ensure consistent ordering)
        edge_key = (from_entity, to_entity)

        # Update existing relationship or create new one
        if edge_key in self.edges:
            edge = self.edges[edge_key]
            # Update existing edge
            edge.sentiment = (
                edge.sentiment + sentiment
            ) / 2  # Average with new sentiment
            edge.strength = max(edge.strength, strength)  # Take stronger relationship
            edge.last_updated = datetime.now()
            if evidence:
                edge.evidence.extend(evidence)
            if metadata:
                edge.metadata.update(metadata)
        else:
            # Create new edge
            edge = RelationshipEdge(
                from_entity=from_entity,
                to_entity=to_entity,
                relationship_type=relationship_type,
                sentiment=sentiment,
                strength=strength,
                evidence=evidence or [],
                metadata=metadata or {},
            )
            self.edges[edge_key] = edge

        # Update nodes
        self.nodes.add(from_entity)
        self.nodes.add(to_entity)

        # Update reverse lookup
        self.reverse_edges[to_entity].append(edge_key)

        logger.debug(
            f"Added relationship: {from_entity} -> {to_entity} "
            f"({relationship_type}, sentiment: {sentiment:.2f})"
        )
        return True

    def get_relationships(
        self,
        entity_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        min_strength: float = 0.0,
        limit: int = 10,
    ) -> List[RelationshipEdge]:
        """
        Query relationships from the graph.

        Args:
            entity_id: Filter by specific entity (returns relationships from/to this entity)
            relationship_type: Filter by relationship type
            min_strength: Minimum relationship strength to include
            limit: Maximum number of relationships to return

        Returns:
            List of matching RelationshipEdge objects
        """
        results = []

        for edge in self.edges.values():
            # Apply filters
            if entity_id:
                if (
                    edge.from_entity != entity_id.lower()
                    and edge.to_entity != entity_id.lower()
                ):
                    continue

            if relationship_type and edge.relationship_type != relationship_type:
                continue

            if edge.strength < min_strength:
                continue

            results.append(edge)

        # Sort by strength and recency
        results.sort(key=lambda e: (e.strength, e.last_updated), reverse=True)

        return results[:limit]

    def get_entity_relationships(
        self, entity_id: str
    ) -> Dict[str, List[RelationshipEdge]]:
        """
        Get all relationships for a specific entity.

        Args:
            entity_id: Entity to get relationships for

        Returns:
            Dict with 'outgoing' and 'incoming' relationship lists
        """
        entity_id = entity_id.lower()
        outgoing = []
        incoming = []

        # Find all edges involving this entity
        for (from_entity, to_entity), edge in self.edges.items():
            if from_entity == entity_id:
                outgoing.append(edge)
            elif to_entity == entity_id:
                incoming.append(edge)

        return {
            "outgoing": outgoing,
            "incoming": incoming,
        }

    def get_relationship_summary(self, entity_id: str) -> Dict[str, Any]:
        """
        Get a summary of relationships for an entity.

        Args:
            entity_id: Entity to summarize relationships for

        Returns:
            Dictionary with relationship statistics and summaries
        """
        relationships = self.get_entity_relationships(entity_id)

        summary: Dict[str, Any] = {
            "entity_id": entity_id,
            "total_outgoing": len(relationships["outgoing"]),
            "total_incoming": len(relationships["incoming"]),
            "relationship_types": {},
            "average_sentiment": 0.0,
            "strongest_relationships": [],
        }

        all_sentiments = []

        # Analyze outgoing relationships
        for edge in relationships["outgoing"]:
            rel_type = edge.relationship_type
            if rel_type not in summary["relationship_types"]:
                summary["relationship_types"][rel_type] = {
                    "count": 0,
                    "avg_sentiment": 0.0,
                }

            summary["relationship_types"][rel_type]["count"] += 1
            summary["relationship_types"][rel_type]["avg_sentiment"] += edge.sentiment
            all_sentiments.append(edge.sentiment)

            # Track strongest relationships
            if len(summary["strongest_relationships"]) < 5:
                summary["strongest_relationships"].append(
                    {
                        "entity": edge.to_entity,
                        "type": edge.relationship_type,
                        "sentiment": edge.sentiment,
                        "strength": edge.strength,
                    }
                )

        # Calculate averages
        if all_sentiments:
            summary["average_sentiment"] = sum(all_sentiments) / len(all_sentiments)

        for rel_type in summary["relationship_types"]:
            data = summary["relationship_types"][rel_type]
            if data["count"] > 0:
                data["avg_sentiment"] /= data["count"]

        return summary

    def get_graph_summary(self) -> Dict[str, Any]:
        """
        Get overall graph statistics.

        Returns:
            Dictionary with graph-wide statistics
        """
        return {
            "total_entities": len(self.nodes),
            "total_relationships": len(self.edges),
            "relationship_types": list(
                set(edge.relationship_type for edge in self.edges.values())
            ),
            "avg_relationship_strength": (
                sum(edge.strength for edge in self.edges.values()) / len(self.edges)
                if self.edges
                else 0.0
            ),
            "most_connected_entities": self._get_most_connected_entities(),
        }

    def _get_most_connected_entities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get entities with the most relationships"""
        connections: Dict[str, int] = defaultdict(int)

        for (from_entity, to_entity), edge in self.edges.items():
            connections[from_entity] += 1
            connections[to_entity] += 1

        sorted_entities = sorted(
            [
                {"entity_id": entity, "connection_count": count}
                for entity, count in connections.items()
            ],
            key=lambda x: x["connection_count"],  # type: ignore
            reverse=True,
        )

        return sorted_entities[:limit]

    def clear_entity_relationships(self, entity_id: str) -> int:
        """
        Remove all relationships involving a specific entity.

        Args:
            entity_id: Entity to remove relationships for

        Returns:
            Number of relationships removed
        """
        entity_id = entity_id.lower()
        to_remove = []

        for (from_entity, to_entity), edge in self.edges.items():
            if from_entity == entity_id or to_entity == entity_id:
                to_remove.append((from_entity, to_entity))

        for edge_key in to_remove:
            del self.edges[edge_key]

        # Update reverse edges
        if entity_id in self.reverse_edges:
            del self.reverse_edges[entity_id]

        # Remove from nodes if no relationships remain
        has_relationships = any(
            from_entity == entity_id or to_entity == entity_id
            for (from_entity, to_entity) in self.edges.keys()
        )

        if not has_relationships and entity_id in self.nodes:
            self.nodes.remove(entity_id)

        logger.debug(f"Removed {len(to_remove)} relationships for entity: {entity_id}")
        return len(to_remove)

    def serialize(self) -> Dict[str, Any]:
        """Serialize graph to dictionary for storage"""
        return {
            "nodes": list(self.nodes),
            "edges": [
                {
                    "from_entity": edge.from_entity,
                    "to_entity": edge.to_entity,
                    "relationship_type": edge.relationship_type,
                    "sentiment": edge.sentiment,
                    "strength": edge.strength,
                    "last_updated": edge.last_updated.isoformat(),
                    "evidence": edge.evidence,
                    "metadata": edge.metadata,
                }
                for edge in self.edges.values()
            ],
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        """Deserialize graph from dictionary"""
        self.nodes = set(data.get("nodes", []))
        self.edges = {}
        self.reverse_edges = defaultdict(list)

        for edge_data in data.get("edges", []):
            edge = RelationshipEdge(
                from_entity=edge_data["from_entity"],
                to_entity=edge_data["to_entity"],
                relationship_type=edge_data["relationship_type"],
                sentiment=edge_data["sentiment"],
                strength=edge_data.get("strength", 1.0),
                last_updated=datetime.fromisoformat(edge_data["last_updated"]),
                evidence=edge_data.get("evidence", []),
                metadata=edge_data.get("metadata", {}),
            )

            edge_key = (edge.from_entity, edge.to_entity)
            self.edges[edge_key] = edge
            self.reverse_edges[edge.to_entity].append(edge_key)

    def queue_enrichment_analysis(
        self, content: str, entity_id: str, related_entities: List[str]
    ) -> str:
        """
        Queue relationship enrichment analysis for ambiguous relationships.

        Args:
            content: Memory content to analyze
            entity_id: Entity that recorded this memory
            related_entities: List of entities mentioned in the content

        Returns:
            Analysis ID for tracking the queued task
        """
        analysis_id = f"analysis_{entity_id}_{len(self.enrichment_queue)}"

        # Create enrichment task
        task = {
            "id": analysis_id,
            "content": content,
            "entity_id": entity_id,
            "related_entities": related_entities,
            "status": "queued",
            "created_at": datetime.now(),
        }

        self.enrichment_queue.append(task)
        logger.debug(f"Queued relationship enrichment analysis: {analysis_id}")

        return analysis_id

    def get_enrichment_queue_status(self) -> List[Dict[str, Any]]:
        """Get status of all queued enrichment tasks"""
        return self.enrichment_queue.copy()

    def clear_completed_enrichments(self) -> int:
        """Remove completed enrichment tasks from queue"""
        initial_count = len(self.enrichment_queue)
        self.enrichment_queue = [
            task for task in self.enrichment_queue if task["status"] != "completed"
        ]
        return initial_count - len(self.enrichment_queue)

    async def process_enrichment_analysis(self, task_id: str, provider=None) -> bool:
        """
        Process a queued enrichment analysis using LLM.

        Args:
            task_id: ID of the task to process
            provider: Optional LLM provider instance

        Returns:
            True if analysis completed successfully, False otherwise
        """
        # Find the task
        task = None
        for t in self.enrichment_queue:
            if t["id"] == task_id:
                task = t
                break

        if not task or task["status"] != "queued":
            logger.warning(f"Task {task_id} not found or not queued")
            return False

        if not provider:
            logger.warning("No provider available for enrichment analysis")
            task["status"] = "failed"
            return False

        try:
            task["status"] = "processing"

            # Create analysis prompt
            analysis_prompt = f"""Analyze this relationship memory for detailed sentiment and type:

MEMORY CONTENT: "{task['content']}"

ENTITIES INVOLVED: {task['entity_id']} and {', '.join(task['related_entities'])}

Provide detailed analysis in this exact JSON format:
{{
  "sentiment": <float between -1.0 and 1.0, where -1.0 is very negative, 0.0 is neutral, 1.0 is very positive>,
  "relationship_type": "<one of: family, friendship, romantic, adversarial, mentor, professional, acquaintance>",
  "confidence": <float between 0.0 and 1.0 indicating how confident you are in this analysis>,
  "reasoning": "<brief explanation of your analysis>",
  "specific_relationships": [
    {{
      "from_entity": "{task['entity_id']}",
      "to_entity": "<specific entity name>",
      "type": "<specific type>",
      "sentiment": <sentiment value>
    }}
  ]
}}

Respond with ONLY the JSON object:"""

            from langchain.schema import HumanMessage, SystemMessage

            response = await provider.chat(
                [
                    SystemMessage(
                        content="You are an expert at analyzing human relationships and emotions. Provide precise numerical sentiment scores and accurate relationship classifications."
                    ),
                    HumanMessage(content=analysis_prompt),
                ]
            )

            # Extract JSON from response
            response_content = (
                response.content if hasattr(response, "content") else str(response)
            )

            import json

            def _extract_json_object(s):
                """Extract the first JSON object from a string using JSONDecoder."""
                decoder = json.JSONDecoder()
                s = s.lstrip()
                try:
                    obj, idx = decoder.raw_decode(s)
                    return obj
                except Exception:
                    return None

            # Look for JSON object in response
            analysis = _extract_json_object(response_content)
            if analysis:
                # Validate required fields
                if all(
                    key in analysis
                    for key in ["sentiment", "relationship_type", "confidence"]
                ):
                    # Update the relationship in the graph
                    for rel in analysis.get("specific_relationships", []):
                        self.add_relationship(
                            from_entity=rel["from_entity"],
                            to_entity=rel["to_entity"],
                            relationship_type=rel["type"],
                            sentiment=rel["sentiment"],
                            strength=analysis["confidence"],
                            evidence=[task_id],
                        )

                    task["status"] = "completed"
                    task["result"] = analysis
                    logger.info(f"Enrichment analysis completed for task {task_id}")
                    return True

            # If JSON parsing fails, mark as failed
            logger.warning(
                f"Failed to parse enrichment analysis response: {response_content[:100]}"
            )
            task["status"] = "failed"

        except Exception as e:
            logger.error(f"Enrichment analysis failed for task {task_id}: {e}")
            task["status"] = "failed"

        return False


def extract_relationship_from_content(
    content: str,
    entity_id: str,
    all_entities: List[str],
) -> Optional[Dict[str, Any]]:
    """
    Extract relationship information from memory content using pattern matching.

    Args:
        content: Memory content to analyze
        entity_id: Entity that recorded this memory
        all_entities: List of all known entity IDs

    Returns:
        Dictionary with extracted relationship info or None if no relationship found
    """
    content_lower = content.lower()
    entity_id_lower = entity_id.lower()

    # Find other entities mentioned in the content
    mentioned_entities = []
    for entity in all_entities:
        entity_lower = entity.lower()
        if entity_lower != entity_id_lower and entity_lower in content_lower:
            mentioned_entities.append(entity)

    if not mentioned_entities:
        return None

    # Analyze sentiment and relationship type
    sentiment_score = 0.0
    relationship_type = "acquaintance"  # default

    # Positive sentiment indicators
    positive_words = [
        "trust",
        "love",
        "friend",
        "ally",
        "respect",
        "care",
        "protect",
        "help",
        "support",
        "loyal",
    ]
    negative_words = [
        "hate",
        "fear",
        "enemy",
        "rival",
        "betray",
        "anger",
        "distrust",
        "conflict",
        "tension",
    ]

    positive_count = sum(1 for word in positive_words if word in content_lower)
    negative_count = sum(1 for word in negative_words if word in content_lower)

    sentiment_score = (positive_count - negative_count) / max(
        positive_count + negative_count, 1
    )

    # Determine relationship type based on keywords
    if any(
        word in content_lower
        for word in ["family", "sibling", "parent", "child", "blood"]
    ):
        relationship_type = "family"
    elif any(
        word in content_lower for word in ["friend", "companion", "ally", "trust"]
    ):
        relationship_type = "friendship"
    elif any(
        word in content_lower for word in ["romantic", "love", "partner", "spouse"]
    ):
        relationship_type = "romantic"
    elif any(
        word in content_lower
        for word in ["fear", "enemy", "rival", "opponent", "foe", "betray"]
    ):
        relationship_type = "adversarial"
    elif any(
        word in content_lower for word in ["mentor", "teacher", "student", "guide"]
    ):
        relationship_type = "mentor"
    elif any(
        word in content_lower for word in ["boss", "employee", "subordinate", "leader"]
    ):
        relationship_type = "professional"

    return {
        "from_entity": entity_id,
        "to_entity": mentioned_entities[0],  # Use first mentioned entity
        "relationship_type": relationship_type,
        "sentiment": sentiment_score,
        "strength": abs(sentiment_score),  # Strength based on sentiment magnitude
    }
