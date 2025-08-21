#!/usr/bin/env python3
"""
Production Optimizer for OMOP-UMLS Integration
Leverages OntologyRAG, GRAPE, and OMOP2OBO knowledge for large-scale processing
Builds upon existing RAG Literature infrastructure for production scalability
"""

import pandas as pd
import numpy as np
import networkx as nx
import logging
import time
import os
import sys
import gc
import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import psutil
from dataclasses import dataclass
from functools import lru_cache, wraps
import tracemalloc
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import threading
from collections import defaultdict, deque

# Import our existing modules
from omop_cdm_processor import OMOPDataProcessor, OMOPConfig, MemoryManager
from umls_omop_mapper import UMLSOMOPMapper, MappingConfig, MappingResult
from omop_umls_integrator import OMOPUMLSIntegrator, IntegrationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProductionMetrics:
    """Production performance metrics tracking"""
    concepts_processed: int = 0
    processing_rate: float = 0.0  # concepts per second
    memory_peak: float = 0.0
    memory_current: float = 0.0
    cpu_utilization: float = 0.0
    cache_hit_rate: float = 0.0
    mapping_accuracy: float = 0.0
    error_rate: float = 0.0
    processing_time: float = 0.0

@dataclass
class ProductionConfig:
    """Production-optimized configuration"""
    # Data processing
    chunk_size: int = 250000  # Larger chunks for production
    max_workers: int = min(mp.cpu_count(), 16)  # Cap at 16 workers
    memory_limit_gb: float = 32.0  # Production memory allocation
    
    # OntologyRAG optimizations
    enable_semantic_caching: bool = True
    semantic_cache_size: int = 100000
    enable_hierarchical_pruning: bool = True
    
    # GRAPE-style optimizations
    enable_parallel_chunking: bool = True
    enable_memory_mapping: bool = True
    enable_graph_compression: bool = True
    
    # Database backend for very large datasets
    use_database_backend: bool = False
    database_path: str = "production_cache.db"
    
    # Quality and validation
    enable_incremental_validation: bool = True
    validation_sample_rate: float = 0.1  # Validate 10% of mappings
    
    # Monitoring
    enable_performance_monitoring: bool = True
    monitoring_interval: float = 30.0  # seconds

