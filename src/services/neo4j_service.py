"""Neo4j Knowledge Graph Service for Drug Repurposing"""
from neo4j import GraphDatabase
from typing import List, Dict, Optional, Any
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class Neo4jService:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")
        
        if not self.password:
            logger.warning("⚠️ NEO4J_PASSWORD not set")
            self.driver = None
            return
        
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self.driver.verify_connectivity()
            logger.info(f"✅ Neo4j connected: {self.uri} (db: {self.database})")
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            self.driver = None
    
    def is_connected(self) -> bool:
        return self.driver is not None
    
    def close(self):
        if self.driver:
            self.driver.close()
    
    def ingest_search_results(self, disease_name: str, papers: List[Dict[str, Any]], 
                             drugs_mentioned: List[str] = None) -> Dict[str, int]:
        if not self.driver:
            return {"error": "Neo4j not connected"}
        
        stats = {"papers": 0, "drugs": 0, "relationships": 0, "errors": 0}
        
        try:
            with self.driver.session(database=self.database) as session:
                session.run("MERGE (d:Disease {name: $name})", name=disease_name)
                
                for paper in papers:
                    try:
                        paper_id = paper.get('id') or paper.get('url', '')
                        if not paper_id:
                            continue
                        
                        session.run("""
                            MERGE (p:Paper {paper_id: $id})
                            SET p.title = $title,
                                p.abstract = $abstract,
                                p.url = $url,
                                p.source = $source,
                                p.updated_at = datetime()
                        """, 
                        id=paper_id,
                        title=str(paper.get('title', ''))[:500],
                        abstract=str(paper.get('abstract', ''))[:2000],
                        url=str(paper.get('url', ''))[:500],
                        source=str(paper.get('source', ''))[:100])
                        
                        session.run("""
                            MATCH (p:Paper {paper_id: $id})
                            MATCH (d:Disease {name: $disease})
                            MERGE (p)-[r:ABOUT]->(d)
                        """, id=paper_id, disease=disease_name)
                        
                        stats['papers'] += 1
                        stats['relationships'] += 1
                    except Exception as e:
                        stats['errors'] += 1
                
                if drugs_mentioned:
                    for drug in drugs_mentioned:
                        try:
                            session.run("MERGE (d:Drug {name: $name})", name=drug)
                            session.run("""
                                MATCH (drug:Drug {name: $drug})
                                MATCH (disease:Disease {name: $disease})
                                MERGE (drug)-[r:POTENTIAL_TREATMENT]->(disease)
                            """, drug=drug, disease=disease_name)
                            stats['drugs'] += 1
                            stats['relationships'] += 1
                        except Exception as e:
                            stats['errors'] += 1
            
            logger.info(f"�� Neo4j ingestion: {stats['papers']} papers, {stats['drugs']} drugs")
        except Exception as e:
            logger.error(f"Neo4j ingestion error: {e}")
            stats['errors'] += 1
        
        return stats

_neo4j_service = None

def get_neo4j_service() -> Optional[Neo4jService]:
    global _neo4j_service
    if _neo4j_service is None:
        _neo4j_service = Neo4jService()
    return _neo4j_service if _neo4j_service and _neo4j_service.is_connected() else None
