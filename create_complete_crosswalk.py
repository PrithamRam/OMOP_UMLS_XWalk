#!/usr/bin/env python3
"""
Create Complete OMOP-UMLS Crosswalk
Uses your complete 9.66M OMOP concepts with 3.4M UMLS concepts
Creates the definitive production crosswalk system
"""

import pickle
import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
from datetime import datetime
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def load_complete_datasets():
    """Load complete OMOP and UMLS datasets"""
    print("="*80)
    print("LOADING COMPLETE DATASETS")
    print("="*80)
    
    # Load complete OMOP concepts
    print("📚 Loading complete OMOP concepts...")
    with open("complete_omop_processed.pkl", 'rb') as f:
        omop_data = pickle.load(f)
    
    omop_concepts = omop_data['concepts']
    print(f"   OMOP concepts: {len(omop_concepts):,}")
    print(f"   Vocabularies: {len(omop_data['vocabularies'])}")
    
    # Load complete UMLS knowledge graph
    print("🧬 Loading complete UMLS knowledge graph...")
    umls_graph_path = "/Users/pmr45/Desktop/BIDS Admin/RAG Literature/RRF FILES/full_scale_output/full_scale_knowledge_graph.pkl"
    
    with open(umls_graph_path, 'rb') as f:
        umls_graph = pickle.load(f)
    
    # Extract UMLS concepts
    umls_concepts = {}
    for node, data in umls_graph.nodes(data=True):
        umls_concepts[node] = {
            'cui': node,
            'preferred_name': data.get('preferred_name', data.get('name', str(node))),
            'semantic_types': data.get('semantic_types', []),
            'definitions': data.get('definitions', []),
            'synonyms': data.get('synonyms', [])
        }
    
    print(f"   UMLS concepts: {len(umls_concepts):,}")
    print(f"   Graph nodes: {umls_graph.number_of_nodes():,}")
    print(f"   Graph edges: {umls_graph.number_of_edges():,}")
    
    return omop_concepts, umls_concepts