class GRAPEOptimizedProcessor:
    """
    GRAPE-style processor optimized for production scale
    Leverages techniques from your existing RAG Literature work
    """
    
    def __init__(self, config: ProductionConfig):
        self.config = config
        self.memory_manager = MemoryManager(config.memory_limit_gb)
        self.performance_metrics = ProductionMetrics()
        self.processing_cache = {}
        self.semantic_cache = {}
        
        # Initialize database backend if enabled
        if config.use_database_backend:
            self.init_database_backend()
        
        # Performance monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
        logger.info(f"Initialized GRAPE-optimized processor with {config.max_workers} workers")
    
    def init_database_backend(self):
        """Initialize SQLite backend for very large datasets"""
        self.db_path = Path(self.config.database_path)
        self.db_conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        
        # Create optimized tables
        self.db_conn.executescript("""
            CREATE TABLE IF NOT EXISTS concepts (
                concept_id INTEGER PRIMARY KEY,
                concept_name TEXT NOT NULL,
                vocabulary_id TEXT,
                domain_id TEXT,
                concept_class_id TEXT,
                standard_concept TEXT,
                concept_code TEXT,
                valid_start_date TEXT,
                valid_end_date TEXT,
                invalid_reason TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_concept_name ON concepts(concept_name);
            CREATE INDEX IF NOT EXISTS idx_vocabulary ON concepts(vocabulary_id);
            CREATE INDEX IF NOT EXISTS idx_domain ON concepts(domain_id);
            CREATE INDEX IF NOT EXISTS idx_standard ON concepts(standard_concept);
            
            CREATE TABLE IF NOT EXISTS mappings (
                omop_concept_id INTEGER,
                umls_cui TEXT,
                confidence_score REAL,
                mapping_type TEXT,
                similarity_score REAL,
                evidence TEXT,
                PRIMARY KEY (omop_concept_id, umls_cui)
            );
            
            CREATE INDEX IF NOT EXISTS idx_mappings_cui ON mappings(umls_cui);
            CREATE INDEX IF NOT EXISTS idx_mappings_confidence ON mappings(confidence_score);
        """)
        
        logger.info(f"Initialized database backend: {self.db_path}")
    
    def start_performance_monitoring(self):
        """Start background performance monitoring"""
        if not self.config.enable_performance_monitoring:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitor_performance)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("Started performance monitoring")
    
    def stop_performance_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5.0)
    
    def _monitor_performance(self):
        """Background performance monitoring thread"""
        while self.monitoring_active:
            try:
                # Update performance metrics
                process = psutil.Process()
                
                self.performance_metrics.memory_current = process.memory_info().rss / (1024**3)
                self.performance_metrics.cpu_utilization = process.cpu_percent()
                
                if self.performance_metrics.memory_current > self.performance_metrics.memory_peak:
                    self.performance_metrics.memory_peak = self.performance_metrics.memory_current
                
                # Log performance if significant changes
                if self.performance_metrics.memory_current > self.config.memory_limit_gb * 0.8:
                    logger.warning(f"High memory usage: {self.performance_metrics.memory_current:.2f} GB")
                
                time.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                break
    
    @lru_cache(maxsize=50000)
    def cached_semantic_similarity(self, text1: str, text2: str) -> float:
        """Cached semantic similarity calculation using OntologyRAG approach"""
        # This would use your existing TF-IDF vectorizer from OntologyRAG
        # Simplified implementation for demonstration
        if not hasattr(self, '_vectorizer'):
            self._vectorizer = TfidfVectorizer(max_features=10000, stop_words='english')
            # In production, load pre-trained vectorizer from your existing work
        
        try:
            vectors = self._vectorizer.transform([text1.lower(), text2.lower()])
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
            return float(similarity)
        except:
            return 0.0
    
    def process_concepts_in_parallel_chunks(self, concepts: List[Dict], 
                                          processing_func: callable) -> Generator[List[Dict], None, None]:
        """
        GRAPE-style parallel chunked processing
        Optimized for large-scale concept processing
        """
        logger.info(f"Processing {len(concepts):,} concepts in parallel chunks")
        
        # Create chunks
        chunk_size = self.config.chunk_size
        concept_chunks = [
            concepts[i:i + chunk_size] 
            for i in range(0, len(concepts), chunk_size)
        ]
        
        logger.info(f"Created {len(concept_chunks)} chunks of size {chunk_size:,}")
        
        # Process chunks in parallel
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all chunks
            future_to_chunk = {
                executor.submit(processing_func, chunk): chunk 
                for chunk in concept_chunks
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                try:
                    result = future.result()
                    
                    # Update performance metrics
                    if isinstance(result, list):
                        self.performance_metrics.concepts_processed += len(result)
                    
                    # Memory management
                    if not self.memory_manager.is_memory_available(1.0):
                        logger.warning("Memory threshold reached, forcing garbage collection")
                        gc.collect()
                    
                    yield result
                    
                except Exception as e:
                    chunk = future_to_chunk[future]
                    logger.error(f"Chunk processing failed: {e}")
                    self.performance_metrics.error_rate += 1
                    continue
    
    def optimized_concept_mapping(self, omop_concepts: List[Dict], 
                                 umls_concepts: Dict) -> Dict[int, MappingResult]:
        """
        Production-optimized concept mapping using OntologyRAG strategies
        """
        logger.info(f"Starting optimized mapping for {len(omop_concepts):,} OMOP concepts")
        
        mappings = {}
        start_time = time.time()
        
        # Strategy 1: Vocabulary-based prioritization (from OMOP2OBO knowledge)
        vocabulary_priority = ['UMLS', 'SNOMED', 'ICD10CM', 'RxNorm', 'LOINC', 'CPT4']
        
        # Group concepts by vocabulary for efficient processing
        vocab_groups = defaultdict(list)
        for concept in omop_concepts:
            vocab_id = concept.get('vocabulary_id', 'Unknown')
            vocab_groups[vocab_id].append(concept)
        
        # Process by priority
        for vocab in vocabulary_priority:
            if vocab in vocab_groups:
                logger.info(f"Processing {len(vocab_groups[vocab]):,} concepts from {vocab}")
                
                # Use specialized mapping for each vocabulary
                vocab_mappings = self._map_vocabulary_concepts(
                    vocab_groups[vocab], umls_concepts, vocab
                )
                mappings.update(vocab_mappings)
                
                # Memory management
                gc.collect()
        
        # Process remaining vocabularies
        for vocab, concepts in vocab_groups.items():
            if vocab not in vocabulary_priority:
                logger.info(f"Processing {len(concepts):,} concepts from {vocab}")
                vocab_mappings = self._map_vocabulary_concepts(concepts, umls_concepts, vocab)
                mappings.update(vocab_mappings)
        
        # Update performance metrics
        processing_time = time.time() - start_time
        self.performance_metrics.processing_time = processing_time
        self.performance_metrics.processing_rate = len(omop_concepts) / processing_time
        
        logger.info(f"Mapping complete: {len(mappings):,} mappings in {processing_time:.2f}s")
        logger.info(f"Processing rate: {self.performance_metrics.processing_rate:.1f} concepts/second")
        
        return mappings
    
    def _map_vocabulary_concepts(self, concepts: List[Dict], umls_concepts: Dict, 
                               vocabulary: str) -> Dict[int, MappingResult]:
        """Map concepts from specific vocabulary using optimized strategies"""
        
        mappings = {}
        
        # Vocabulary-specific optimization strategies
        if vocabulary == 'UMLS':
            # Direct CUI mappings - highest confidence
            mappings.update(self._direct_cui_mapping(concepts, umls_concepts))
            
        elif vocabulary in ['SNOMED', 'ICD10CM']:
            # Medical terminologies - use semantic similarity
            mappings.update(self._semantic_similarity_mapping(concepts, umls_concepts))
            
        elif vocabulary == 'RxNorm':
            # Drug concepts - specialized drug matching
            mappings.update(self._drug_concept_mapping(concepts, umls_concepts))
            
        else:
            # General mapping approach
            mappings.update(self._general_concept_mapping(concepts, umls_concepts))
        
        return mappings
    
    def _direct_cui_mapping(self, concepts: List[Dict], umls_concepts: Dict) -> Dict[int, MappingResult]:
        """Direct CUI mapping for UMLS vocabulary concepts"""
        mappings = {}
        
        for concept in concepts:
            concept_id = concept['concept_id']
            concept_code = concept.get('concept_code', '')
            
            if concept_code in umls_concepts:
                mappings[concept_id] = MappingResult(
                    omop_concept_id=concept_id,
                    umls_cui=concept_code,
                    mapping_type='direct_cui',
                    confidence_score=1.0,
                    similarity_score=1.0,
                    evidence={
                        'method': 'direct_cui_mapping',
                        'vocabulary': 'UMLS',
                        'concept_code': concept_code
                    }
                )
        
        logger.info(f"Direct CUI mapping: {len(mappings)} mappings")
        return mappings
    
    def _semantic_similarity_mapping(self, concepts: List[Dict], 
                                   umls_concepts: Dict) -> Dict[int, MappingResult]:
        """Semantic similarity mapping using OntologyRAG approach"""
        mappings = {}
        
        # Build concept embeddings if not cached
        if not hasattr(self, '_concept_embeddings'):
            self._build_concept_embeddings(umls_concepts)
        
        for concept in concepts:
            concept_id = concept['concept_id']
            concept_name = concept.get('concept_name', '').lower().strip()
            
            if not concept_name:
                continue
            
            # Find best semantic match
            best_match = self._find_best_semantic_match(concept_name, umls_concepts)
            
            if best_match and best_match['similarity'] >= 0.7:
                mappings[concept_id] = MappingResult(
                    omop_concept_id=concept_id,
                    umls_cui=best_match['cui'],
                    mapping_type='semantic_similarity',
                    confidence_score=min(best_match['similarity'] * 0.9, 0.95),
                    similarity_score=best_match['similarity'],
                    evidence={
                        'method': 'semantic_similarity_ontologyrag',
                        'omop_name': concept['concept_name'],
                        'umls_name': best_match['name'],
                        'similarity': best_match['similarity']
                    }
                )
        
        logger.info(f"Semantic similarity mapping: {len(mappings)} mappings")
        return mappings
    
    def _drug_concept_mapping(self, concepts: List[Dict], 
                            umls_concepts: Dict) -> Dict[int, MappingResult]:
        """Specialized mapping for drug concepts (RxNorm)"""
        mappings = {}
        
        # Drug-specific matching strategies
        drug_patterns = [
            r'\b(\w+)\s+\d+\s*mg\b',  # Drug name + dosage
            r'\b(\w+)\s+tablet\b',     # Drug name + form
            r'\b(\w+)\s+capsule\b',    # Drug name + form
        ]
        
        for concept in concepts:
            concept_id = concept['concept_id']
            concept_name = concept.get('concept_name', '').lower()
            
            # Try exact match first
            exact_match = self._find_exact_drug_match(concept_name, umls_concepts)
            if exact_match:
                mappings[concept_id] = exact_match
                continue
            
            # Try pattern-based matching
            pattern_match = self._find_pattern_drug_match(concept_name, umls_concepts, drug_patterns)
            if pattern_match:
                mappings[concept_id] = pattern_match
        
        logger.info(f"Drug concept mapping: {len(mappings)} mappings")
        return mappings
    
    def _general_concept_mapping(self, concepts: List[Dict], 
                               umls_concepts: Dict) -> Dict[int, MappingResult]:
        """General concept mapping using multiple strategies"""
        mappings = {}
        
        for concept in concepts:
            concept_id = concept['concept_id']
            concept_name = concept.get('concept_name', '').lower().strip()
            
            # Try exact string match
            exact_match = self._find_exact_string_match(concept_name, umls_concepts)
            if exact_match:
                mappings[concept_id] = MappingResult(
                    omop_concept_id=concept_id,
                    umls_cui=exact_match['cui'],
                    mapping_type='exact_string',
                    confidence_score=0.9,
                    similarity_score=1.0,
                    evidence={
                        'method': 'exact_string_match',
                        'omop_name': concept['concept_name'],
                        'umls_name': exact_match['name']
                    }
                )
                continue
            
            # Try fuzzy matching
            fuzzy_match = self._find_fuzzy_match(concept_name, umls_concepts)
            if fuzzy_match and fuzzy_match['similarity'] >= 0.8:
                mappings[concept_id] = MappingResult(
                    omop_concept_id=concept_id,
                    umls_cui=fuzzy_match['cui'],
                    mapping_type='fuzzy_match',
                    confidence_score=min(fuzzy_match['similarity'] * 0.8, 0.85),
                    similarity_score=fuzzy_match['similarity'],
                    evidence={
                        'method': 'fuzzy_string_match',
                        'omop_name': concept['concept_name'],
                        'umls_name': fuzzy_match['name'],
                        'similarity': fuzzy_match['similarity']
                    }
                )
        
        logger.info(f"General concept mapping: {len(mappings)} mappings")
        return mappings
    
    def _build_concept_embeddings(self, umls_concepts: Dict):
        """Build TF-IDF embeddings for UMLS concepts (OntologyRAG approach)"""
        logger.info("Building concept embeddings for semantic similarity...")
        
        # Prepare texts
        texts = []
        concept_ids = []
        
        for cui, concept_data in umls_concepts.items():
            # Combine name, definitions, and synonyms
            text_parts = [concept_data.get('preferred_name', '')]
            
            if 'definitions' in concept_data:
                text_parts.extend(concept_data['definitions'])
            
            if 'synonyms' in concept_data:
                text_parts.extend(concept_data['synonyms'])
            
            combined_text = ' '.join(text_parts).lower()
            texts.append(combined_text)
            concept_ids.append(cui)
        
        # Build TF-IDF vectors
        self._vectorizer = TfidfVectorizer(
            max_features=20000,  # Increased for production
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        
        self._concept_embeddings = self._vectorizer.fit_transform(texts)
        self._concept_ids_ordered = concept_ids
        
        logger.info(f"Built embeddings for {len(concept_ids):,} UMLS concepts")
    
    def _find_best_semantic_match(self, query_text: str, umls_concepts: Dict) -> Optional[Dict]:
        """Find best semantic match using cached similarity"""
        
        # Check cache first
        cache_key = hash(query_text)
        if cache_key in self.semantic_cache:
            return self.semantic_cache[cache_key]
        
        if not hasattr(self, '_concept_embeddings'):
            return None
        
        try:
            # Transform query
            query_vector = self._vectorizer.transform([query_text])
            
            # Calculate similarities
            similarities = cosine_similarity(query_vector, self._concept_embeddings).flatten()
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_similarity = similarities[best_idx]
            
            if best_similarity >= 0.5:  # Minimum threshold
                best_cui = self._concept_ids_ordered[best_idx]
                best_concept = umls_concepts[best_cui]
                
                result = {
                    'cui': best_cui,
                    'name': best_concept.get('preferred_name', ''),
                    'similarity': float(best_similarity)
                }
                
                # Cache result
                if len(self.semantic_cache) < self.config.semantic_cache_size:
                    self.semantic_cache[cache_key] = result
                
                return result
        
        except Exception as e:
            logger.debug(f"Semantic matching error: {e}")
        
        return None
    
    def _find_exact_string_match(self, query_text: str, umls_concepts: Dict) -> Optional[Dict]:
        """Find exact string match in UMLS concepts"""
        query_lower = query_text.lower().strip()
        
        for cui, concept_data in umls_concepts.items():
            # Check preferred name
            preferred_name = concept_data.get('preferred_name', '').lower().strip()
            if preferred_name == query_lower:
                return {'cui': cui, 'name': concept_data.get('preferred_name', '')}
            
            # Check synonyms
            synonyms = concept_data.get('synonyms', [])
            for synonym in synonyms:
                if synonym.lower().strip() == query_lower:
                    return {'cui': cui, 'name': concept_data.get('preferred_name', '')}
        
        return None
    
    def _find_fuzzy_match(self, query_text: str, umls_concepts: Dict) -> Optional[Dict]:
        """Find fuzzy string match using difflib"""
        from difflib import SequenceMatcher
        
        best_match = None
        best_similarity = 0.0
        
        query_lower = query_text.lower().strip()
        
        # Sample subset for performance (in production, use more sophisticated sampling)
        sample_concepts = dict(list(umls_concepts.items())[:10000])
        
        for cui, concept_data in sample_concepts.items():
            preferred_name = concept_data.get('preferred_name', '').lower().strip()
            
            if preferred_name:
                similarity = SequenceMatcher(None, query_lower, preferred_name).ratio()
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'cui': cui,
                        'name': concept_data.get('preferred_name', ''),
                        'similarity': similarity
                    }
        
        return best_match if best_similarity >= 0.7 else None
    
    def _find_exact_drug_match(self, drug_name: str, umls_concepts: Dict) -> Optional[MappingResult]:
        """Find exact match for drug concepts"""
        # Simplified drug matching - in production, use specialized drug databases
        exact_match = self._find_exact_string_match(drug_name, umls_concepts)
        
        if exact_match:
            return MappingResult(
                omop_concept_id=0,  # Will be set by caller
                umls_cui=exact_match['cui'],
                mapping_type='exact_drug_match',
                confidence_score=0.95,
                similarity_score=1.0,
                evidence={
                    'method': 'exact_drug_match',
                    'drug_name': drug_name,
                    'umls_name': exact_match['name']
                }
            )
        
        return None
    
    def _find_pattern_drug_match(self, drug_name: str, umls_concepts: Dict, 
                               patterns: List[str]) -> Optional[MappingResult]:
        """Find drug match using pattern matching"""
        import re
        
        for pattern in patterns:
            match = re.search(pattern, drug_name)
            if match:
                base_drug = match.group(1)
                
                # Look for base drug name in UMLS
                exact_match = self._find_exact_string_match(base_drug, umls_concepts)
                if exact_match:
                    return MappingResult(
                        omop_concept_id=0,  # Will be set by caller
                        umls_cui=exact_match['cui'],
                        mapping_type='pattern_drug_match',
                        confidence_score=0.8,
                        similarity_score=0.9,
                        evidence={
                            'method': 'pattern_drug_match',
                            'pattern': pattern,
                            'base_drug': base_drug,
                            'umls_name': exact_match['name']
                        }
                    )
        
        return None
    
    def save_production_cache(self, output_path: Path):
        """Save production processing cache"""
        cache_data = {
            'semantic_cache': self.semantic_cache,
            'processing_cache': self.processing_cache,
            'performance_metrics': self.performance_metrics.__dict__
        }
        
        with open(output_path / 'production_cache.pkl', 'wb') as f:
            pickle.dump(cache_data, f)
        
        logger.info(f"Saved production cache to {output_path}")
    
    def load_production_cache(self, cache_path: Path):
        """Load production processing cache"""
        cache_file = cache_path / 'production_cache.pkl'
        
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            self.semantic_cache = cache_data.get('semantic_cache', {})
            self.processing_cache = cache_data.get('processing_cache', {})
            
            logger.info(f"Loaded production cache from {cache_path}")
        else:
            logger.info("No existing cache found, starting fresh")

class ProductionOMOPUMLSIntegrator(OMOPUMLSIntegrator):
    """
    Production-optimized OMOP-UMLS integrator
    Extends base integrator with GRAPE and OntologyRAG optimizations
    """
    
    def __init__(self, config: IntegrationConfig, production_config: ProductionConfig = None):
        super().__init__(config)
        
        self.production_config = production_config or ProductionConfig()
        self.grape_processor = GRAPEOptimizedProcessor(self.production_config)
        
        # Replace standard mapper with optimized version
        self.umls_mapper = ProductionUMLSMapper(
            config.umls_graph_path,
            config.mapping_config,
            self.grape_processor
        )
        
        logger.info("Initialized Production OMOP-UMLS Integrator")
    
    def run_production_integration(self) -> Dict:
        """Run production-scale integration with all optimizations"""
        logger.info("="*80)
        logger.info("STARTING PRODUCTION OMOP-UMLS INTEGRATION")
        logger.info("="*80)
        
        # Start performance monitoring
        self.grape_processor.start_performance_monitoring()
        
        try:
            # Load production cache
            self.grape_processor.load_production_cache(self.output_path)
            
            # Run standard integration with optimizations
            integration_stats = self.run_complete_integration()
            
            # Add production metrics
            integration_stats.update({
                'production_metrics': self.grape_processor.performance_metrics.__dict__,
                'cache_statistics': {
                    'semantic_cache_size': len(self.grape_processor.semantic_cache),
                    'processing_cache_size': len(self.grape_processor.processing_cache)
                }
            })
            
            # Save production cache
            self.grape_processor.save_production_cache(self.output_path)
            
            return integration_stats
            
        finally:
            # Stop monitoring
            self.grape_processor.stop_performance_monitoring()

class ProductionUMLSMapper(UMLSOMOPMapper):
    """Production-optimized UMLS mapper with GRAPE and OntologyRAG enhancements"""
    
    def __init__(self, umls_graph_path: str, config: MappingConfig, 
                 grape_processor: GRAPEOptimizedProcessor):
        super().__init__(umls_graph_path, config)
        self.grape_processor = grape_processor
        
    def map_omop_to_umls(self, omop_concepts: List[Dict]) -> Dict:
        """Production-optimized mapping using GRAPE processor"""
        logger.info(f"Starting production UMLS-OMOP mapping for {len(omop_concepts):,} concepts")
        
        # Use GRAPE-optimized mapping
        mappings = self.grape_processor.optimized_concept_mapping(
            omop_concepts, 
            self.umls_concepts
        )
        
        # Update statistics
        self.mapping_statistics['total_omop_concepts'] = len(omop_concepts)
        self.mapping_statistics['mapped_concepts'] = len(mappings)
        self.mapping_statistics['unmapped_concepts'] = len(omop_concepts) - len(mappings)
        
        coverage = len(mappings) / len(omop_concepts) * 100 if omop_concepts else 0
        
        logger.info("Production UMLS-OMOP mapping complete:")
        logger.info(f"  Total concepts: {len(omop_concepts):,}")
        logger.info(f"  Mapped concepts: {len(mappings):,}")
        logger.info(f"  Coverage: {coverage:.1f}%")
        logger.info(f"  Processing rate: {self.grape_processor.performance_metrics.processing_rate:.1f} concepts/second")
        
        return mappings

def create_production_integration_config(omop_data_path: str, 
                                       umls_graph_path: str,
                                       output_path: str) -> Tuple[IntegrationConfig, ProductionConfig]:
    """Create optimized production configuration"""
    
    # OMOP processing optimized for production
    omop_config = OMOPConfig(
        chunk_size=250000,  # Large chunks for efficiency
        max_workers=min(mp.cpu_count(), 16),
        memory_limit_gb=32.0,
        enable_parallel=True,
        cache_results=True,
        output_format='pickle'
    )
    
    # Mapping configuration optimized for accuracy and speed
    mapping_config = MappingConfig(
        similarity_threshold=0.7,
        confidence_threshold=0.8,
        max_candidates=20,  # More candidates for better matches
        enable_fuzzy_matching=True,
        enable_semantic_similarity=True,
        enable_hierarchical_mapping=True,
        batch_size=5000  # Larger batches
    )
    
    # Integration configuration
    integration_config = IntegrationConfig(
        omop_data_path=omop_data_path,
        umls_graph_path=umls_graph_path,
        output_path=output_path,
        omop_config=omop_config,
        mapping_config=mapping_config,
        create_unified_graph=True,
        generate_crosswalk_tables=True,
        enable_validation=True,
        save_intermediate_results=True,
        memory_limit_gb=32.0,
        max_workers=min(mp.cpu_count(), 16)
    )
    
    # Production-specific configuration
    production_config = ProductionConfig(
        chunk_size=250000,
        max_workers=min(mp.cpu_count(), 16),
        memory_limit_gb=32.0,
        enable_semantic_caching=True,
        semantic_cache_size=200000,
        enable_hierarchical_pruning=True,
        enable_parallel_chunking=True,
        enable_memory_mapping=True,
        enable_graph_compression=True,
        use_database_backend=False,  # Enable for very large datasets
        enable_incremental_validation=True,
        validation_sample_rate=0.1,
        enable_performance_monitoring=True,
        monitoring_interval=30.0
    )
    
    return integration_config, production_config

def main():
    """Example production integration"""
    
    # Production paths (update with your actual paths)
    omop_data_path = "/path/to/production/omop/cdm/data"
    umls_graph_path = "/path/to/production/umls/knowledge/graph"
    output_path = "/path/to/production/output"
    
    # Create production configuration
    integration_config, production_config = create_production_integration_config(
        omop_data_path, umls_graph_path, output_path
    )
    
    # Initialize production integrator
    integrator = ProductionOMOPUMLSIntegrator(integration_config, production_config)
    
    try:
        logger.info("Starting production OMOP-UMLS integration...")
        
        # Run production integration
        results = integrator.run_production_integration()
        
        # Log final results
        logger.info("="*80)
        logger.info("PRODUCTION INTEGRATION COMPLETE")
        logger.info("="*80)
        
        production_metrics = results.get('production_metrics', {})
        logger.info(f"Concepts processed: {production_metrics.get('concepts_processed', 0):,}")
        logger.info(f"Processing rate: {production_metrics.get('processing_rate', 0):.1f} concepts/second")
        logger.info(f"Peak memory usage: {production_metrics.get('memory_peak', 0):.2f} GB")
        logger.info(f"Processing time: {production_metrics.get('processing_time', 0):.2f} seconds")
        logger.info(f"Cache hit rate: {production_metrics.get('cache_hit_rate', 0):.1%}")
        
        return results
        
    except Exception as e:
        logger.error(f"Production integration failed: {e}")
        raise

if __name__ == "__main__":
    main()
