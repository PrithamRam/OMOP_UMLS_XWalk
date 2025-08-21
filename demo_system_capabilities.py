#!/usr/bin/env python3
"""
OMOP-UMLS Crosswalk System: Capabilities Demonstration
Showcases the system's key features and query capabilities
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("⚠️  Neo4j driver not available. Install with: pip install neo4j")

class SystemCapabilitiesDemo:
    """Demonstrates the system's key capabilities"""
    
    def __init__(self):
        """Initialize Neo4j connection"""
        if not NEO4J_AVAILABLE:
            print("❌ Neo4j driver not available")
            return
            
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        user = os.getenv('NEO4J_USER', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD')
        
        if not password:
            print("❌ Neo4j password not found in environment variables")
            return
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            print("✅ Connected to Neo4j successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            return
    
    def close(self):
        """Close Neo4j connection"""
        if hasattr(self, 'driver'):
            self.driver.close()
    
    def demo_1_basic_statistics(self):
        """Demonstrate basic system statistics"""
        print("\n" + "="*60)
        print("📊 DEMO 1: BASIC SYSTEM STATISTICS")
        print("="*60)
        
        with self.driver.session() as session:
            # Total node counts
            result = session.run("MATCH (n) RETURN labels(n) as node_type, count(n) as count ORDER BY count DESC")
            print("\n📈 Total Nodes by Type:")
            for record in result:
                print(f"   {record['node_type']}: {record['count']:,}")
            
            # Total relationship counts
            result = session.run("MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC")
            print("\n🔗 Total Relationships by Type:")
            for record in result:
                print(f"   {record['rel_type']}: {record['count']:,}")
    
    def demo_2_concept_search(self):
        """Demonstrate concept search capabilities"""
        print("\n" + "="*60)
        print("🔍 DEMO 2: CONCEPT SEARCH CAPABILITIES")
        print("="*60)
        
        with self.driver.session() as session:
            # Search for diabetes concepts
            print("\n🔍 Searching for 'diabetes' concepts:")
            result = session.run("""
                MATCH (o:OMOPConcept)
                WHERE o.concept_name CONTAINS 'diabetes'
                RETURN o.concept_name, o.domain_id, o.vocabulary_id
                LIMIT 5
            """)
            
            for i, record in enumerate(result, 1):
                print(f"   {i}. {record['o.concept_name']} ({record['o.domain_id']}, {record['o.vocabulary_id']})")
            
            # Search for UMLS concepts
            print("\n🔍 Searching for UMLS 'diabetes' concepts:")
            result = session.run("""
                MATCH (u:UMLSConcept)
                WHERE u.preferred_name CONTAINS 'diabetes'
                RETURN u.preferred_name, u.semantic_types
                LIMIT 5
            """)
            
            for i, record in enumerate(result, 1):
                semantic_types = record['u.semantic_types'][:3] if record['u.semantic_types'] else []
                print(f"   {i}. {record['u.preferred_name']} - Types: {semantic_types}")
    
    def demo_3_crosswalk_mappings(self):
        """Demonstrate crosswalk mapping capabilities"""
        print("\n" + "="*60)
        print("🔗 DEMO 3: CROSSWALK MAPPING CAPABILITIES")
        print("="*60)
        
        with self.driver.session() as session:
            # Find crosswalk mappings for diabetes
            print("\n🔗 Crosswalk mappings for 'diabetes':")
            result = session.run("""
                MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
                WHERE o.concept_name CONTAINS 'diabetes'
                RETURN o.concept_name, u.preferred_name, m.confidence_score, m.mapping_type
                ORDER BY m.confidence_score DESC
                LIMIT 5
            """)
            
            for i, record in enumerate(result, 1):
                print(f"   {i}. OMOP: {record['o.concept_name']}")
                print(f"      UMLS: {record['u.preferred_name']}")
                print(f"      Confidence: {record['m.confidence_score']:.3f}, Type: {record['m.mapping_type']}")
                print()
    
    def demo_4_semantic_richness(self):
        """Demonstrate UMLS semantic richness"""
        print("\n" + "="*60)
        print("🧬 DEMO 4: UMLS SEMANTIC RICHNESS")
        print("="*60)
        
        with self.driver.session() as session:
            # Show concepts with semantic types
            print("\n🧬 Concepts with semantic types:")
            result = session.run("""
                MATCH (u:UMLSConcept)
                WHERE u.semantic_types IS NOT NULL AND size(u.semantic_types) > 0
                RETURN u.preferred_name, u.semantic_types, u.definitions
                LIMIT 3
            """)
            
            for i, record in enumerate(result, 1):
                print(f"   {i}. {record['u.preferred_name']}")
                print(f"      Semantic Types: {record['u.semantic_types']}")
                if record['u.definitions']:
                    definition = record['u.definitions'][0][:100] + "..." if len(record['u.definitions'][0]) > 100 else record['u.definitions'][0]
                    print(f"      Definition: {definition}")
                print()
    
    def demo_5_hierarchical_relationships(self):
        """Demonstrate hierarchical relationship capabilities"""
        print("\n" + "="*60)
        print("🌳 DEMO 5: HIERARCHICAL RELATIONSHIP CAPABILITIES")
        print("="*60)
        
        with self.driver.session() as session:
            # Find hierarchical relationships
            print("\n🌳 Hierarchical relationships for 'diabetes':")
            result = session.run("""
                MATCH (u1:UMLSConcept)-[r:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
                WHERE u1.preferred_name CONTAINS 'diabetes'
                AND r.relationship_type IN ['RB', 'RN', 'PAR', 'CHD']
                RETURN u1.preferred_name, u2.preferred_name, r.relationship_type
                ORDER BY r.relationship_type
                LIMIT 10
            """)
            
            for i, record in enumerate(result, 1):
                rel_type = record['r.relationship_type']
                rel_desc = {
                    'RB': 'Broader than',
                    'RN': 'Narrower than', 
                    'PAR': 'Parent of',
                    'CHD': 'Child of'
                }.get(rel_type, rel_type)
                
                print(f"   {i}. {record['u1.preferred_name']} {rel_desc} {record['u2.preferred_name']}")
    
    def demo_6_advanced_queries(self):
        """Demonstrate advanced query capabilities"""
        print("\n" + "="*60)
        print("🚀 DEMO 6: ADVANCED QUERY CAPABILITIES")
        print("="*60)
        
        with self.driver.session() as session:
            # Multi-hop relationship analysis
            print("\n🚀 Multi-hop relationship analysis:")
            result = session.run("""
                MATCH path = (u1:UMLSConcept)-[:UMLS_RELATIONSHIP*1..2]-(u2:UMLSConcept)
                WHERE u1.preferred_name CONTAINS 'diabetes'
                AND u2.preferred_name CONTAINS 'complication'
                RETURN u1.preferred_name, u2.preferred_name, length(path) as hops
                ORDER BY hops
                LIMIT 5
            """)
            
            for i, record in enumerate(result, 1):
                print(f"   {i}. {record['u1.preferred_name']} → {record['u2.preferred_name']} ({record['hops']} hops)")
            
            # Vocabulary integration analysis
            print("\n📚 Vocabulary integration analysis:")
            result = session.run("""
                MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
                WHERE o.vocabulary_id IN ['SNOMED', 'ICD10CM', 'RxNorm']
                AND m.confidence_score > 0.8
                RETURN o.vocabulary_id, count(*) as concept_count
                ORDER BY concept_count DESC
            """)
            
            for record in result:
                print(f"   {record['o.vocabulary_id']}: {record['concept_count']:,} concepts")
    
    def demo_7_use_case_examples(self):
        """Demonstrate real-world use cases"""
        print("\n" + "="*60)
        print("💡 DEMO 7: REAL-WORLD USE CASES")
        print("="*60)
        
        with self.driver.session() as session:
            # Phenotype development example
            print("\n💡 Phenotype Development - Diabetes Case Definition:")
            result = session.run("""
                MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
                WHERE (o.concept_name CONTAINS 'diabetes' OR u.preferred_name CONTAINS 'diabetes')
                AND o.domain_id = 'Condition'
                AND m.confidence_score > 0.8
                RETURN o.concept_name, o.vocabulary_id, u.preferred_name, m.confidence_score
                ORDER BY m.confidence_score DESC
                LIMIT 5
            """)
            
            for i, record in enumerate(result, 1):
                print(f"   {i}. {record['o.concept_name']} ({record['o.vocabulary_id']})")
                print(f"      UMLS: {record['u.preferred_name']}")
                print(f"      Confidence: {record['m.confidence_score']:.3f}")
                print()
            
            # Drug-disease relationship example
            print("\n💊 Drug-Disease Relationship Analysis:")
            result = session.run("""
                MATCH (o1:OMOPConcept)-[m1:CROSSWALK_MAPPING]->(u1:UMLSConcept)
                MATCH (o2:OMOPConcept)-[m2:CROSSWALK_MAPPING]->(u2:UMLSConcept)
                WHERE o1.domain_id = 'Drug'
                AND o2.domain_id = 'Condition'
                AND u1.preferred_name CONTAINS 'insulin'
                AND u2.preferred_name CONTAINS 'diabetes'
                AND m1.confidence_score > 0.8
                AND m2.confidence_score > 0.8
                RETURN o1.concept_name, o2.concept_name
                LIMIT 3
            """)
            
            for i, record in enumerate(result, 1):
                print(f"   {i}. Drug: {record['o1.concept_name']}")
                print(f"      Condition: {record['o2.concept_name']}")
                print()
    
    def run_all_demos(self):
        """Run all demonstration scenarios"""
        print("🎉 OMOP-UMLS CROSSWALK SYSTEM CAPABILITIES DEMONSTRATION")
        print("="*80)
        print("This demonstration showcases the system's key features and capabilities.")
        print("="*80)
        
        if not hasattr(self, 'driver'):
            print("❌ Cannot run demos - Neo4j connection not available")
            return
        
        try:
            self.demo_1_basic_statistics()
            self.demo_2_concept_search()
            self.demo_3_crosswalk_mappings()
            self.demo_4_semantic_richness()
            self.demo_5_hierarchical_relationships()
            self.demo_6_advanced_queries()
            self.demo_7_use_case_examples()
            
            print("\n" + "="*80)
            print("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
            print("="*80)
            print("\n💡 WHAT YOU'VE SEEN:")
            print("   ✅ Complete system statistics and data volume")
            print("   ✅ Concept search across OMOP and UMLS")
            print("   ✅ Crosswalk mapping capabilities")
            print("   ✅ UMLS semantic richness preservation")
            print("   ✅ Hierarchical relationship exploration")
            print("   ✅ Advanced query capabilities")
            print("   ✅ Real-world use case examples")
            
            print("\n🚀 NEXT STEPS:")
            print("   1. Explore the Neo4j Browser at http://localhost:7474")
            print("   2. Try the sample queries from the User Manual")
            print("   3. Build your own queries for your research needs")
            print("   4. Refer to the documentation for advanced features")
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main demonstration function"""
    print("🚀 Starting OMOP-UMLS Crosswalk System Capabilities Demonstration...")
    
    if not NEO4J_AVAILABLE:
        print("❌ Neo4j driver not available. Install with: pip install neo4j")
        return
    
    demo = SystemCapabilitiesDemo()
    
    if hasattr(demo, 'driver'):
        demo.run_all_demos()
        demo.close()
    else:
        print("❌ Failed to initialize demonstration system")

if __name__ == "__main__":
    main()
