#!/usr/bin/env python3
"""
Persistent Infrastructure for OMOP-UMLS Crosswalk
Sets up Neo4j, persistent caching, and LLM-enhanced validation
Designed for one-time processing with long-term reuse
"""

import os
import sys
import json
import pickle
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
import threading
import time

# Neo4j imports
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("Warning: Neo4j driver not available. Install with: pip install neo4j")

# OpenAI imports for LLM enhancement
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available. Install with: pip install openai")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('persistent_infrastructure.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class InfrastructureConfig:
    """Configuration for persistent infrastructure"""
    # Database settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    sqlite_path: str = "omop_umls_cache.db"
    
    # Caching settings
    enable_semantic_cache: bool = True
    enable_mapping_cache: bool = True
    enable_graph_cache: bool = True
    cache_compression: bool = True
    
    # LLM enhancement settings
    enable_llm_validation: bool = True
    llm_batch_size: int = 10
    llm_confidence_threshold: float = 0.5
    llm_model: str = "gpt-3.5-turbo"
    
    # Processing settings
    incremental_updates: bool = True
    version_tracking: bool = True
    backup_enabled: bool = True

class PersistentCacheManager:
    """
    Manages persistent caching for expensive computations
    Avoids recalculation of semantic similarities, embeddings, etc.
    """
    
    def __init__(self, config: InfrastructureConfig):
        self.config = config
        self.cache_dir = Path("persistent_cache")
        self.cache_dir.mkdir(exist_ok=True)
        
        # Initialize SQLite for structured caching
        self.init_sqlite_cache()
        
        # Cache statistics
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0,
            'total_size_mb': 0
        }
        
        logger.info(f"Initialized persistent cache manager: {self.cache_dir}")
    
    def init_sqlite_cache(self):
        """Initialize SQLite database for structured caching"""
        self.db_path = self.cache_dir / self.config.sqlite_path
        self.db_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db_lock = threading.Lock()
        
        # Create cache tables
        with self.db_lock:
            self.db_conn.executescript("""
                CREATE TABLE IF NOT EXISTS semantic_similarities (
                    concept1_hash TEXT,
                    concept2_hash TEXT,
                    similarity_score REAL,
                    computation_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (concept1_hash, concept2_hash)
                );
                
                CREATE TABLE IF NOT EXISTS concept_embeddings (
                    concept_hash TEXT PRIMARY KEY,
                    embedding_vector BLOB,
                    embedding_method TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS mapping_results (
                    omop_concept_id INTEGER,
                    umls_cui TEXT,
                    confidence_score REAL,
                    mapping_type TEXT,
                    evidence TEXT,
                    llm_validated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (omop_concept_id, umls_cui)
                );
                
                CREATE TABLE IF NOT EXISTS processing_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_similarities_score ON semantic_similarities(similarity_score);
                CREATE INDEX IF NOT EXISTS idx_mappings_confidence ON mapping_results(confidence_score);
                CREATE INDEX IF NOT EXISTS idx_mappings_type ON mapping_results(mapping_type);
            """)
        
        logger.info(f"SQLite cache initialized: {self.db_path}")
    
    def get_concept_hash(self, concept_text: str) -> str:
        """Generate hash for concept text"""
        return hashlib.md5(concept_text.encode()).hexdigest()
    
    def cache_semantic_similarity(self, concept1: str, concept2: str, 
                                similarity: float, method: str = "tfidf"):
        """Cache semantic similarity calculation"""
        hash1 = self.get_concept_hash(concept1)
        hash2 = self.get_concept_hash(concept2)
        
        # Ensure consistent ordering
        if hash1 > hash2:
            hash1, hash2 = hash2, hash1
        
        with self.db_lock:
            try:
                self.db_conn.execute(
                    "INSERT OR REPLACE INTO semantic_similarities VALUES (?, ?, ?, ?, ?)",
                    (hash1, hash2, similarity, method, datetime.now())
                )
                self.db_conn.commit()
                self.cache_stats['saves'] += 1
            except Exception as e:
                logger.error(f"Error caching similarity: {e}")
    
    def get_semantic_similarity(self, concept1: str, concept2: str) -> Optional[float]:
        """Retrieve cached semantic similarity"""
        hash1 = self.get_concept_hash(concept1)
        hash2 = self.get_concept_hash(concept2)
        
        # Ensure consistent ordering
        if hash1 > hash2:
            hash1, hash2 = hash2, hash1
        
        with self.db_lock:
            try:
                cursor = self.db_conn.execute(
                    "SELECT similarity_score FROM semantic_similarities WHERE concept1_hash = ? AND concept2_hash = ?",
                    (hash1, hash2)
                )
                result = cursor.fetchone()
                
                if result:
                    self.cache_stats['hits'] += 1
                    return result[0]
                else:
                    self.cache_stats['misses'] += 1
                    return None
            except Exception as e:
                logger.error(f"Error retrieving similarity: {e}")
                return None
    
    def cache_concept_embedding(self, concept_text: str, embedding: np.ndarray, method: str = "tfidf"):
        """Cache concept embedding"""
        concept_hash = self.get_concept_hash(concept_text)
        embedding_blob = pickle.dumps(embedding)
        
        with self.db_lock:
            try:
                self.db_conn.execute(
                    "INSERT OR REPLACE INTO concept_embeddings VALUES (?, ?, ?, ?)",
                    (concept_hash, embedding_blob, method, datetime.now())
                )
                self.db_conn.commit()
                self.cache_stats['saves'] += 1
            except Exception as e:
                logger.error(f"Error caching embedding: {e}")
    
    def get_concept_embedding(self, concept_text: str) -> Optional[np.ndarray]:
        """Retrieve cached concept embedding"""
        concept_hash = self.get_concept_hash(concept_text)
        
        with self.db_lock:
            try:
                cursor = self.db_conn.execute(
                    "SELECT embedding_vector FROM concept_embeddings WHERE concept_hash = ?",
                    (concept_hash,)
                )
                result = cursor.fetchone()
                
                if result:
                    self.cache_stats['hits'] += 1
                    return pickle.loads(result[0])
                else:
                    self.cache_stats['misses'] += 1
                    return None
            except Exception as e:
                logger.error(f"Error retrieving embedding: {e}")
                return None
    
    def cache_mapping_result(self, omop_concept_id: int, umls_cui: str, 
                           confidence_score: float, mapping_type: str, 
                           evidence: Dict, llm_validated: bool = False):
        """Cache mapping result"""
        evidence_json = json.dumps(evidence)
        
        with self.db_lock:
            try:
                self.db_conn.execute(
                    "INSERT OR REPLACE INTO mapping_results VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (omop_concept_id, umls_cui, confidence_score, mapping_type, 
                     evidence_json, llm_validated, datetime.now())
                )
                self.db_conn.commit()
                self.cache_stats['saves'] += 1
            except Exception as e:
                logger.error(f"Error caching mapping: {e}")
    
    def get_cached_mappings(self, omop_concept_ids: List[int] = None) -> pd.DataFrame:
        """Retrieve cached mapping results"""
        query = "SELECT * FROM mapping_results"
        params = []
        
        if omop_concept_ids:
            placeholders = ','.join(['?' for _ in omop_concept_ids])
            query += f" WHERE omop_concept_id IN ({placeholders})"
            params = omop_concept_ids
        
        with self.db_lock:
            try:
                return pd.read_sql_query(query, self.db_conn, params=params)
            except Exception as e:
                logger.error(f"Error retrieving mappings: {e}")
                return pd.DataFrame()
    
    def set_processing_metadata(self, key: str, value: Any):
        """Set processing metadata"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        
        with self.db_lock:
            try:
                self.db_conn.execute(
                    "INSERT OR REPLACE INTO processing_metadata VALUES (?, ?, ?)",
                    (key, value_str, datetime.now())
                )
                self.db_conn.commit()
            except Exception as e:
                logger.error(f"Error setting metadata: {e}")
    
    def get_processing_metadata(self, key: str) -> Optional[Any]:
        """Get processing metadata"""
        with self.db_lock:
            try:
                cursor = self.db_conn.execute(
                    "SELECT value FROM processing_metadata WHERE key = ?",
                    (key,)
                )
                result = cursor.fetchone()
                
                if result:
                    try:
                        return json.loads(result[0])
                    except:
                        return result[0]
                return None
            except Exception as e:
                logger.error(f"Error getting metadata: {e}")
                return None
    
    def get_cache_statistics(self) -> Dict:
        """Get cache performance statistics"""
        total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
        hit_rate = self.cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        # Get database statistics
        with self.db_lock:
            try:
                similarities_count = self.db_conn.execute("SELECT COUNT(*) FROM semantic_similarities").fetchone()[0]
                embeddings_count = self.db_conn.execute("SELECT COUNT(*) FROM concept_embeddings").fetchone()[0]
                mappings_count = self.db_conn.execute("SELECT COUNT(*) FROM mapping_results").fetchone()[0]
            except:
                similarities_count = embeddings_count = mappings_count = 0
        
        return {
            'cache_hit_rate': hit_rate,
            'total_requests': total_requests,
            'cached_similarities': similarities_count,
            'cached_embeddings': embeddings_count,
            'cached_mappings': mappings_count,
            **self.cache_stats
        }

class Neo4jGraphManager:
    """
    Manages Neo4j graph database for OMOP-UMLS knowledge graph
    Provides efficient graph-based queries and analytics
    """
    
    def __init__(self, config: InfrastructureConfig):
        self.config = config
        self.driver = None
        
        if NEO4J_AVAILABLE:
            self.connect()
        else:
            logger.warning("Neo4j not available - graph features disabled")
    
    def connect(self):
        """Connect to Neo4j database"""
        try:
            self.driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_user, self.config.neo4j_password)
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            logger.info(f"Connected to Neo4j: {self.config.neo4j_uri}")
            
            # Initialize schema
            self.init_graph_schema()
            
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
    
    def init_graph_schema(self):
        """Initialize Neo4j schema for OMOP-UMLS graph"""
        if not self.driver:
            return
        
        schema_queries = [
            # Node constraints and indexes
            "CREATE CONSTRAINT omop_concept_id IF NOT EXISTS FOR (c:OMOPConcept) REQUIRE c.concept_id IS UNIQUE",
            "CREATE CONSTRAINT umls_cui IF NOT EXISTS FOR (u:UMLSConcept) REQUIRE u.cui IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX omop_name_idx IF NOT EXISTS FOR (c:OMOPConcept) ON (c.concept_name)",
            "CREATE INDEX omop_vocab_idx IF NOT EXISTS FOR (c:OMOPConcept) ON (c.vocabulary_id)",
            "CREATE INDEX umls_name_idx IF NOT EXISTS FOR (u:UMLSConcept) ON (u.preferred_name)",
            "CREATE INDEX mapping_confidence_idx IF NOT EXISTS FOR ()-[r:MAPS_TO]-() ON (r.confidence_score)",
        ]
        
        with self.driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                except Exception as e:
                    logger.debug(f"Schema query failed (may already exist): {e}")
        
        logger.info("Neo4j schema initialized")
    
    def load_omop_concepts(self, concepts: List[Dict], batch_size: int = 1000):
        """Load OMOP concepts into Neo4j"""
        if not self.driver:
            logger.warning("Neo4j not available - skipping concept loading")
            return
        
        logger.info(f"Loading {len(concepts):,} OMOP concepts to Neo4j")
        
        # Process in batches for performance
        for i in range(0, len(concepts), batch_size):
            batch = concepts[i:i + batch_size]
            
            with self.driver.session() as session:
                session.run("""
                    UNWIND $concepts AS concept
                    MERGE (c:OMOPConcept {concept_id: concept.concept_id})
                    SET c.concept_name = concept.concept_name,
                        c.domain_id = concept.domain_id,
                        c.vocabulary_id = concept.vocabulary_id,
                        c.concept_class_id = concept.concept_class_id,
                        c.standard_concept = concept.standard_concept,
                        c.concept_code = concept.concept_code,
                        c.valid_start_date = concept.valid_start_date,
                        c.valid_end_date = concept.valid_end_date,
                        c.invalid_reason = concept.invalid_reason
                """, concepts=batch)
            
            if (i + batch_size) % 10000 == 0:
                logger.info(f"Loaded {i + batch_size:,} OMOP concepts")
        
        logger.info("OMOP concept loading complete")
    
    def load_umls_concepts(self, concepts: Dict, batch_size: int = 1000):
        """Load UMLS concepts into Neo4j"""
        if not self.driver:
            return
        
        logger.info(f"Loading {len(concepts):,} UMLS concepts to Neo4j")
        
        concept_list = []
        for cui, concept_data in concepts.items():
            concept_list.append({
                'cui': cui,
                'preferred_name': concept_data.get('preferred_name', ''),
                'semantic_types': concept_data.get('semantic_types', []),
                'definitions': concept_data.get('definitions', []),
                'synonyms': concept_data.get('synonyms', [])
            })
        
        # Process in batches
        for i in range(0, len(concept_list), batch_size):
            batch = concept_list[i:i + batch_size]
            
            with self.driver.session() as session:
                session.run("""
                    UNWIND $concepts AS concept
                    MERGE (u:UMLSConcept {cui: concept.cui})
                    SET u.preferred_name = concept.preferred_name,
                        u.semantic_types = concept.semantic_types,
                        u.definitions = concept.definitions,
                        u.synonyms = concept.synonyms
                """, concepts=batch)
            
            if (i + batch_size) % 10000 == 0:
                logger.info(f"Loaded {i + batch_size:,} UMLS concepts")
        
        logger.info("UMLS concept loading complete")
    
    def load_mappings(self, mappings: Dict, batch_size: int = 1000):
        """Load concept mappings into Neo4j"""
        if not self.driver:
            return
        
        logger.info(f"Loading {len(mappings):,} concept mappings to Neo4j")
        
        mapping_list = []
        for omop_concept_id, mapping_result in mappings.items():
            mapping_list.append({
                'omop_concept_id': omop_concept_id,
                'umls_cui': mapping_result.umls_cui,
                'mapping_type': mapping_result.mapping_type,
                'confidence_score': mapping_result.confidence_score,
                'similarity_score': mapping_result.similarity_score,
                'evidence': json.dumps(mapping_result.evidence)
            })
        
        # Process in batches
        for i in range(0, len(mapping_list), batch_size):
            batch = mapping_list[i:i + batch_size]
            
            with self.driver.session() as session:
                session.run("""
                    UNWIND $mappings AS mapping
                    MATCH (o:OMOPConcept {concept_id: mapping.omop_concept_id})
                    MATCH (u:UMLSConcept {cui: mapping.umls_cui})
                    MERGE (o)-[r:MAPS_TO]->(u)
                    SET r.mapping_type = mapping.mapping_type,
                        r.confidence_score = mapping.confidence_score,
                        r.similarity_score = mapping.similarity_score,
                        r.evidence = mapping.evidence
                """, mappings=batch)
            
            if (i + batch_size) % 5000 == 0:
                logger.info(f"Loaded {i + batch_size:,} mappings")
        
        logger.info("Mapping loading complete")
    
    def query_similar_concepts(self, concept_name: str, limit: int = 10) -> List[Dict]:
        """Query for similar concepts using graph traversal"""
        if not self.driver:
            return []
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (o:OMOPConcept)-[r:MAPS_TO]->(u:UMLSConcept)
                WHERE toLower(o.concept_name) CONTAINS toLower($concept_name)
                   OR toLower(u.preferred_name) CONTAINS toLower($concept_name)
                RETURN o.concept_id, o.concept_name, u.cui, u.preferred_name, 
                       r.confidence_score, r.mapping_type
                ORDER BY r.confidence_score DESC
                LIMIT $limit
            """, concept_name=concept_name, limit=limit)
            
            return [dict(record) for record in result]
    
    def get_mapping_statistics(self) -> Dict:
        """Get mapping statistics from Neo4j"""
        if not self.driver:
            return {}
        
        with self.driver.session() as session:
            stats = {}
            
            # Count nodes
            result = session.run("MATCH (o:OMOPConcept) RETURN count(o) as omop_count")
            stats['omop_concepts'] = result.single()['omop_count']
            
            result = session.run("MATCH (u:UMLSConcept) RETURN count(u) as umls_count")
            stats['umls_concepts'] = result.single()['umls_count']
            
            # Count mappings
            result = session.run("MATCH ()-[r:MAPS_TO]->() RETURN count(r) as mapping_count")
            stats['total_mappings'] = result.single()['mapping_count']
            
            # Mapping type distribution
            result = session.run("""
                MATCH ()-[r:MAPS_TO]->()
                RETURN r.mapping_type as type, count(r) as count
                ORDER BY count DESC
            """)
            stats['mapping_types'] = {record['type']: record['count'] for record in result}
            
            # Confidence distribution
            result = session.run("""
                MATCH ()-[r:MAPS_TO]->()
                RETURN 
                    count(CASE WHEN r.confidence_score >= 0.9 THEN 1 END) as high_confidence,
                    count(CASE WHEN r.confidence_score >= 0.7 AND r.confidence_score < 0.9 THEN 1 END) as medium_confidence,
                    count(CASE WHEN r.confidence_score < 0.7 THEN 1 END) as low_confidence
            """)
            confidence_stats = result.single()
            stats['confidence_distribution'] = dict(confidence_stats)
            
            return stats
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

