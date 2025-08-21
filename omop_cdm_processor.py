#!/usr/bin/env python3
"""
OMOP CDM 5.4 Data Processor
Integrates OMOP Common Data Model version 5.4 with existing UMLS knowledge graph infrastructure
Built on GRAPE-style optimization principles for memory efficiency and performance
"""

import pandas as pd
import numpy as np
import os
import sys
import json
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Generator
from pathlib import Path
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import psutil
import gc
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('omop_cdm_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class OMOPConfig:
    """Configuration for OMOP CDM processing"""
    chunk_size: int = 50000
    max_workers: int = mp.cpu_count()
    memory_limit_gb: float = 8.0
    enable_parallel: bool = True
    cache_results: bool = True
    output_format: str = 'pickle'  # 'pickle', 'json', 'csv'
    quality_threshold: float = 0.8
    
class MemoryManager:
    """GRAPE-style memory management for large-scale processing"""
    
    def __init__(self, memory_limit_gb: float = 8.0):
        self.memory_limit_bytes = memory_limit_gb * 1024**3
        self.process = psutil.Process()
        
    def check_memory_usage(self) -> float:
        """Check current memory usage in GB"""
        memory_info = self.process.memory_info()
        return memory_info.rss / (1024**3)
    
    def is_memory_available(self, required_gb: float = 1.0) -> bool:
        """Check if sufficient memory is available"""
        current_usage = self.check_memory_usage()
        return (current_usage + required_gb) < (self.memory_limit_bytes / 1024**3)
    
    def force_garbage_collection(self):
        """Force garbage collection to free memory"""
        gc.collect()
        logger.info(f"Memory after GC: {self.check_memory_usage():.2f} GB")

class OMOPDataProcessor:
    """
    Main processor for OMOP CDM 5.4 data
    Implements memory-efficient processing with GRAPE-style optimization
    """
    
    def __init__(self, omop_data_path: str, config: OMOPConfig = None):
        self.omop_data_path = Path(omop_data_path)
        self.config = config or OMOPConfig()
        self.memory_manager = MemoryManager(self.config.memory_limit_gb)
        
        # OMOP CDM 5.4 table definitions
        self.omop_tables = {
            'CONCEPT': 'CONCEPT.csv',
            'CONCEPT_RELATIONSHIP': 'CONCEPT_RELATIONSHIP.csv', 
            'CONCEPT_ANCESTOR': 'CONCEPT_ANCESTOR.csv',
            'CONCEPT_SYNONYM': 'CONCEPT_SYNONYM.csv',
            'VOCABULARY': 'VOCABULARY.csv',
            'DOMAIN': 'DOMAIN.csv',
            'CONCEPT_CLASS': 'CONCEPT_CLASS.csv'
        }
        
        # Processing statistics
        self.processing_stats = {
            'start_time': None,
            'end_time': None,
            'tables_processed': 0,
            'concepts_processed': 0,
            'relationships_processed': 0,
            'memory_peak': 0.0,
            'errors': []
        }
        
        logger.info(f"Initialized OMOP CDM 5.4 Processor")
        logger.info(f"Data path: {self.omop_data_path}")
        logger.info(f"Config: {self.config}")
    
    def validate_data_files(self) -> Dict[str, bool]:
        """Validate that required OMOP data files exist"""
        validation_results = {}
        
        for table_name, filename in self.omop_tables.items():
            file_path = self.omop_data_path / filename
            exists = file_path.exists()
            validation_results[table_name] = exists
            
            if exists:
                file_size = file_path.stat().st_size / (1024**2)  # MB
                logger.info(f"✅ {table_name}: {filename} ({file_size:.1f} MB)")
            else:
                logger.warning(f"❌ {table_name}: {filename} not found")
                
        return validation_results
    
    def load_table_chunked(self, table_name: str) -> Generator[pd.DataFrame, None, None]:
        """
        Load OMOP table in memory-efficient chunks
        Implements GRAPE-style chunked processing
        """
        file_path = self.omop_data_path / self.omop_tables[table_name]
        
        if not file_path.exists():
            raise FileNotFoundError(f"OMOP table file not found: {file_path}")
        
        logger.info(f"Loading {table_name} in chunks of {self.config.chunk_size}")
        
        try:
            # Use pandas chunking for memory efficiency
            chunk_reader = pd.read_csv(
                file_path,
                sep='\t',  # OMOP files are typically tab-separated
                chunksize=self.config.chunk_size,
                low_memory=True,
                dtype=str  # Load as strings initially for safety
            )
            
            chunk_count = 0
            for chunk in chunk_reader:
                chunk_count += 1
                
                # Memory check before processing chunk
                if not self.memory_manager.is_memory_available(1.0):
                    logger.warning("Memory threshold reached, forcing garbage collection")
                    self.memory_manager.force_garbage_collection()
                
                # Clean and standardize chunk
                chunk = self.clean_chunk_data(chunk, table_name)
                
                logger.debug(f"Processed chunk {chunk_count} of {table_name}: {len(chunk)} records")
                yield chunk
                
        except Exception as e:
            error_msg = f"Error loading {table_name}: {str(e)}"
            logger.error(error_msg)
            self.processing_stats['errors'].append(error_msg)
            raise
    
    def clean_chunk_data(self, chunk: pd.DataFrame, table_name: str) -> pd.DataFrame:
        """Clean and standardize chunk data"""
        
        # Remove rows with missing critical identifiers
        if table_name == 'CONCEPT':
            chunk = chunk.dropna(subset=['concept_id', 'concept_name'])
            # Convert concept_id to int where possible
            chunk['concept_id'] = pd.to_numeric(chunk['concept_id'], errors='coerce')
            chunk = chunk.dropna(subset=['concept_id'])
            
        elif table_name == 'CONCEPT_RELATIONSHIP':
            chunk = chunk.dropna(subset=['concept_id_1', 'concept_id_2', 'relationship_id'])
            chunk['concept_id_1'] = pd.to_numeric(chunk['concept_id_1'], errors='coerce')
            chunk['concept_id_2'] = pd.to_numeric(chunk['concept_id_2'], errors='coerce')
            chunk = chunk.dropna(subset=['concept_id_1', 'concept_id_2'])
        
        # Standardize text fields
        text_columns = chunk.select_dtypes(include=['object']).columns
        for col in text_columns:
            if col in chunk.columns:
                chunk[col] = chunk[col].astype(str).str.strip()
                # Replace empty strings with NaN
                chunk[col] = chunk[col].replace('', np.nan)
        
        return chunk
    
    def process_concept_table(self) -> Dict:
        """
        Process OMOP CONCEPT table (~6M concepts)
        Extract key concept information for UMLS mapping
        """
        logger.info("Processing OMOP CONCEPT table")
        
        concept_data = {
            'concepts': [],
            'vocabularies': set(),
            'domains': set(),
            'concept_classes': set(),
            'processing_stats': {
                'total_concepts': 0,
                'standard_concepts': 0,
                'valid_concepts': 0
            }
        }
        
        try:
            for chunk in self.load_table_chunked('CONCEPT'):
                # Process each concept in the chunk
                for _, concept in chunk.iterrows():
                    concept_info = {
                        'concept_id': int(concept['concept_id']),
                        'concept_name': concept['concept_name'],
                        'domain_id': concept.get('domain_id', ''),
                        'vocabulary_id': concept.get('vocabulary_id', ''),
                        'concept_class_id': concept.get('concept_class_id', ''),
                        'standard_concept': concept.get('standard_concept', ''),
                        'concept_code': concept.get('concept_code', ''),
                        'valid_start_date': concept.get('valid_start_date', ''),
                        'valid_end_date': concept.get('valid_end_date', ''),
                        'invalid_reason': concept.get('invalid_reason', '')
                    }
                    
                    concept_data['concepts'].append(concept_info)
                    concept_data['vocabularies'].add(concept.get('vocabulary_id', ''))
                    concept_data['domains'].add(concept.get('domain_id', ''))
                    concept_data['concept_classes'].add(concept.get('concept_class_id', ''))
                    
                    # Update statistics
                    concept_data['processing_stats']['total_concepts'] += 1
                    if concept.get('standard_concept') == 'S':
                        concept_data['processing_stats']['standard_concepts'] += 1
                    if concept.get('invalid_reason', '') == '':
                        concept_data['processing_stats']['valid_concepts'] += 1
                
                # Memory management
                if len(concept_data['concepts']) % 100000 == 0:
                    logger.info(f"Processed {len(concept_data['concepts'])} concepts")
                    current_memory = self.memory_manager.check_memory_usage()
                    self.processing_stats['memory_peak'] = max(
                        self.processing_stats['memory_peak'], 
                        current_memory
                    )
        
        except Exception as e:
            error_msg = f"Error processing CONCEPT table: {str(e)}"
            logger.error(error_msg)
            self.processing_stats['errors'].append(error_msg)
            raise
        
        logger.info(f"CONCEPT table processing complete:")
        logger.info(f"  Total concepts: {concept_data['processing_stats']['total_concepts']:,}")
        logger.info(f"  Standard concepts: {concept_data['processing_stats']['standard_concepts']:,}")
        logger.info(f"  Valid concepts: {concept_data['processing_stats']['valid_concepts']:,}")
        logger.info(f"  Unique vocabularies: {len(concept_data['vocabularies'])}")
        logger.info(f"  Unique domains: {len(concept_data['domains'])}")
        
        return concept_data
    
    def process_relationship_table(self) -> Dict:
        """
        Process OMOP CONCEPT_RELATIONSHIP table (~50M relationships)
        Extract concept relationships for graph construction
        """
        logger.info("Processing OMOP CONCEPT_RELATIONSHIP table")
        
        relationship_data = {
            'relationships': [],
            'relationship_types': set(),
            'processing_stats': {
                'total_relationships': 0,
                'valid_relationships': 0
            }
        }
        
        try:
            for chunk in self.load_table_chunked('CONCEPT_RELATIONSHIP'):
                for _, rel in chunk.iterrows():
                    if pd.isna(rel['concept_id_1']) or pd.isna(rel['concept_id_2']):
                        continue
                        
                    relationship_info = {
                        'concept_id_1': int(rel['concept_id_1']),
                        'concept_id_2': int(rel['concept_id_2']),
                        'relationship_id': rel.get('relationship_id', ''),
                        'valid_start_date': rel.get('valid_start_date', ''),
                        'valid_end_date': rel.get('valid_end_date', ''),
                        'invalid_reason': rel.get('invalid_reason', '')
                    }
                    
                    relationship_data['relationships'].append(relationship_info)
                    relationship_data['relationship_types'].add(rel.get('relationship_id', ''))
                    
                    relationship_data['processing_stats']['total_relationships'] += 1
                    if rel.get('invalid_reason', '') == '':
                        relationship_data['processing_stats']['valid_relationships'] += 1
                
                # Progress logging
                if len(relationship_data['relationships']) % 500000 == 0:
                    logger.info(f"Processed {len(relationship_data['relationships'])} relationships")
        
        except Exception as e:
            error_msg = f"Error processing CONCEPT_RELATIONSHIP table: {str(e)}"
            logger.error(error_msg)
            self.processing_stats['errors'].append(error_msg)
            raise
        
        logger.info(f"CONCEPT_RELATIONSHIP table processing complete:")
        logger.info(f"  Total relationships: {relationship_data['processing_stats']['total_relationships']:,}")
        logger.info(f"  Valid relationships: {relationship_data['processing_stats']['valid_relationships']:,}")
        logger.info(f"  Unique relationship types: {len(relationship_data['relationship_types'])}")
        
        return relationship_data
    
    def process_vocabulary_metadata(self) -> Dict:
        """Process OMOP vocabulary metadata tables"""
        logger.info("Processing OMOP vocabulary metadata")
        
        metadata = {
            'vocabularies': {},
            'domains': {},
            'concept_classes': {}
        }
        
        # Process VOCABULARY table
        try:
            vocab_df = pd.read_csv(
                self.omop_data_path / 'VOCABULARY.csv',
                sep='\t',
                dtype=str
            )
            
            for _, vocab in vocab_df.iterrows():
                metadata['vocabularies'][vocab['vocabulary_id']] = {
                    'vocabulary_name': vocab.get('vocabulary_name', ''),
                    'vocabulary_reference': vocab.get('vocabulary_reference', ''),
                    'vocabulary_version': vocab.get('vocabulary_version', '')
                }
        except Exception as e:
            logger.warning(f"Could not process VOCABULARY table: {e}")
        
        # Process DOMAIN table
        try:
            domain_df = pd.read_csv(
                self.omop_data_path / 'DOMAIN.csv',
                sep='\t',
                dtype=str
            )
            
            for _, domain in domain_df.iterrows():
                metadata['domains'][domain['domain_id']] = {
                    'domain_name': domain.get('domain_name', ''),
                    'domain_concept_id': domain.get('domain_concept_id', '')
                }
        except Exception as e:
            logger.warning(f"Could not process DOMAIN table: {e}")
        
        # Process CONCEPT_CLASS table
        try:
            class_df = pd.read_csv(
                self.omop_data_path / 'CONCEPT_CLASS.csv',
                sep='\t',
                dtype=str
            )
            
            for _, concept_class in class_df.iterrows():
                metadata['concept_classes'][concept_class['concept_class_id']] = {
                    'concept_class_name': concept_class.get('concept_class_name', ''),
                    'concept_class_concept_id': concept_class.get('concept_class_concept_id', '')
                }
        except Exception as e:
            logger.warning(f"Could not process CONCEPT_CLASS table: {e}")
        
        logger.info(f"Vocabulary metadata processing complete:")
        logger.info(f"  Vocabularies: {len(metadata['vocabularies'])}")
        logger.info(f"  Domains: {len(metadata['domains'])}")
        logger.info(f"  Concept Classes: {len(metadata['concept_classes'])}")
        
        return metadata
    
    def extract_umls_mappings(self, concept_data: Dict) -> Dict:
        """
        Extract existing UMLS mappings from OMOP concepts
        Many OMOP concepts contain direct CUI references
        """
        logger.info("Extracting existing UMLS mappings from OMOP concepts")
        
        umls_mappings = {
            'direct_cui_mappings': {},
            'vocabulary_mappings': {},
            'statistics': {
                'concepts_with_cuis': 0,
                'umls_vocabulary_concepts': 0
            }
        }
        
        for concept in concept_data['concepts']:
            concept_id = concept['concept_id']
            vocabulary_id = concept['vocabulary_id']
            concept_code = concept['concept_code']
            
            # Check for UMLS vocabulary
            if vocabulary_id == 'UMLS':
                umls_mappings['vocabulary_mappings'][concept_id] = {
                    'concept_code': concept_code,
                    'concept_name': concept['concept_name']
                }
                umls_mappings['statistics']['umls_vocabulary_concepts'] += 1
            
            # Check for CUI patterns in concept codes
            if concept_code and concept_code.startswith('C') and len(concept_code) == 8:
                # Potential CUI format (C1234567)
                try:
                    int(concept_code[1:])  # Check if rest is numeric
                    umls_mappings['direct_cui_mappings'][concept_id] = concept_code
                    umls_mappings['statistics']['concepts_with_cuis'] += 1
                except ValueError:
                    pass
        
        logger.info(f"UMLS mapping extraction complete:")
        logger.info(f"  Direct CUI mappings: {umls_mappings['statistics']['concepts_with_cuis']:,}")
        logger.info(f"  UMLS vocabulary concepts: {umls_mappings['statistics']['umls_vocabulary_concepts']:,}")
        
        return umls_mappings
    
    def process_all_tables(self) -> Dict:
        """
        Process all OMOP CDM 5.4 tables
        Main entry point for complete processing
        """
        logger.info("Starting complete OMOP CDM 5.4 processing")
        self.processing_stats['start_time'] = datetime.now()
        
        # Validate data files first
        validation_results = self.validate_data_files()
        missing_files = [table for table, exists in validation_results.items() if not exists]
        
        if missing_files:
            logger.warning(f"Missing OMOP data files: {missing_files}")
        
        # Process core tables
        results = {
            'config': self.config,
            'validation_results': validation_results,
            'processing_stats': self.processing_stats
        }
        
        try:
            # Process CONCEPT table (core concepts)
            if validation_results.get('CONCEPT', False):
                results['concept_data'] = self.process_concept_table()
                self.processing_stats['tables_processed'] += 1
                
                # Extract UMLS mappings from concepts
                results['umls_mappings'] = self.extract_umls_mappings(results['concept_data'])
            
            # Process CONCEPT_RELATIONSHIP table (relationships)
            if validation_results.get('CONCEPT_RELATIONSHIP', False):
                results['relationship_data'] = self.process_relationship_table()
                self.processing_stats['tables_processed'] += 1
            
            # Process vocabulary metadata
            results['metadata'] = self.process_vocabulary_metadata()
            
        except Exception as e:
            error_msg = f"Error in complete processing: {str(e)}"
            logger.error(error_msg)
            self.processing_stats['errors'].append(error_msg)
            raise
        
        finally:
            self.processing_stats['end_time'] = datetime.now()
            processing_time = (
                self.processing_stats['end_time'] - 
                self.processing_stats['start_time']
            ).total_seconds()
            
            logger.info(f"OMOP CDM 5.4 processing complete:")
            logger.info(f"  Processing time: {processing_time:.2f} seconds")
            logger.info(f"  Tables processed: {self.processing_stats['tables_processed']}")
            logger.info(f"  Peak memory usage: {self.processing_stats['memory_peak']:.2f} GB")
            logger.info(f"  Errors: {len(self.processing_stats['errors'])}")
        
        return results
    
    def save_results(self, results: Dict, output_path: str):
        """Save processing results to disk"""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if self.config.output_format == 'pickle':
            with open(output_path / 'omop_cdm_processed.pkl', 'wb') as f:
                pickle.dump(results, f)
            logger.info(f"Results saved to {output_path / 'omop_cdm_processed.pkl'}")
            
        elif self.config.output_format == 'json':
            # Convert non-serializable objects to serializable format
            json_results = self._prepare_for_json(results)
            with open(output_path / 'omop_cdm_processed.json', 'w') as f:
                json.dump(json_results, f, indent=2, default=str)
            logger.info(f"Results saved to {output_path / 'omop_cdm_processed.json'}")
    
    def _prepare_for_json(self, obj):
        """Prepare object for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._prepare_for_json(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return str(obj)
        else:
            return obj

def main():
    """Example usage of OMOP CDM processor"""
    
    # Configuration
    config = OMOPConfig(
        chunk_size=50000,
        max_workers=mp.cpu_count(),
        memory_limit_gb=8.0,
        enable_parallel=True,
        cache_results=True,
        output_format='pickle'
    )
    
    # Initialize processor
    omop_data_path = "/path/to/omop/cdm/data"  # Update with actual path
    processor = OMOPDataProcessor(omop_data_path, config)
    
    # Process all tables
    try:
        results = processor.process_all_tables()
        
        # Save results
        output_path = "/path/to/output"  # Update with actual output path
        processor.save_results(results, output_path)
        
        # Print summary
        print("\n" + "="*60)
        print("OMOP CDM 5.4 PROCESSING SUMMARY")
        print("="*60)
        
        if 'concept_data' in results:
            concept_stats = results['concept_data']['processing_stats']
            print(f"Concepts processed: {concept_stats['total_concepts']:,}")
            print(f"Standard concepts: {concept_stats['standard_concepts']:,}")
            print(f"Valid concepts: {concept_stats['valid_concepts']:,}")
        
        if 'relationship_data' in results:
            rel_stats = results['relationship_data']['processing_stats']
            print(f"Relationships processed: {rel_stats['total_relationships']:,}")
            print(f"Valid relationships: {rel_stats['valid_relationships']:,}")
        
        if 'umls_mappings' in results:
            umls_stats = results['umls_mappings']['statistics']
            print(f"Direct CUI mappings: {umls_stats['concepts_with_cuis']:,}")
            print(f"UMLS vocabulary concepts: {umls_stats['umls_vocabulary_concepts']:,}")
        
        processing_time = (
            results['processing_stats']['end_time'] - 
            results['processing_stats']['start_time']
        ).total_seconds()
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Peak memory usage: {results['processing_stats']['memory_peak']:.2f} GB")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