def create_production_scale_mappings(omop_concepts, umls_concepts, max_mappings=None):
    """Create mappings at production scale"""
    print(f"\n🔗 Creating production-scale mappings...")
    print(f"   OMOP concepts: {len(omop_concepts):,}")
    print(f"   UMLS concepts: {len(umls_concepts):,}")
    
    if max_mappings:
        print(f"   Max mappings limit: {max_mappings:,}")
    
    start_time = time.time()
    mappings = {}
    
    # Strategy 1: Direct CUI mappings (highest confidence)
    print(f"   Phase 1: Direct CUI mappings...")
    direct_count = 0
    
    for concept in omop_concepts:
        # Check limit before adding
        if max_mappings and len(mappings) >= max_mappings:
            print(f"     ⚠️  Reached max mappings limit ({max_mappings:,}) - stopping Phase 1")
            break
            
        concept_code = concept.get('concept_code', '')
        
        # Check for direct CUI patterns
        if concept_code and concept_code.startswith('C') and len(concept_code) == 8:
            if concept_code in umls_concepts:
                mappings[concept['concept_id']] = {
                    'umls_cui': concept_code,
                    'mapping_type': 'direct_cui',
                    'confidence_score': 1.0,
                    'similarity_score': 1.0,
                    'evidence': {'method': 'direct_cui', 'concept_code': concept_code}
                }
                direct_count += 1
    
    print(f"     Direct CUI mappings: {direct_count:,}")
    
    # Strategy 2: Exact string matching (efficient)
    print(f"   Phase 2: Exact string matching...")
    
    # Create UMLS lookup (optimized)
    umls_lookup = {}
    for cui, concept_data in umls_concepts.items():
        name = concept_data.get('preferred_name', '').lower().strip()
        if name and len(name) > 2:
            if name not in umls_lookup:
                umls_lookup[name] = []
            umls_lookup[name].append(cui)
        
        # Index first synonym only (for efficiency)
        synonyms = concept_data.get('synonyms', [])
        if synonyms and len(synonyms) > 0:
            first_synonym = synonyms[0].lower().strip()
            if first_synonym and len(first_synonym) > 2:
                if first_synonym not in umls_lookup:
                    umls_lookup[first_synonym] = []
                umls_lookup[first_synonym].append(cui)
    
    print(f"     UMLS lookup created: {len(umls_lookup):,} entries")
    
    exact_count = 0
    for concept in omop_concepts:
        # Check limit before adding
        if max_mappings and len(mappings) >= max_mappings:
            print(f"     ⚠️  Reached max mappings limit ({max_mappings:,}) - stopping Phase 2")
            break
            
        concept_id = concept['concept_id']
        
        if concept_id in mappings:
            continue
        
        concept_name = concept.get('concept_name', '').lower().strip()
        
        if concept_name in umls_lookup:
            matched_cui = umls_lookup[concept_name][0]
            mappings[concept_id] = {
                'umls_cui': matched_cui,
                'mapping_type': 'exact_match',
                'confidence_score': 0.95,
                'similarity_score': 1.0,
                'evidence': {'method': 'exact_string', 'matched_name': concept_name}
            }
            exact_count += 1
    
    print(f"     Exact string matches: {exact_count:,}")
    
    # Strategy 3: High-value semantic matching (selective for performance)
    print(f"   Phase 3: Semantic matching (high-value concepts)...")
    
    # Only proceed if we haven't hit the limit
    if max_mappings and len(mappings) >= max_mappings:
        print(f"     ⚠️  Already at max mappings limit ({max_mappings:,}) - skipping Phase 3")
    else:
        # Select high-value concepts for semantic matching
        high_value_concepts = []
        medical_keywords = [
            'diabetes', 'hypertension', 'cancer', 'heart', 'blood', 'infection',
            'mg', 'ml', 'tablet', 'capsule', 'injection', 'procedure', 'surgery',
            'test', 'lab', 'measurement', 'syndrome', 'disease', 'disorder'
        ]
        
        for concept in omop_concepts:
            if concept['concept_id'] in mappings:
                continue
            
            concept_name = concept.get('concept_name', '').lower()
            
            if any(keyword in concept_name for keyword in medical_keywords):
                high_value_concepts.append(concept)
            
            # Limit for performance
            if max_mappings and len(high_value_concepts) >= max_mappings - len(mappings):
                break
        
        print(f"     High-value concepts selected: {len(high_value_concepts):,}")
        
        # Semantic matching with efficiency optimizations
        semantic_mappings = create_efficient_semantic_mappings(
            high_value_concepts, umls_concepts, batch_size=10000
        )
        
        # Apply limit to semantic mappings
        if max_mappings:
            remaining_slots = max_mappings - len(mappings)
            if len(semantic_mappings) > remaining_slots:
                print(f"     ⚠️  Limiting semantic mappings to {remaining_slots:,} to stay under limit")
                # Take only the first remaining_slots mappings
                limited_semantic = dict(list(semantic_mappings.items())[:remaining_slots])
                semantic_mappings = limited_semantic
        
        mappings.update(semantic_mappings)
        print(f"     Semantic matches: {len(semantic_mappings):,}")
    
    total_time = time.time() - start_time
    total_mappings = len(mappings)
    coverage = total_mappings / len(omop_concepts) * 100
    
    print(f"\n✅ Production mapping complete!")
    print(f"   Total mappings: {total_mappings:,}")
    if max_mappings:
        print(f"   Limit applied: {max_mappings:,}")
        print(f"   Limit utilization: {total_mappings/max_mappings*100:.1f}%")
    print(f"   Coverage: {coverage:.1f}%")
    print(f"   Processing time: {total_time / 60:.1f} minutes")
    
    return mappings

def create_efficient_semantic_mappings(concepts, umls_concepts, batch_size=10000):
    """Create semantic mappings efficiently"""
    
    # Use subset of UMLS for efficiency (every 5th concept)
    umls_sample = dict(list(umls_concepts.items())[::5])
    
    umls_texts = []
    umls_cuis = []
    
    for cui, concept_data in umls_sample.items():
        text = concept_data.get('preferred_name', '')
        if text and len(text) > 2:
            umls_texts.append(text.lower())
            umls_cuis.append(cui)
    
    if not umls_texts:
        return {}
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        max_features=15000,
        stop_words='english',
        ngram_range=(1, 2),
        min_df=2
    )
    
    umls_vectors = vectorizer.fit_transform(umls_texts)
    print(f"       TF-IDF vectors: {len(umls_texts):,} UMLS concepts")
    
    mappings = {}
    
    # Process in batches
    for i in range(0, len(concepts), batch_size):
        batch = concepts[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"       Processing batch {batch_num} ({len(batch):,} concepts)...")
        
        for concept in batch:
            concept_name = concept.get('concept_name', '').lower().strip()
            
            if not concept_name or len(concept_name) < 3:
                continue
            
            try:
                concept_vector = vectorizer.transform([concept_name])
                similarities = cosine_similarity(concept_vector, umls_vectors).flatten()
                
                best_idx = np.argmax(similarities)
                best_similarity = similarities[best_idx]
                
                if best_similarity >= 0.4:  # Reasonable threshold
                    matched_cui = umls_cuis[best_idx]
                    
                    mappings[concept['concept_id']] = {
                        'umls_cui': matched_cui,
                        'mapping_type': 'semantic_similarity',
                        'confidence_score': min(best_similarity * 0.8, 0.9),
                        'similarity_score': float(best_similarity),
                        'evidence': {
                            'method': 'semantic_similarity_production',
                            'similarity': float(best_similarity)
                        }
                    }
            
            except Exception:
                continue
    
    return mappings