class LLMEnhancedValidator:
    """
    Uses OpenAI LLM to enhance and validate concept mappings
    Leverages domain knowledge to improve mapping quality
    """
    
    def __init__(self, config: InfrastructureConfig):
        self.config = config
        self.client = None
        
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("OpenAI client initialized for LLM enhancement")
        else:
            logger.warning("OpenAI not available - LLM features disabled")
    
    def validate_mapping(self, omop_concept: Dict, umls_concept: Dict, 
                        confidence_score: float) -> Dict:
        """Validate a concept mapping using LLM"""
        if not self.client:
            return {'validated': False, 'llm_confidence': 0.0, 'explanation': 'LLM not available'}
        
        try:
            # Prepare prompt
            prompt = self._create_validation_prompt(omop_concept, umls_concept, confidence_score)
            
            # Query LLM
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": "You are a biomedical ontology expert specializing in concept mapping validation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            # Parse response
            llm_response = response.choices[0].message.content
            validation_result = self._parse_llm_response(llm_response)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"LLM validation error: {e}")
            return {'validated': False, 'llm_confidence': 0.0, 'explanation': f'Error: {str(e)}'}
    
    def _create_validation_prompt(self, omop_concept: Dict, umls_concept: Dict, 
                                confidence_score: float) -> str:
        """Create validation prompt for LLM"""
        
        omop_name = omop_concept.get('concept_name', '')
        omop_vocab = omop_concept.get('vocabulary_id', '')
        omop_domain = omop_concept.get('domain_id', '')
        
        umls_name = umls_concept.get('preferred_name', '')
        umls_types = ', '.join(umls_concept.get('semantic_types', []))
        umls_defs = '. '.join(umls_concept.get('definitions', []))
        
        prompt = f"""
        Please validate this concept mapping between OMOP and UMLS:

        OMOP Concept:
        - Name: "{omop_name}"
        - Vocabulary: {omop_vocab}
        - Domain: {omop_domain}

        UMLS Concept:
        - Preferred Name: "{umls_name}"
        - Semantic Types: {umls_types}
        - Definition: {umls_defs}

        Current Confidence Score: {confidence_score:.2f}

        Questions:
        1. Are these concepts semantically equivalent or closely related?
        2. Is this mapping medically/clinically accurate?
        3. What confidence level (0.0-1.0) would you assign?

        Respond in this format:
        VALIDATED: [YES/NO]
        CONFIDENCE: [0.0-1.0]
        EXPLANATION: [Brief explanation]
        """
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM validation response"""
        result = {
            'validated': False,
            'llm_confidence': 0.0,
            'explanation': response
        }
        
        try:
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('VALIDATED:'):
                    validated_text = line.split(':', 1)[1].strip().upper()
                    result['validated'] = validated_text == 'YES'
                
                elif line.startswith('CONFIDENCE:'):
                    confidence_text = line.split(':', 1)[1].strip()
                    try:
                        result['llm_confidence'] = float(confidence_text)
                    except ValueError:
                        result['llm_confidence'] = 0.0
                
                elif line.startswith('EXPLANATION:'):
                    result['explanation'] = line.split(':', 1)[1].strip()
        
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
        
        return result
    
    def batch_validate_mappings(self, mappings: List[Tuple], 
                              omop_concepts: Dict, umls_concepts: Dict) -> List[Dict]:
        """Validate multiple mappings in batch"""
        if not self.client:
            return []
        
        logger.info(f"LLM batch validation of {len(mappings)} mappings")
        
        validation_results = []
        
        # Process in batches to manage API limits
        for i in range(0, len(mappings), self.config.llm_batch_size):
            batch = mappings[i:i + self.config.llm_batch_size]
            
            for omop_concept_id, mapping_result in batch:
                omop_concept = next(
                    (c for c in omop_concepts if c['concept_id'] == omop_concept_id),
                    {}
                )
                umls_concept = umls_concepts.get(mapping_result.umls_cui, {})
                
                validation = self.validate_mapping(
                    omop_concept, 
                    umls_concept, 
                    mapping_result.confidence_score
                )
                
                validation_results.append({
                    'omop_concept_id': omop_concept_id,
                    'umls_cui': mapping_result.umls_cui,
                    'original_confidence': mapping_result.confidence_score,
                    **validation
                })
                
                # Small delay to respect API limits
                time.sleep(0.1)
            
            logger.info(f"Validated {min(i + self.config.llm_batch_size, len(mappings))} mappings")
        
        return validation_results
    
    def suggest_alternative_mappings(self, omop_concept: Dict, 
                                   candidate_umls_concepts: List[Dict]) -> List[Dict]:
        """Use LLM to suggest alternative mappings"""
        if not self.client or not candidate_umls_concepts:
            return []
        
        try:
            # Create prompt with candidates
            prompt = self._create_suggestion_prompt(omop_concept, candidate_umls_concepts)
            
            response = self.client.chat.completions.create(
                model=self.config.llm_model,
                messages=[
                    {"role": "system", "content": "You are a biomedical ontology expert. Rank concept mappings by semantic similarity and clinical relevance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            # Parse suggestions
            suggestions = self._parse_suggestions(response.choices[0].message.content)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"LLM suggestion error: {e}")
            return []
    
    def _create_suggestion_prompt(self, omop_concept: Dict, candidates: List[Dict]) -> str:
        """Create suggestion prompt for LLM"""
        
        omop_name = omop_concept.get('concept_name', '')
        omop_vocab = omop_concept.get('vocabulary_id', '')
        
        prompt = f"""
        Find the best UMLS concept mapping for this OMOP concept:
        
        OMOP Concept: "{omop_name}" (Vocabulary: {omop_vocab})
        
        UMLS Candidates:
        """
        
        for i, candidate in enumerate(candidates[:5], 1):  # Limit to top 5
            prompt += f"""
        {i}. CUI: {candidate.get('cui', '')}
           Name: "{candidate.get('preferred_name', '')}"
           Types: {', '.join(candidate.get('semantic_types', []))}
           Definition: {'. '.join(candidate.get('definitions', [])[:1])}
        """
        
        prompt += """
        
        Rank these candidates (1-5) by relevance and provide confidence scores (0.0-1.0).
        
        Format:
        RANK: [1-5]
        CUI: [CUI]
        CONFIDENCE: [0.0-1.0]
        REASON: [Brief explanation]
        """
        
        return prompt
    
    def _parse_suggestions(self, response: str) -> List[Dict]:
        """Parse LLM suggestions"""
        suggestions = []
        
        try:
            # Split by rank entries
            entries = response.split('RANK:')[1:]  # Skip first empty split
            
            for entry in entries:
                lines = entry.strip().split('\n')
                suggestion = {}
                
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith(('1', '2', '3', '4', '5')):
                        suggestion['rank'] = int(line[0])
                    elif line.startswith('CUI:'):
                        suggestion['cui'] = line.split(':', 1)[1].strip()
                    elif line.startswith('CONFIDENCE:'):
                        try:
                            suggestion['confidence'] = float(line.split(':', 1)[1].strip())
                        except ValueError:
                            suggestion['confidence'] = 0.0
                    elif line.startswith('REASON:'):
                        suggestion['reason'] = line.split(':', 1)[1].strip()
                
                if 'cui' in suggestion:
                    suggestions.append(suggestion)
        
        except Exception as e:
            logger.error(f"Error parsing suggestions: {e}")
        
        return sorted(suggestions, key=lambda x: x.get('rank', 999))

class PersistentInfrastructureManager:
    """
    Main manager for persistent OMOP-UMLS infrastructure
    Coordinates caching, Neo4j, and LLM enhancement
    """
    
    def __init__(self, config: InfrastructureConfig = None):
        self.config = config or InfrastructureConfig()
        
        # Initialize components
        self.cache_manager = PersistentCacheManager(self.config)
        self.graph_manager = Neo4jGraphManager(self.config) if NEO4J_AVAILABLE else None
        self.llm_validator = LLMEnhancedValidator(self.config) if OPENAI_AVAILABLE else None
        
        # Processing state
        self.processing_state = {
            'omop_loaded': False,
            'umls_loaded': False,
            'mappings_computed': False,
            'llm_validated': False,
            'last_update': None
        }
        
        logger.info("Persistent infrastructure manager initialized")
    
    def setup_complete_infrastructure(self, omop_concepts: List[Dict], 
                                    umls_concepts: Dict, 
                                    mappings: Dict) -> Dict:
        """
        Set up complete persistent infrastructure
        One-time setup for long-term reuse
        """
        logger.info("Setting up complete persistent infrastructure...")
        
        setup_results = {
            'cache_setup': False,
            'neo4j_setup': False,
            'llm_validation': False,
            'processing_time': 0,
            'statistics': {}
        }
        
        start_time = time.time()
        
        try:
            # 1. Set up caching infrastructure
            logger.info("Phase 1: Setting up persistent caching...")
            self._setup_caching_infrastructure(omop_concepts, umls_concepts, mappings)
            setup_results['cache_setup'] = True
            
            # 2. Set up Neo4j graph database
            if self.graph_manager:
                logger.info("Phase 2: Setting up Neo4j graph database...")
                self._setup_neo4j_infrastructure(omop_concepts, umls_concepts, mappings)
                setup_results['neo4j_setup'] = True
            
            # 3. LLM validation (selective)
            if self.llm_validator and self.config.enable_llm_validation:
                logger.info("Phase 3: Running LLM validation...")
                self._setup_llm_validation(omop_concepts, umls_concepts, mappings)
                setup_results['llm_validation'] = True
            
            # 4. Update processing state
            self.processing_state.update({
                'omop_loaded': True,
                'umls_loaded': True,
                'mappings_computed': True,
                'llm_validated': setup_results['llm_validation'],
                'last_update': datetime.now().isoformat()
            })
            
            self.cache_manager.set_processing_metadata('processing_state', self.processing_state)
            
            # 5. Generate statistics
            setup_results['statistics'] = self._generate_infrastructure_statistics()
            
            processing_time = time.time() - start_time
            setup_results['processing_time'] = processing_time
            
            logger.info(f"Infrastructure setup complete in {processing_time:.2f} seconds")
            
            return setup_results
            
        except Exception as e:
            logger.error(f"Infrastructure setup failed: {e}")
            raise
    
    def _setup_caching_infrastructure(self, omop_concepts: List[Dict], 
                                    umls_concepts: Dict, mappings: Dict):
        """Set up persistent caching"""
        
        # Cache all mappings
        for omop_concept_id, mapping_result in mappings.items():
            self.cache_manager.cache_mapping_result(
                omop_concept_id,
                mapping_result.umls_cui,
                mapping_result.confidence_score,
                mapping_result.mapping_type,
                mapping_result.evidence
            )
        
        # Cache metadata
        self.cache_manager.set_processing_metadata('omop_concept_count', len(omop_concepts))
        self.cache_manager.set_processing_metadata('umls_concept_count', len(umls_concepts))
        self.cache_manager.set_processing_metadata('mapping_count', len(mappings))
        
        logger.info("Caching infrastructure setup complete")
    
    def _setup_neo4j_infrastructure(self, omop_concepts: List[Dict], 
                                   umls_concepts: Dict, mappings: Dict):
        """Set up Neo4j graph database"""
        
        # Load concepts
        self.graph_manager.load_omop_concepts(omop_concepts)
        self.graph_manager.load_umls_concepts(umls_concepts)
        
        # Load mappings
        self.graph_manager.load_mappings(mappings)
        
        logger.info("Neo4j infrastructure setup complete")
    
    def _setup_llm_validation(self, omop_concepts: List[Dict], 
                            umls_concepts: Dict, mappings: Dict):
        """Set up LLM validation (selective)"""
        
        # Select high-value mappings for LLM validation
        high_value_mappings = [
            (omop_id, mapping) for omop_id, mapping in mappings.items()
            if mapping.confidence_score < self.config.llm_confidence_threshold
        ]
        
        # Limit to manageable number for API costs
        sample_size = min(len(high_value_mappings), 100)
        validation_sample = high_value_mappings[:sample_size]
        
        if validation_sample:
            validation_results = self.llm_validator.batch_validate_mappings(
                validation_sample, 
                {c['concept_id']: c for c in omop_concepts},
                umls_concepts
            )
            
            # Cache LLM validation results
            for result in validation_results:
                self.cache_manager.cache_mapping_result(
                    result['omop_concept_id'],
                    result['umls_cui'],
                    result['original_confidence'],
                    'llm_validated',
                    result,
                    llm_validated=True
                )
        
        logger.info(f"LLM validation complete for {len(validation_sample)} mappings")
    
    def _generate_infrastructure_statistics(self) -> Dict:
        """Generate comprehensive infrastructure statistics"""
        
        stats = {
            'cache_statistics': self.cache_manager.get_cache_statistics(),
            'processing_state': self.processing_state
        }
        
        if self.graph_manager:
            stats['neo4j_statistics'] = self.graph_manager.get_mapping_statistics()
        
        return stats
    
    def is_infrastructure_ready(self) -> bool:
        """Check if infrastructure is ready for use"""
        state = self.cache_manager.get_processing_metadata('processing_state')
        
        if state:
            return (state.get('omop_loaded', False) and 
                   state.get('umls_loaded', False) and 
                   state.get('mappings_computed', False))
        
        return False
    
    def get_cached_mappings_fast(self, omop_concept_ids: List[int] = None) -> pd.DataFrame:
        """Fast retrieval of cached mappings"""
        return self.cache_manager.get_cached_mappings(omop_concept_ids)
    
    def query_graph_fast(self, query: str, **kwargs) -> List[Dict]:
        """Fast graph queries using Neo4j"""
        if self.graph_manager:
            return self.graph_manager.query_similar_concepts(query, **kwargs)
        return []
    
    def close(self):
        """Clean up resources"""
        if self.graph_manager:
            self.graph_manager.close()
        
        if hasattr(self.cache_manager, 'db_conn'):
            self.cache_manager.db_conn.close()
        
        logger.info("Infrastructure resources closed")

def main():
    """Example setup of persistent infrastructure"""
    
    # Configuration
    config = InfrastructureConfig(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="your_password",
        enable_llm_validation=True,
        llm_model="gpt-3.5-turbo"
    )
    
    # Initialize infrastructure
    infrastructure = PersistentInfrastructureManager(config)
    
    # Example usage (would be integrated with your OMOP-UMLS processing)
    print("Persistent Infrastructure Manager initialized")
    print(f"Neo4j available: {NEO4J_AVAILABLE}")
    print(f"OpenAI available: {OPENAI_AVAILABLE}")
    print(f"Infrastructure ready: {infrastructure.is_infrastructure_ready()}")

if __name__ == "__main__":
    main()
