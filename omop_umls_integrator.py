#!/usr/bin/env python3
"""
OMOP-UMLS Integration System
Main orchestrator that combines OMOP CDM 5.4 processing with UMLS knowledge graph
Creates unified crosswalk system with comprehensive mapping and validation
"""

import os
import sys
import json
import pickle
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import networkx as nx
from dataclasses import dataclass

# Import our custom modules
from omop_cdm_processor import OMOPDataProcessor, OMOPConfig
from umls_omop_mapper import UMLSOMOPMapper, MappingConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('omop_umls_integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for complete OMOP-UMLS integration"""
    # Data paths
    omop_data_path: str
    umls_graph_path: str
    output_path: str
    
    # Processing configuration
    omop_config: OMOPConfig
    mapping_config: MappingConfig
    
    # Integration options
    create_unified_graph: bool = True
    generate_crosswalk_tables: bool = True
    enable_validation: bool = True
    save_intermediate_results: bool = True
    
    # Performance settings
    memory_limit_gb: float = 8.0
    max_workers: int = 4

class OMOPUMLSIntegrator:
    """
    Main integration system that orchestrates OMOP CDM 5.4 and UMLS integration
    Builds upon existing UMLS infrastructure to create comprehensive crosswalk
    """
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.output_path = Path(config.output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize processors
        self.omop_processor = OMOPDataProcessor(
            config.omop_data_path, 
            config.omop_config
        )
        
        self.umls_mapper = UMLSOMOPMapper(
            config.umls_graph_path,
            config.mapping_config
        )
        
        # Results storage
        self.omop_data = None
        self.mappings = None
        self.unified_graph = None
        self.crosswalk_tables = None
        
        # Integration statistics
        self.integration_stats = {
            'start_time': None,
            'end_time': None,
            'omop_concepts_processed': 0,
            'umls_concepts_loaded': 0,
            'successful_mappings': 0,
            'mapping_coverage': 0.0,
            'unified_graph_nodes': 0,
            'unified_graph_edges': 0,
            'processing_errors': []
        }
        
        logger.info("Initialized OMOP-UMLS Integration System")
        logger.info(f"Output directory: {self.output_path}")
    
    def run_complete_integration(self) -> Dict:
        """
        Run complete OMOP-UMLS integration pipeline
        Main entry point for the entire system
        """
        logger.info("="*60)
        logger.info("STARTING OMOP-UMLS INTEGRATION PIPELINE")
        logger.info("="*60)
        
        self.integration_stats['start_time'] = datetime.now()
        
        try:
            # Phase 1: Process OMOP CDM 5.4 data
            logger.info("Phase 1: Processing OMOP CDM 5.4 data...")
            self.omop_data = self.omop_processor.process_all_tables()
            
            if self.config.save_intermediate_results:
                self.omop_processor.save_results(
                    self.omop_data, 
                    self.output_path / "omop_processed"
                )
            
            # Update statistics
            if 'concept_data' in self.omop_data:
                self.integration_stats['omop_concepts_processed'] = len(
                    self.omop_data['concept_data']['concepts']
                )
            
            # Phase 2: Load UMLS infrastructure
            logger.info("Phase 2: Loading UMLS knowledge graph infrastructure...")
            self.umls_mapper.load_umls_infrastructure()
            self.integration_stats['umls_concepts_loaded'] = len(
                self.umls_mapper.umls_concepts
            )
            
            # Phase 3: Map OMOP concepts to UMLS
            logger.info("Phase 3: Mapping OMOP concepts to UMLS...")
            if 'concept_data' in self.omop_data:
                omop_concepts = self.omop_data['concept_data']['concepts']
                self.mappings = self.umls_mapper.map_omop_to_umls(omop_concepts)
                
                self.integration_stats['successful_mappings'] = len(self.mappings)
                self.integration_stats['mapping_coverage'] = (
                    len(self.mappings) / len(omop_concepts) * 100
                )
                
                # Save mapping results
                self.umls_mapper.save_mappings(
                    self.mappings,
                    self.output_path / "mappings"
                )
            
            # Phase 4: Create unified knowledge graph
            if self.config.create_unified_graph:
                logger.info("Phase 4: Creating unified knowledge graph...")
                self.unified_graph = self.create_unified_knowledge_graph()
                
                self.integration_stats['unified_graph_nodes'] = self.unified_graph.number_of_nodes()
                self.integration_stats['unified_graph_edges'] = self.unified_graph.number_of_edges()
                
                # Save unified graph
                self.save_unified_graph()
            
            # Phase 5: Generate crosswalk tables
            if self.config.generate_crosswalk_tables:
                logger.info("Phase 5: Generating crosswalk tables...")
                self.crosswalk_tables = self.generate_crosswalk_tables()
                self.save_crosswalk_tables()
            
            # Phase 6: Validation and quality assessment
            if self.config.enable_validation:
                logger.info("Phase 6: Running validation and quality assessment...")
                validation_results = self.run_validation()
                self.save_validation_results(validation_results)
            
            # Generate final report
            final_report = self.generate_integration_report()
            self.save_integration_report(final_report)
            
        except Exception as e:
            error_msg = f"Integration pipeline failed: {str(e)}"
            logger.error(error_msg)
            self.integration_stats['processing_errors'].append(error_msg)
            raise
        
        finally:
            self.integration_stats['end_time'] = datetime.now()
            processing_time = (
                self.integration_stats['end_time'] - 
                self.integration_stats['start_time']
            ).total_seconds()
            
            logger.info("="*60)
            logger.info("OMOP-UMLS INTEGRATION COMPLETE")
            logger.info("="*60)
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            logger.info(f"OMOP concepts processed: {self.integration_stats['omop_concepts_processed']:,}")
            logger.info(f"UMLS concepts loaded: {self.integration_stats['umls_concepts_loaded']:,}")
            logger.info(f"Successful mappings: {self.integration_stats['successful_mappings']:,}")
            logger.info(f"Mapping coverage: {self.integration_stats['mapping_coverage']:.1f}%")
            
            if self.unified_graph:
                logger.info(f"Unified graph nodes: {self.integration_stats['unified_graph_nodes']:,}")
                logger.info(f"Unified graph edges: {self.integration_stats['unified_graph_edges']:,}")
        
        return self.integration_stats
    
    def create_unified_knowledge_graph(self) -> nx.Graph:
        """
        Create unified knowledge graph combining OMOP and UMLS
        Extends existing UMLS graph with OMOP concepts and mappings
        """
        logger.info("Creating unified OMOP-UMLS knowledge graph")
        
        # Start with existing UMLS graph or create new one
        if self.umls_mapper.umls_graph:
            unified_graph = self.umls_mapper.umls_graph.copy()
            logger.info(f"Starting with existing UMLS graph: {unified_graph.number_of_nodes():,} nodes")
        else:
            unified_graph = nx.Graph()
            logger.info("Creating new unified graph")
        
        # Add OMOP concepts as nodes
        if 'concept_data' in self.omop_data:
            omop_concepts = self.omop_data['concept_data']['concepts']
            
            for concept in omop_concepts:
                concept_id = concept['concept_id']
                
                # Create OMOP node identifier (prefix to avoid conflicts)
                omop_node_id = f"OMOP_{concept_id}"
                
                # Add OMOP concept as node
                unified_graph.add_node(omop_node_id, **{
                    'node_type': 'omop_concept',
                    'omop_concept_id': concept_id,
                    'concept_name': concept['concept_name'],
                    'domain_id': concept.get('domain_id', ''),
                    'vocabulary_id': concept.get('vocabulary_id', ''),
                    'concept_class_id': concept.get('concept_class_id', ''),
                    'standard_concept': concept.get('standard_concept', ''),
                    'concept_code': concept.get('concept_code', '')
                })
        
        # Add mapping edges between OMOP and UMLS concepts
        if self.mappings:
            for omop_concept_id, mapping in self.mappings.items():
                omop_node_id = f"OMOP_{omop_concept_id}"
                umls_node_id = mapping.umls_cui
                
                # Add mapping edge if both nodes exist
                if unified_graph.has_node(omop_node_id) and unified_graph.has_node(umls_node_id):
                    unified_graph.add_edge(omop_node_id, umls_node_id, **{
                        'edge_type': 'concept_mapping',
                        'mapping_type': mapping.mapping_type,
                        'confidence_score': mapping.confidence_score,
                        'similarity_score': mapping.similarity_score,
                        'evidence': mapping.evidence
                    })
        
        # Add OMOP relationships as edges
        if 'relationship_data' in self.omop_data:
            relationships = self.omop_data['relationship_data']['relationships']
            
            for rel in relationships:
                concept_id_1 = f"OMOP_{rel['concept_id_1']}"
                concept_id_2 = f"OMOP_{rel['concept_id_2']}"
                
                # Add relationship edge if both nodes exist
                if unified_graph.has_node(concept_id_1) and unified_graph.has_node(concept_id_2):
                    unified_graph.add_edge(concept_id_1, concept_id_2, **{
                        'edge_type': 'omop_relationship',
                        'relationship_id': rel['relationship_id'],
                        'valid_start_date': rel.get('valid_start_date', ''),
                        'valid_end_date': rel.get('valid_end_date', ''),
                        'invalid_reason': rel.get('invalid_reason', '')
                    })
        
        logger.info(f"Unified graph created: {unified_graph.number_of_nodes():,} nodes, {unified_graph.number_of_edges():,} edges")
        return unified_graph
    
    def generate_crosswalk_tables(self) -> Dict[str, pd.DataFrame]:
        """Generate crosswalk tables for different use cases"""
        logger.info("Generating crosswalk tables")
        
        crosswalk_tables = {}
        
        # 1. Main OMOP-UMLS crosswalk table
        if self.mappings:
            crosswalk_records = []
            
            for omop_concept_id, mapping in self.mappings.items():
                # Get OMOP concept details
                omop_concept = next(
                    (c for c in self.omop_data['concept_data']['concepts'] 
                     if c['concept_id'] == omop_concept_id),
                    {}
                )
                
                # Get UMLS concept details
                umls_concept = self.umls_mapper.umls_concepts.get(mapping.umls_cui, {})
                
                crosswalk_records.append({
                    'omop_concept_id': omop_concept_id,
                    'omop_concept_name': omop_concept.get('concept_name', ''),
                    'omop_domain_id': omop_concept.get('domain_id', ''),
                    'omop_vocabulary_id': omop_concept.get('vocabulary_id', ''),
                    'omop_concept_class_id': omop_concept.get('concept_class_id', ''),
                    'omop_concept_code': omop_concept.get('concept_code', ''),
                    'umls_cui': mapping.umls_cui,
                    'umls_preferred_name': umls_concept.get('preferred_name', ''),
                    'umls_semantic_types': ', '.join(umls_concept.get('semantic_types', [])),
                    'mapping_type': mapping.mapping_type,
                    'confidence_score': mapping.confidence_score,
                    'similarity_score': mapping.similarity_score,
                    'mapping_method': mapping.evidence.get('method', '')
                })
            
            crosswalk_tables['omop_umls_crosswalk'] = pd.DataFrame(crosswalk_records)
        
        # 2. Vocabulary-specific crosswalks
        if 'concept_data' in self.omop_data:
            vocabularies = self.omop_data['concept_data']['vocabularies']
            
            for vocabulary in vocabularies:
                vocab_concepts = [
                    c for c in self.omop_data['concept_data']['concepts']
                    if c.get('vocabulary_id') == vocabulary
                ]
                
                if vocab_concepts:
                    vocab_crosswalk = []
                    for concept in vocab_concepts:
                        concept_id = concept['concept_id']
                        mapping = self.mappings.get(concept_id)
                        
                        record = {
                            'omop_concept_id': concept_id,
                            'concept_name': concept['concept_name'],
                            'concept_code': concept.get('concept_code', ''),
                            'vocabulary_id': vocabulary
                        }
                        
                        if mapping:
                            record.update({
                                'umls_cui': mapping.umls_cui,
                                'mapping_confidence': mapping.confidence_score
                            })
                        else:
                            record.update({
                                'umls_cui': '',
                                'mapping_confidence': 0.0
                            })
                        
                        vocab_crosswalk.append(record)
                    
                    crosswalk_tables[f'crosswalk_{vocabulary.lower()}'] = pd.DataFrame(vocab_crosswalk)
        
        # 3. Domain-specific crosswalks
        if 'concept_data' in self.omop_data:
            domains = self.omop_data['concept_data']['domains']
            
            for domain in domains:
                domain_concepts = [
                    c for c in self.omop_data['concept_data']['concepts']
                    if c.get('domain_id') == domain
                ]
                
                if domain_concepts:
                    domain_crosswalk = []
                    for concept in domain_concepts:
                        concept_id = concept['concept_id']
                        mapping = self.mappings.get(concept_id)
                        
                        record = {
                            'omop_concept_id': concept_id,
                            'concept_name': concept['concept_name'],
                            'domain_id': domain,
                            'vocabulary_id': concept.get('vocabulary_id', '')
                        }
                        
                        if mapping:
                            record.update({
                                'umls_cui': mapping.umls_cui,
                                'mapping_confidence': mapping.confidence_score
                            })
                        
                        domain_crosswalk.append(record)
                    
                    crosswalk_tables[f'crosswalk_{domain.lower()}'] = pd.DataFrame(domain_crosswalk)
        
        logger.info(f"Generated {len(crosswalk_tables)} crosswalk tables")
        return crosswalk_tables
    
    def run_validation(self) -> Dict:
        """Run validation and quality assessment on integration results"""
        logger.info("Running validation and quality assessment")
        
        validation_results = {
            'data_quality': {},
            'mapping_quality': {},
            'graph_quality': {},
            'coverage_analysis': {},
            'recommendations': []
        }
        
        # Data quality validation
        if 'concept_data' in self.omop_data:
            total_concepts = len(self.omop_data['concept_data']['concepts'])
            valid_concepts = self.omop_data['concept_data']['processing_stats']['valid_concepts']
            
            validation_results['data_quality'] = {
                'total_omop_concepts': total_concepts,
                'valid_omop_concepts': valid_concepts,
                'data_quality_percentage': (valid_concepts / total_concepts * 100) if total_concepts > 0 else 0
            }
        
        # Mapping quality validation
        if self.mappings:
            high_confidence_mappings = sum(
                1 for m in self.mappings.values() 
                if m.confidence_score >= self.config.mapping_config.confidence_threshold
            )
            
            validation_results['mapping_quality'] = {
                'total_mappings': len(self.mappings),
                'high_confidence_mappings': high_confidence_mappings,
                'mapping_quality_percentage': (high_confidence_mappings / len(self.mappings) * 100),
                'average_confidence': sum(m.confidence_score for m in self.mappings.values()) / len(self.mappings)
            }
        
        # Graph quality validation
        if self.unified_graph:
            connected_components = list(nx.connected_components(self.unified_graph))
            largest_component_size = len(max(connected_components, key=len)) if connected_components else 0
            
            validation_results['graph_quality'] = {
                'total_nodes': self.unified_graph.number_of_nodes(),
                'total_edges': self.unified_graph.number_of_edges(),
                'connected_components': len(connected_components),
                'largest_component_size': largest_component_size,
                'graph_density': nx.density(self.unified_graph)
            }
        
        # Coverage analysis
        if self.omop_data and self.mappings:
            total_omop = len(self.omop_data['concept_data']['concepts'])
            mapped_omop = len(self.mappings)
            
            validation_results['coverage_analysis'] = {
                'total_omop_concepts': total_omop,
                'mapped_omop_concepts': mapped_omop,
                'overall_coverage_percentage': (mapped_omop / total_omop * 100),
                'unmapped_concepts': total_omop - mapped_omop
            }
        
        # Generate recommendations
        recommendations = []
        
        if validation_results['mapping_quality']['mapping_quality_percentage'] < 70:
            recommendations.append("Consider lowering confidence threshold or improving mapping algorithms")
        
        if validation_results['coverage_analysis']['overall_coverage_percentage'] < 75:
            recommendations.append("Investigate unmapped concepts and consider additional mapping strategies")
        
        if validation_results['graph_quality']['connected_components'] > 10:
            recommendations.append("Graph has many disconnected components - consider adding more relationship data")
        
        validation_results['recommendations'] = recommendations
        
        logger.info("Validation complete:")
        logger.info(f"  Data quality: {validation_results['data_quality'].get('data_quality_percentage', 0):.1f}%")
        logger.info(f"  Mapping quality: {validation_results['mapping_quality'].get('mapping_quality_percentage', 0):.1f}%")
        logger.info(f"  Overall coverage: {validation_results['coverage_analysis'].get('overall_coverage_percentage', 0):.1f}%")
        
        return validation_results
    
    def save_unified_graph(self):
        """Save unified knowledge graph"""
        graph_path = self.output_path / "unified_graph"
        graph_path.mkdir(exist_ok=True)
        
        # Save as pickle for full functionality
        with open(graph_path / "unified_omop_umls_graph.pkl", 'wb') as f:
            pickle.dump(self.unified_graph, f)
        
        # Save as GraphML for external tools (convert lists to strings)
        try:
            # Create a copy of the graph with string-converted attributes
            graph_copy = self.unified_graph.copy()
            
            # Convert list attributes to strings for GraphML compatibility
            for node, data in graph_copy.nodes(data=True):
                for key, value in data.items():
                    if isinstance(value, list):
                        graph_copy.nodes[node][key] = ', '.join(map(str, value))
            
            for u, v, data in graph_copy.edges(data=True):
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        graph_copy.edges[u, v][key] = str(value)
            
            nx.write_graphml(graph_copy, graph_path / "unified_omop_umls_graph.graphml")
        except Exception as e:
            logger.warning(f"Could not save GraphML format: {e}")
            logger.info("Graph saved in pickle format only")
        
        logger.info(f"Unified graph saved to {graph_path}")
    
    def save_crosswalk_tables(self):
        """Save crosswalk tables"""
        crosswalk_path = self.output_path / "crosswalk_tables"
        crosswalk_path.mkdir(exist_ok=True)
        
        for table_name, df in self.crosswalk_tables.items():
            # Save as CSV
            df.to_csv(crosswalk_path / f"{table_name}.csv", index=False)
            
            # Save as Excel for easier viewing
            df.to_excel(crosswalk_path / f"{table_name}.xlsx", index=False)
        
        logger.info(f"Crosswalk tables saved to {crosswalk_path}")
    
    def save_validation_results(self, validation_results: Dict):
        """Save validation results"""
        with open(self.output_path / "validation_results.json", 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)
        
        logger.info(f"Validation results saved to {self.output_path / 'validation_results.json'}")
    
    def generate_integration_report(self) -> Dict:
        """Generate comprehensive integration report"""
        report = {
            'integration_summary': self.integration_stats,
            'system_configuration': {
                'omop_data_path': self.config.omop_data_path,
                'umls_graph_path': self.config.umls_graph_path,
                'output_path': str(self.output_path),
                'omop_config': self.config.omop_config.__dict__,
                'mapping_config': self.config.mapping_config.__dict__
            },
            'data_overview': {},
            'mapping_overview': {},
            'output_files': []
        }
        
        # Data overview
        if self.omop_data:
            report['data_overview'] = {
                'omop_tables_processed': self.omop_data['processing_stats']['tables_processed'],
                'omop_concepts': len(self.omop_data.get('concept_data', {}).get('concepts', [])),
                'omop_relationships': len(self.omop_data.get('relationship_data', {}).get('relationships', [])),
                'omop_vocabularies': len(self.omop_data.get('concept_data', {}).get('vocabularies', [])),
                'omop_domains': len(self.omop_data.get('concept_data', {}).get('domains', []))
            }
        
        # Mapping overview
        if self.mappings:
            mapping_types = {}
            for mapping in self.mappings.values():
                mapping_type = mapping.mapping_type
                mapping_types[mapping_type] = mapping_types.get(mapping_type, 0) + 1
            
            report['mapping_overview'] = {
                'total_mappings': len(self.mappings),
                'mapping_types': mapping_types,
                'coverage_percentage': self.integration_stats['mapping_coverage']
            }
        
        # Output files
        output_files = []
        for file_path in self.output_path.rglob('*'):
            if file_path.is_file():
                output_files.append({
                    'filename': file_path.name,
                    'path': str(file_path.relative_to(self.output_path)),
                    'size_mb': file_path.stat().st_size / (1024 * 1024)
                })
        
        report['output_files'] = output_files
        
        return report
    
    def save_integration_report(self, report: Dict):
        """Save integration report"""
        with open(self.output_path / "integration_report.json", 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Integration report saved to {self.output_path / 'integration_report.json'}")

def main():
    """Example usage of OMOP-UMLS integrator"""
    
    # Configuration
    omop_config = OMOPConfig(
        chunk_size=50000,
        max_workers=4,
        memory_limit_gb=8.0,
        enable_parallel=True,
        cache_results=True
    )
    
    mapping_config = MappingConfig(
        similarity_threshold=0.7,
        confidence_threshold=0.8,
        enable_fuzzy_matching=True,
        enable_semantic_similarity=True
    )
    
    integration_config = IntegrationConfig(
        omop_data_path="/path/to/omop/cdm/data",  # Update with actual path
        umls_graph_path="/path/to/umls/knowledge/graph",  # Update with actual path
        output_path="/path/to/output",  # Update with actual path
        omop_config=omop_config,
        mapping_config=mapping_config,
        create_unified_graph=True,
        generate_crosswalk_tables=True,
        enable_validation=True
    )
    
    # Run integration
    integrator = OMOPUMLSIntegrator(integration_config)
    
    try:
        integration_stats = integrator.run_complete_integration()
        
        print("\n" + "="*80)
        print("OMOP-UMLS INTEGRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        print(f"Processing time: {(integration_stats['end_time'] - integration_stats['start_time']).total_seconds():.2f} seconds")
        print(f"OMOP concepts processed: {integration_stats['omop_concepts_processed']:,}")
        print(f"UMLS concepts loaded: {integration_stats['umls_concepts_loaded']:,}")
        print(f"Successful mappings: {integration_stats['successful_mappings']:,}")
        print(f"Mapping coverage: {integration_stats['mapping_coverage']:.1f}%")
        print(f"Unified graph nodes: {integration_stats['unified_graph_nodes']:,}")
        print(f"Unified graph edges: {integration_stats['unified_graph_edges']:,}")
        print(f"Output directory: {integration_config.output_path}")
        
    except Exception as e:
        logger.error(f"Integration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