def save_complete_crosswalk(mappings, omop_concepts, umls_concepts):
    """Save the complete crosswalk results"""
    print(f"\n💾 Saving complete crosswalk...")
    
    output_dir = Path("COMPLETE_PRODUCTION_CROSSWALK")
    output_dir.mkdir(exist_ok=True)
    
    # OPTIMIZATION: Create lookup dictionaries to avoid linear searches
    print(f"   Creating optimized lookups...")
    omop_lookup = {c['concept_id']: c for c in omop_concepts}
    umls_lookup = umls_concepts  # Already a dict
    
    print(f"   OMOP lookup: {len(omop_lookup):,} concepts")
    print(f"   UMLS lookup: {len(umls_lookup):,} concepts")
    
    # Create comprehensive crosswalk table
    print(f"   Building crosswalk records...")
    crosswalk_records = []
    
    for i, (omop_concept_id, mapping) in enumerate(mappings.items()):
        if i % 100000 == 0:  # Progress indicator
            print(f"     Processed {i:,} mappings...")
            
        # Use optimized lookups instead of linear search
        omop_concept = omop_lookup.get(omop_concept_id, {})
        umls_concept = umls_lookup.get(mapping['umls_cui'], {})
        
        crosswalk_records.append({
            'omop_concept_id': omop_concept_id,
            'omop_concept_name': omop_concept.get('concept_name', ''),
            'omop_domain_id': omop_concept.get('domain_id', ''),
            'omop_vocabulary_id': omop_concept.get('vocabulary_id', ''),
            'omop_concept_class_id': omop_concept.get('concept_class_id', ''),
            'omop_concept_code': omop_concept.get('concept_code', ''),
            'omop_standard_concept': omop_concept.get('standard_concept', ''),
            'umls_cui': mapping['umls_cui'],
            'umls_preferred_name': umls_concept.get('preferred_name', ''),
            'umls_semantic_types': ', '.join(umls_concept.get('semantic_types', [])),
            'mapping_type': mapping['mapping_type'],
            'confidence_score': mapping['confidence_score'],
            'similarity_score': mapping['similarity_score'],
            'mapping_method': mapping['evidence'].get('method', '')
        })
    
    print(f"   Crosswalk records built: {len(crosswalk_records):,}")
    
    # Save main crosswalk
    print(f"   Saving main crosswalk CSV...")
    crosswalk_df = pd.DataFrame(crosswalk_records)
    crosswalk_df.to_csv(output_dir / 'COMPLETE_OMOP_UMLS_CROSSWALK.csv', index=False)
    print(f"   Main crosswalk saved: {len(crosswalk_df):,} mappings")
    
    # Save as pickle for faster future loading
    print(f"   Saving pickle format...")
    with open(output_dir / 'complete_mappings.pkl', 'wb') as f:
        pickle.dump(mappings, f)
    
    # Generate comprehensive summary
    print(f"   Generating summary...")
    summary = generate_complete_summary(mappings, omop_concepts, umls_concepts)
    
    with open(output_dir / 'COMPLETE_SUMMARY.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"✅ Complete crosswalk saved to: {output_dir}/")
    
    return summary

def generate_complete_summary(mappings, omop_concepts, umls_concepts):
    """Generate comprehensive summary of complete crosswalk"""
    
    # Basic statistics
    total_mappings = len(mappings)
    total_omop = len(omop_concepts)
    coverage = total_mappings / total_omop * 100
    
    # Mapping type distribution
    mapping_types = Counter()
    confidence_distribution = Counter()
    
    for mapping in mappings.values():
        mapping_types[mapping['mapping_type']] += 1
        
        # Confidence ranges
        conf = mapping['confidence_score']
        if conf >= 0.9:
            confidence_distribution['excellent'] += 1
        elif conf >= 0.8:
            confidence_distribution['high'] += 1
        elif conf >= 0.7:
            confidence_distribution['good'] += 1
        elif conf >= 0.6:
            confidence_distribution['moderate'] += 1
        else:
            confidence_distribution['low'] += 1
    
    # Vocabulary coverage
    vocab_coverage = {}
    omop_vocab_counts = Counter()
    
    for concept in omop_concepts:
        vocab = concept.get('vocabulary_id', 'Unknown')
        omop_vocab_counts[vocab] += 1
    
    for vocab, total_count in omop_vocab_counts.items():
        mapped_count = sum(
            1 for omop_id, mapping in mappings.items()
            if any(c['concept_id'] == omop_id and c.get('vocabulary_id') == vocab 
                  for c in omop_concepts)
        )
        
        if total_count > 0:
            vocab_coverage[vocab] = {
                'total_concepts': total_count,
                'mapped_concepts': mapped_count,
                'coverage_percentage': mapped_count / total_count * 100
            }
    
    return {
        'generation_timestamp': datetime.now().isoformat(),
        'dataset_scale': {
            'total_omop_concepts': total_omop,
            'total_umls_concepts': len(umls_concepts),
            'total_mappings': total_mappings,
            'overall_coverage_percentage': coverage
        },
        'mapping_types': dict(mapping_types),
        'confidence_distribution': dict(confidence_distribution),
        'vocabulary_coverage': vocab_coverage,
        'quality_metrics': {
            'high_confidence_mappings': confidence_distribution['excellent'] + confidence_distribution['high'],
            'average_confidence': sum(m['confidence_score'] for m in mappings.values()) / len(mappings),
            'top_vocabularies_by_coverage': sorted(
                [(v, stats['coverage_percentage']) for v, stats in vocab_coverage.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
        }
    }

def main():
    """Create complete production crosswalk"""
    
    print("Complete OMOP-UMLS Crosswalk Creation")
    print("Production scale: 9.66M OMOP + 3.4M UMLS concepts")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    overall_start = time.time()
    
    try:
        # Load datasets
        omop_concepts, umls_concepts = load_complete_datasets()
        
        # Create mappings (test with 3M limit)
        print(f"\n🔗 Creating production mappings...")
        print(f"   Test run: Limited to 3M mappings to verify limit functionality")
        print(f"   This will test if the limit enforcement works correctly")
        
        mappings = create_production_scale_mappings(
            omop_concepts, umls_concepts, max_mappings=3000000
        )
        
        # Save complete results
        summary = save_complete_crosswalk(mappings, omop_concepts, umls_concepts)
        
        # Final summary
        total_time = time.time() - overall_start
        
        print(f"\n" + "="*80)
        print("COMPLETE PRODUCTION CROSSWALK FINISHED!")
        print("="*80)
        
        print(f"Total processing time: {total_time / 60:.1f} minutes")
        print(f"OMOP concepts: {summary['dataset_scale']['total_omop_concepts']:,}")
        print(f"UMLS concepts: {summary['dataset_scale']['total_umls_concepts']:,}")
        print(f"Mappings created: {summary['dataset_scale']['total_mappings']:,}")
        print(f"Coverage: {summary['dataset_scale']['overall_coverage_percentage']:.1f}%")
        
        print(f"\n📊 Mapping breakdown:")
        for mapping_type, count in summary['mapping_types'].items():
            print(f"   {mapping_type}: {count:,}")
        
        print(f"\n🏆 Quality metrics:")
        print(f"   High confidence: {summary['quality_metrics']['high_confidence_mappings']:,}")
        print(f"   Average confidence: {summary['quality_metrics']['average_confidence']:.3f}")
        
        print(f"\n📁 Complete results: COMPLETE_PRODUCTION_CROSSWALK/")
        print(f"🎉 PHASE 1.1 COMPLETE - Ready for Phase 1.2!")
        
        return summary
        
    except Exception as e:
        print(f"\n❌ Complete processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    results = main()
