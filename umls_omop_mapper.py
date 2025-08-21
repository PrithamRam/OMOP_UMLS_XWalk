#!/usr/bin/env python3
"""
UMLS-OMOP Mapping Engine
Connects OMOP CDM 5.4 concepts to existing UMLS knowledge graph infrastructure
Implements semantic similarity and confidence scoring for cross-ontology alignment
"""

import pandas as pd
import numpy as np
import pickle
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import re
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MappingConfig:
    """Configuration for UMLS-OMOP mapping"""
    similarity_threshold: float = 0.7
    confidence_threshold: float = 0.8
    max_candidates: int = 10
    enable_fuzzy_matching: bool = True
    enable_semantic_similarity: bool = True
    enable_hierarchical_mapping: bool = True
    batch_size: int = 1000

@dataclass
class MappingResult:
    """Result of concept mapping"""
    omop_concept_id: int
    umls_cui: str
    mapping_type: str  # 'direct', 'exact_match', 'fuzzy_match', 'semantic'
    confidence_score: float
    similarity_score: float
    evidence: Dict
    
class UMLSOMOPMapper:
    """
    Maps OMOP concepts to UMLS concepts using multiple strategies
    Integrates with existing UMLS knowledge graph infrastructure
    """
    
    def __init__(self, umls_graph_path: str, config: MappingConfig = None):
        self.config = config or MappingConfig()
        self.umls_graph_path = Path(umls_graph_path)
        
        # Will be loaded from existing UMLS infrastructure
        self.umls_concepts = {}
        self.umls_graph = None
        self.concept_embeddings = None
        self.tfidf_vectorizer = None
        
        # Mapping results storage
        self.mappings = {}
        self.mapping_statistics = {
            'total_omop_concepts': 0,
            'mapped_concepts': 0,
            'direct_mappings': 0,
            'exact_matches': 0,
            'fuzzy_matches': 0,
            'semantic_matches': 0,
            'unmapped_concepts': 0,
            'high_confidence_mappings': 0
        }
        
        logger.info("Initialized UMLS-OMOP Mapper")
    
    def load_umls_infrastructure(self):
        """
        Load existing UMLS knowledge graph and infrastructure
        Connects to your existing 3.4M concept UMLS system
        """
        logger.info("Loading existing UMLS knowledge graph infrastructure")
        
        try:
            # Load UMLS concepts (adapt to your existing format)
            umls_concepts_path = self.umls_graph_path / 'umls_concepts.pkl'
            if umls_concepts_path.exists():
                with open(umls_concepts_path, 'rb') as f:
                    self.umls_concepts = pickle.load(f)
                logger.info(f"Loaded {len(self.umls_concepts):,} UMLS concepts")
            
            # Load UMLS graph (adapt to your existing format)
            umls_graph_path = self.umls_graph_path / 'umls_knowledge_graph.pkl'
            if umls_graph_path.exists():
                with open(umls_graph_path, 'rb') as f:
                    self.umls_graph = pickle.load(f)
                logger.info(f"Loaded UMLS knowledge graph with {self.umls_graph.number_of_nodes():,} nodes")
            
            # Load or create TF-IDF embeddings
            self._initialize_semantic_similarity()
            
        except Exception as e:
            logger.error(f"Error loading UMLS infrastructure: {e}")
            # Create minimal infrastructure if files don't exist
            self._create_minimal_infrastructure()
    
    def _create_minimal_infrastructure(self):
        """Create minimal infrastructure for testing if full UMLS data not available"""
        logger.warning("Creating minimal UMLS infrastructure for testing")
        
        # Create sample UMLS concepts for testing
        sample_concepts = {
            'C0000005': {
                'cui': 'C0000005',
                'preferred_name': '(1->4)-alpha-D-Glucan',
                'semantic_types': ['T109'],
                'definitions': ['A polysaccharide consisting of glucose units'],
                'synonyms': ['alpha-D-Glucan', 'Glucan']
            },
            'C0000039': {
                'cui': 'C0000039', 
                'preferred_name': '1,2-Dipalmitoylphosphatidylcholine',
                'semantic_types': ['T109'],
                'definitions': ['A phosphatidylcholine molecule'],
                'synonyms': ['DPPC', 'Dipalmitoylphosphatidylcholine']
            }
        }
        
        self.umls_concepts = sample_concepts
        self.umls_graph = nx.Graph()
        
        # Add sample nodes to graph
        for cui, concept_data in sample_concepts.items():
            self.umls_graph.add_node(cui, **concept_data)
    
    def _initialize_semantic_similarity(self):
        """Initialize TF-IDF vectorizer for semantic similarity"""
        logger.info("Initializing semantic similarity system")
        
        # Prepare text corpus from UMLS concepts
        corpus = []
        concept_ids = []
        
        for cui, concept_data in self.umls_concepts.items():
            # Combine preferred name, definitions, and synonyms
            text_parts = [concept_data.get('preferred_name', '')]
            
            if 'definitions' in concept_data:
                text_parts.extend(concept_data['definitions'])
            
            if 'synonyms' in concept_data:
                text_parts.extend(concept_data['synonyms'])
            
            combined_text = ' '.join(text_parts).lower()
            corpus.append(combined_text)
            concept_ids.append(cui)
        
        if corpus:
            # Create TF-IDF vectorizer
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words='english',
                ngram_range=(1, 2)
            )
            
            # Fit and transform corpus
            self.concept_embeddings = self.tfidf_vectorizer.fit_transform(corpus)
            self.concept_ids_ordered = concept_ids
            
            logger.info(f"Created TF-IDF embeddings for {len(corpus):,} UMLS concepts")
        else:
            logger.warning("No UMLS concepts available for semantic similarity")
    
    def find_direct_cui_mappings(self, omop_concepts: List[Dict]) -> Dict:
        """
        Find OMOP concepts that already contain direct CUI references
        This handles existing mappings in OMOP data
        """
        logger.info("Finding direct CUI mappings in OMOP concepts")
        
        direct_mappings = {}
        
        for concept in omop_concepts:
            concept_id = concept['concept_id']
            concept_code = concept.get('concept_code', '')
            vocabulary_id = concept.get('vocabulary_id', '')
            
            # Check for UMLS vocabulary concepts
            if vocabulary_id == 'UMLS':
                if concept_code in self.umls_concepts:
                    direct_mappings[concept_id] = MappingResult(
                        omop_concept_id=concept_id,
                        umls_cui=concept_code,
                        mapping_type='direct',
                        confidence_score=1.0,
                        similarity_score=1.0,
                        evidence={
                            'vocabulary': 'UMLS',
                            'concept_code': concept_code,
                            'method': 'direct_vocabulary_mapping'
                        }
                    )
                    self.mapping_statistics['direct_mappings'] += 1
            
            # Check for CUI-like patterns in concept codes
            elif self._is_cui_pattern(concept_code):
                if concept_code in self.umls_concepts:
                    direct_mappings[concept_id] = MappingResult(
                        omop_concept_id=concept_id,
                        umls_cui=concept_code,
                        mapping_type='direct',
                        confidence_score=0.95,
                        similarity_score=1.0,
                        evidence={
                            'concept_code': concept_code,
                            'method': 'cui_pattern_matching'
                        }
                    )
                    self.mapping_statistics['direct_mappings'] += 1
        
        logger.info(f"Found {len(direct_mappings):,} direct CUI mappings")
        return direct_mappings
    
    def _is_cui_pattern(self, code: str) -> bool:
        """Check if a code matches CUI pattern (C followed by 7 digits)"""
        if not code or len(code) != 8:
            return False
        return bool(re.match(r'^C\d{7}$', code))
    
    def find_exact_string_matches(self, omop_concepts: List[Dict]) -> Dict:
        """Find exact string matches between OMOP and UMLS concept names"""
        logger.info("Finding exact string matches")
        
        exact_matches = {}
        
        # Create lookup dictionary for UMLS concepts by name
        umls_name_lookup = {}
        for cui, concept_data in self.umls_concepts.items():
            preferred_name = concept_data.get('preferred_name', '').lower().strip()
            if preferred_name:
                if preferred_name not in umls_name_lookup:
                    umls_name_lookup[preferred_name] = []
                umls_name_lookup[preferred_name].append(cui)
            
            # Also index synonyms
            synonyms = concept_data.get('synonyms', [])
            for synonym in synonyms:
                synonym_clean = synonym.lower().strip()
                if synonym_clean:
                    if synonym_clean not in umls_name_lookup:
                        umls_name_lookup[synonym_clean] = []
                    umls_name_lookup[synonym_clean].append(cui)
        
        # Match OMOP concepts
        for concept in omop_concepts:
            concept_id = concept['concept_id']
            concept_name = concept.get('concept_name', '').lower().strip()
            
            if concept_name in umls_name_lookup:
                # If multiple CUIs match, take the first one (could be improved)
                matched_cui = umls_name_lookup[concept_name][0]
                
                exact_matches[concept_id] = MappingResult(
                    omop_concept_id=concept_id,
                    umls_cui=matched_cui,
                    mapping_type='exact_match',
                    confidence_score=0.9,
                    similarity_score=1.0,
                    evidence={
                        'omop_name': concept['concept_name'],
                        'umls_name': self.umls_concepts[matched_cui]['preferred_name'],
                        'method': 'exact_string_match'
                    }
                )
                self.mapping_statistics['exact_matches'] += 1
        
        logger.info(f"Found {len(exact_matches):,} exact string matches")
        return exact_matches
    
    def find_fuzzy_string_matches(self, omop_concepts: List[Dict], 
                                 already_mapped: Set[int]) -> Dict:
        """Find fuzzy string matches using sequence similarity"""
        logger.info("Finding fuzzy string matches")
        
        fuzzy_matches = {}
        
        # Get unmapped OMOP concepts
        unmapped_concepts = [c for c in omop_concepts 
                           if c['concept_id'] not in already_mapped]
        
        for concept in unmapped_concepts:
            concept_id = concept['concept_id']
            concept_name = concept.get('concept_name', '').lower().strip()
            
            if not concept_name:
                continue
            
            best_match = None
            best_similarity = 0.0
            
            # Compare with all UMLS concepts (could be optimized)
            for cui, concept_data in self.umls_concepts.items():
                umls_name = concept_data.get('preferred_name', '').lower().strip()
                
                if umls_name:
                    similarity = SequenceMatcher(None, concept_name, umls_name).ratio()
                    
                    if similarity > best_similarity and similarity >= self.config.similarity_threshold:
                        best_similarity = similarity
                        best_match = cui
                
                # Also check synonyms
                synonyms = concept_data.get('synonyms', [])
                for synonym in synonyms:
                    synonym_clean = synonym.lower().strip()
                    similarity = SequenceMatcher(None, concept_name, synonym_clean).ratio()
                    
                    if similarity > best_similarity and similarity >= self.config.similarity_threshold:
                        best_similarity = similarity
                        best_match = cui
            
            if best_match:
                confidence_score = min(best_similarity * 0.8, 0.85)  # Lower confidence for fuzzy
                
                fuzzy_matches[concept_id] = MappingResult(
                    omop_concept_id=concept_id,
                    umls_cui=best_match,
                    mapping_type='fuzzy_match',
                    confidence_score=confidence_score,
                    similarity_score=best_similarity,
                    evidence={
                        'omop_name': concept['concept_name'],
                        'umls_name': self.umls_concepts[best_match]['preferred_name'],
                        'similarity_score': best_similarity,
                        'method': 'fuzzy_string_match'
                    }
                )
                self.mapping_statistics['fuzzy_matches'] += 1
        
        logger.info(f"Found {len(fuzzy_matches):,} fuzzy string matches")
        return fuzzy_matches
    
    def find_semantic_similarity_matches(self, omop_concepts: List[Dict],
                                       already_mapped: Set[int]) -> Dict:
        """Find matches using semantic similarity (TF-IDF + cosine similarity)"""
        logger.info("Finding semantic similarity matches")
        
        if not self.tfidf_vectorizer or self.concept_embeddings is None:
            logger.warning("Semantic similarity not available - TF-IDF not initialized")
            return {}
        
        semantic_matches = {}
        
        # Get unmapped OMOP concepts
        unmapped_concepts = [c for c in omop_concepts 
                           if c['concept_id'] not in already_mapped]
        
        for concept in unmapped_concepts:
            concept_id = concept['concept_id']
            concept_name = concept.get('concept_name', '')
            
            if not concept_name:
                continue
            
            # Transform OMOP concept name to TF-IDF vector
            try:
                omop_vector = self.tfidf_vectorizer.transform([concept_name.lower()])
                
                # Calculate cosine similarity with all UMLS concepts
                similarities = cosine_similarity(omop_vector, self.concept_embeddings).flatten()
                
                # Find best matches
                best_indices = np.argsort(similarities)[::-1][:self.config.max_candidates]
                
                for idx in best_indices:
                    similarity_score = similarities[idx]
                    
                    if similarity_score >= self.config.similarity_threshold:
                        matched_cui = self.concept_ids_ordered[idx]
                        confidence_score = min(similarity_score * 0.7, 0.8)  # Lower confidence for semantic
                        
                        semantic_matches[concept_id] = MappingResult(
                            omop_concept_id=concept_id,
                            umls_cui=matched_cui,
                            mapping_type='semantic',
                            confidence_score=confidence_score,
                            similarity_score=similarity_score,
                            evidence={
                                'omop_name': concept_name,
                                'umls_name': self.umls_concepts[matched_cui]['preferred_name'],
                                'similarity_score': similarity_score,
                                'method': 'semantic_similarity_tfidf'
                            }
                        )
                        self.mapping_statistics['semantic_matches'] += 1
                        break  # Take only the best match
                        
            except Exception as e:
                logger.debug(f"Error in semantic matching for concept {concept_id}: {e}")
                continue
        
        logger.info(f"Found {len(semantic_matches):,} semantic similarity matches")
        return semantic_matches
    
    def calculate_mapping_confidence(self, mapping_result: MappingResult) -> float:
        """
        Calculate overall confidence score for a mapping
        Combines multiple evidence factors
        """
        base_confidence = mapping_result.confidence_score
        
        # Adjust based on mapping type
        type_multipliers = {
            'direct': 1.0,
            'exact_match': 0.95,
            'fuzzy_match': 0.8,
            'semantic': 0.7
        }
        
        type_multiplier = type_multipliers.get(mapping_result.mapping_type, 0.5)
        
        # Adjust based on similarity score
        similarity_bonus = min(mapping_result.similarity_score * 0.1, 0.1)
        
        final_confidence = min(base_confidence * type_multiplier + similarity_bonus, 1.0)
        
        return final_confidence
    
    def map_omop_to_umls(self, omop_concepts: List[Dict]) -> Dict:
        """
        Main mapping function - maps OMOP concepts to UMLS using multiple strategies
        """
        logger.info(f"Starting UMLS-OMOP mapping for {len(omop_concepts):,} concepts")
        self.mapping_statistics['total_omop_concepts'] = len(omop_concepts)
        
        all_mappings = {}
        mapped_concept_ids = set()
        
        # Strategy 1: Direct CUI mappings
        if self.umls_concepts:
            direct_mappings = self.find_direct_cui_mappings(omop_concepts)
            all_mappings.update(direct_mappings)
            mapped_concept_ids.update(direct_mappings.keys())
        
        # Strategy 2: Exact string matches
        exact_matches = self.find_exact_string_matches(omop_concepts)
        # Only add if not already mapped
        for concept_id, mapping in exact_matches.items():
            if concept_id not in mapped_concept_ids:
                all_mappings[concept_id] = mapping
                mapped_concept_ids.add(concept_id)
        
        # Strategy 3: Fuzzy string matches
        if self.config.enable_fuzzy_matching:
            fuzzy_matches = self.find_fuzzy_string_matches(omop_concepts, mapped_concept_ids)
            for concept_id, mapping in fuzzy_matches.items():
                if concept_id not in mapped_concept_ids:
                    all_mappings[concept_id] = mapping
                    mapped_concept_ids.add(concept_id)
        
        # Strategy 4: Semantic similarity matches
        if self.config.enable_semantic_similarity:
            semantic_matches = self.find_semantic_similarity_matches(omop_concepts, mapped_concept_ids)
            for concept_id, mapping in semantic_matches.items():
                if concept_id not in mapped_concept_ids:
                    all_mappings[concept_id] = mapping
                    mapped_concept_ids.add(concept_id)
        
        # Update final statistics
        self.mapping_statistics['mapped_concepts'] = len(all_mappings)
        self.mapping_statistics['unmapped_concepts'] = len(omop_concepts) - len(all_mappings)
        
        # Count high confidence mappings
        high_confidence_count = sum(
            1 for mapping in all_mappings.values() 
            if mapping.confidence_score >= self.config.confidence_threshold
        )
        self.mapping_statistics['high_confidence_mappings'] = high_confidence_count
        
        logger.info("UMLS-OMOP mapping complete:")
        logger.info(f"  Total concepts: {self.mapping_statistics['total_omop_concepts']:,}")
        logger.info(f"  Mapped concepts: {self.mapping_statistics['mapped_concepts']:,}")
        logger.info(f"  Unmapped concepts: {self.mapping_statistics['unmapped_concepts']:,}")
        logger.info(f"  Coverage: {(self.mapping_statistics['mapped_concepts'] / self.mapping_statistics['total_omop_concepts'] * 100):.1f}%")
        logger.info(f"  High confidence mappings: {high_confidence_count:,}")
        
        return all_mappings
    
    def generate_mapping_report(self, mappings: Dict) -> Dict:
        """Generate comprehensive mapping report"""
        
        report = {
            'summary': self.mapping_statistics.copy(),
            'mapping_types': {
                'direct': self.mapping_statistics['direct_mappings'],
                'exact_match': self.mapping_statistics['exact_matches'], 
                'fuzzy_match': self.mapping_statistics['fuzzy_matches'],
                'semantic': self.mapping_statistics['semantic_matches']
            },
            'confidence_distribution': {},
            'sample_mappings': {},
            'quality_metrics': {}
        }
        
        # Confidence distribution
        confidence_ranges = [(0.0, 0.5), (0.5, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        for low, high in confidence_ranges:
            count = sum(
                1 for mapping in mappings.values()
                if low <= mapping.confidence_score < high
            )
            report['confidence_distribution'][f"{low}-{high}"] = count
        
        # Sample mappings for each type
        for mapping_type in ['direct', 'exact_match', 'fuzzy_match', 'semantic']:
            samples = [
                {
                    'omop_concept_id': m.omop_concept_id,
                    'umls_cui': m.umls_cui,
                    'confidence_score': m.confidence_score,
                    'similarity_score': m.similarity_score,
                    'evidence': m.evidence
                }
                for m in mappings.values()
                if m.mapping_type == mapping_type
            ][:5]  # Top 5 samples
            
            report['sample_mappings'][mapping_type] = samples
        
        # Quality metrics
        if mappings:
            confidences = [m.confidence_score for m in mappings.values()]
            similarities = [m.similarity_score for m in mappings.values()]
            
            report['quality_metrics'] = {
                'average_confidence': np.mean(confidences),
                'median_confidence': np.median(confidences),
                'average_similarity': np.mean(similarities),
                'median_similarity': np.median(similarities),
                'high_quality_percentage': (
                    sum(1 for c in confidences if c >= 0.8) / len(confidences) * 100
                )
            }
        
        return report
    
    def save_mappings(self, mappings: Dict, output_path: str):
        """Save mapping results to disk"""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save full mapping results
        with open(output_path / 'umls_omop_mappings.pkl', 'wb') as f:
            pickle.dump(mappings, f)
        
        # Save mapping report
        report = self.generate_mapping_report(mappings)
        with open(output_path / 'mapping_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Save CSV format for easy inspection
        mapping_records = []
        for mapping in mappings.values():
            mapping_records.append({
                'omop_concept_id': mapping.omop_concept_id,
                'umls_cui': mapping.umls_cui,
                'mapping_type': mapping.mapping_type,
                'confidence_score': mapping.confidence_score,
                'similarity_score': mapping.similarity_score,
                'omop_name': mapping.evidence.get('omop_name', ''),
                'umls_name': mapping.evidence.get('umls_name', ''),
                'method': mapping.evidence.get('method', '')
            })
        
        df = pd.DataFrame(mapping_records)
        df.to_csv(output_path / 'umls_omop_mappings.csv', index=False)
        
        logger.info(f"Mappings saved to {output_path}")

def main():
    """Example usage of UMLS-OMOP mapper"""
    
    # Configuration
    config = MappingConfig(
        similarity_threshold=0.7,
        confidence_threshold=0.8,
        max_candidates=10,
        enable_fuzzy_matching=True,
        enable_semantic_similarity=True
    )
    
    # Initialize mapper
    umls_graph_path = "/path/to/umls/knowledge/graph"  # Update with actual path
    mapper = UMLSOMOPMapper(umls_graph_path, config)
    
    # Load UMLS infrastructure
    mapper.load_umls_infrastructure()
    
    # Example OMOP concepts (would come from OMOP processor)
    sample_omop_concepts = [
        {
            'concept_id': 1234567,
            'concept_name': 'Type 2 diabetes mellitus',
            'vocabulary_id': 'SNOMED',
            'concept_code': '44054006'
        },
        {
            'concept_id': 2345678,
            'concept_name': 'Hypertension',
            'vocabulary_id': 'ICD10CM',
            'concept_code': 'I10'
        }
    ]
    
    # Perform mapping
    mappings = mapper.map_omop_to_umls(sample_omop_concepts)
    
    # Generate and save results
    output_path = "/path/to/output"  # Update with actual output path
    mapper.save_mappings(mappings, output_path)
    
    # Print summary
    report = mapper.generate_mapping_report(mappings)
    print("\n" + "="*60)
    print("UMLS-OMOP MAPPING SUMMARY")
    print("="*60)
    print(f"Total concepts: {report['summary']['total_omop_concepts']:,}")
    print(f"Mapped concepts: {report['summary']['mapped_concepts']:,}")
    print(f"Coverage: {(report['summary']['mapped_concepts'] / report['summary']['total_omop_concepts'] * 100):.1f}%")
    print(f"High confidence: {report['summary']['high_confidence_mappings']:,}")
    
    if 'quality_metrics' in report:
        print(f"Average confidence: {report['quality_metrics']['average_confidence']:.3f}")
        print(f"High quality percentage: {report['quality_metrics']['high_quality_percentage']:.1f}%")

if __name__ == "__main__":
    main()
