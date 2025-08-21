# OMOP-UMLS Crosswalk System: User Manual

## 📋 Table of Contents
1. [Getting Started](#getting-started)
2. [Understanding the System](#understanding-the-system)
3. [Basic Queries](#basic-queries)
4. [Advanced Queries](#advanced-queries)
5. [Use Cases and Examples](#use-cases-and-examples)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## 🚀 Getting Started

### What You Need
- **Neo4j Browser Access**: Open http://localhost:7474 in your web browser
- **Credentials**: Username: `neo4j`, Password: (your database password)
- **Basic Knowledge**: Familiarity with Cypher query language (Neo4j's query language)

### First Steps
1. **Connect to Neo4j**: Open Neo4j Browser and enter your credentials
2. **Explore the Data**: Run basic queries to understand what's available
3. **Start with Simple Queries**: Begin with concept lookups before complex traversals

---

## 🧠 Understanding the System

### What We Have
The system contains **13.06 million concepts** organized as follows:

#### **OMOP Concepts (9.66M)**
- **Clinical Concepts**: Diagnoses, procedures, medications, measurements
- **Standardized Data**: Follows OMOP CDM 5.4 standards
- **Vocabulary Integration**: SNOMED CT, ICD-10, RxNorm, LOINC, etc.

#### **UMLS Concepts (3.4M)**
- **Biomedical Terminology**: From 200+ source vocabularies
- **Semantic Richness**: Types, definitions, synonyms, hierarchical relationships
- **Comprehensive Coverage**: All major biomedical domains

#### **Crosswalk Mappings (2.6M)**
- **Bidirectional Links**: OMOP ↔ UMLS concept connections
- **Quality Scores**: Confidence and similarity metrics
- **Mapping Types**: Direct, semantic, hierarchical relationships

### Data Structure
```
OMOPConcept ←→ CROSSWALK_MAPPING ←→ UMLSConcept
     ↓              ↓                    ↓
concept_name   confidence_score    preferred_name
domain_id      similarity_score    semantic_types
vocabulary_id  mapping_type       definitions
concept_code   mapping_method      synonyms
```

---

## 🔍 Basic Queries

### 1. Find a Specific Concept

#### **Search by Name**
```cypher
// Find OMOP concepts containing "diabetes"
MATCH (o:OMOPConcept)
WHERE o.concept_name CONTAINS 'diabetes'
RETURN o.concept_id, o.concept_name, o.domain_id, o.vocabulary_id
LIMIT 10;
```

#### **Search by CUI (UMLS)**
```cypher
// Find UMLS concept by CUI
MATCH (u:UMLSConcept {cui: 'C0011849'})
RETURN u.cui, u.preferred_name, u.semantic_types, u.definitions;
```

### 2. Explore Crosswalk Mappings

#### **Find Mappings for a Concept**
```cypher
// Find all UMLS mappings for a specific OMOP concept
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE o.concept_name CONTAINS 'myocardial infarction'
RETURN o.concept_name, u.preferred_name, m.confidence_score, m.mapping_type
ORDER BY m.confidence_score DESC;
```

#### **Find OMOP Concepts for a UMLS Term**
```cypher
// Find OMOP concepts mapped to a UMLS term
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE u.preferred_name CONTAINS 'heart attack'
RETURN o.concept_name, o.domain_id, u.preferred_name, m.confidence_score
ORDER BY m.confidence_score DESC;
```

### 3. Explore Hierarchical Relationships

#### **Find Parent Concepts**
```cypher
// Find broader concepts (parents) for a UMLS concept
MATCH (u1:UMLSConcept)-[r:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes mellitus'
AND r.relationship_type = 'RB'  // RB = Broader than
RETURN u1.preferred_name, u2.preferred_name, r.relationship_type;
```

#### **Find Child Concepts**
```cypher
// Find narrower concepts (children) for a UMLS concept
MATCH (u1:UMLSConcept)-[r:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes'
AND r.relationship_type = 'RN'  // RN = Narrower than
RETURN u1.preferred_name, u2.preferred_name, r.relationship_type
LIMIT 20;
```

---

## 🚀 Advanced Queries

### 1. Semantic Type Analysis

#### **Find Concepts by Semantic Type**
```cypher
// Find all UMLS concepts of a specific semantic type
MATCH (u:UMLSConcept)
WHERE ANY(type IN u.semantic_types WHERE type = 'Disease or Syndrome')
RETURN u.cui, u.preferred_name, u.semantic_types
LIMIT 20;
```

#### **Analyze Semantic Type Distribution**
```cypher
// Count concepts by semantic type
MATCH (u:UMLSConcept)
UNWIND u.semantic_types AS semantic_type
RETURN semantic_type, count(*) as concept_count
ORDER BY concept_count DESC
LIMIT 20;
```

### 2. Complex Relationship Traversals

#### **Multi-hop Relationships**
```cypher
// Find concepts related through multiple hops
MATCH path = (u1:UMLSConcept)-[:UMLS_RELATIONSHIP*1..3]-(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes'
AND u2.preferred_name CONTAINS 'complication'
RETURN u1.preferred_name, u2.preferred_name, length(path) as hops
ORDER BY hops;
```

#### **Relationship Path Analysis**
```cypher
// Find all paths between two concepts
MATCH path = (u1:UMLSConcept)-[:UMLS_RELATIONSHIP*]-(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes'
AND u2.preferred_name CONTAINS 'retinopathy'
RETURN u1.preferred_name, u2.preferred_name, 
       [node IN nodes(path) | node.preferred_name] as path_concepts,
       [rel IN relationships(path) | rel.relationship_type] as path_relationships
LIMIT 5;
```

### 3. Cross-Domain Analysis

#### **Vocabulary Integration**
```cypher
// Find concepts across multiple vocabularies
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE o.vocabulary_id IN ['SNOMED', 'ICD10CM', 'RxNorm']
AND m.confidence_score > 0.8
RETURN o.vocabulary_id, count(*) as concept_count
ORDER BY concept_count DESC;
```

#### **Domain Analysis**
```cypher
// Analyze concept distribution by domain
MATCH (o:OMOPConcept)
RETURN o.domain_id, count(*) as concept_count
ORDER BY concept_count DESC;
```

---

## 💡 Use Cases and Examples

### 1. Clinical Research: Phenotype Development

#### **Find All Diabetes-Related Concepts**
```cypher
// Comprehensive diabetes concept search
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE (o.concept_name CONTAINS 'diabetes' OR u.preferred_name CONTAINS 'diabetes')
AND m.confidence_score > 0.7
RETURN DISTINCT o.concept_name, o.domain_id, u.preferred_name, 
       u.semantic_types, m.confidence_score
ORDER BY m.confidence_score DESC;
```

#### **Build Disease Hierarchy**
```cypher
// Create diabetes concept hierarchy
MATCH (u1:UMLSConcept)-[r:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes'
AND r.relationship_type IN ['RB', 'RN', 'PAR', 'CHD']
RETURN u1.preferred_name, u2.preferred_name, r.relationship_type
ORDER BY u1.preferred_name, r.relationship_type;
```

### 2. Healthcare Analytics: Risk Factor Analysis

#### **Find Risk Factors for a Condition**
```cypher
// Find concepts related to diabetes risk factors
MATCH (u1:UMLSConcept)-[r:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes'
AND u2.semantic_types CONTAINS 'Risk Factor'
RETURN u1.preferred_name, u2.preferred_name, r.relationship_type;
```

#### **Analyze Comorbidity Patterns**
```cypher
// Find common comorbidities
MATCH (u1:UMLSConcept)-[r1:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
MATCH (u2:UMLSConcept)-[r2:UMLS_RELATIONSHIP]->(u3:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes'
AND r1.relationship_type = 'RO'  // Related to
AND r2.relationship_type = 'RO'
RETURN u1.preferred_name, u2.preferred_name, u3.preferred_name
LIMIT 20;
```

### 3. Drug Safety: Interaction Analysis

#### **Find Drug-Disease Relationships**
```cypher
// Find drugs related to diabetes treatment
MATCH (o1:OMOPConcept)-[m1:CROSSWALK_MAPPING]->(u1:UMLSConcept)
MATCH (o2:OMOPConcept)-[m2:CROSSWALK_MAPPING]->(u2:UMLSConcept)
WHERE o1.domain_id = 'Drug'
AND o2.domain_id = 'Condition'
AND u1.preferred_name CONTAINS 'diabetes'
AND u2.preferred_name CONTAINS 'insulin'
AND m1.confidence_score > 0.8
AND m2.confidence_score > 0.8
RETURN o1.concept_name, u1.preferred_name, o2.concept_name, u2.preferred_name;
```

### 4. Population Health: Surveillance Definitions

#### **Create Case Definition**
```cypher
// Comprehensive diabetes case definition
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE (o.concept_name CONTAINS 'diabetes' OR u.preferred_name CONTAINS 'diabetes')
AND o.domain_id = 'Condition'
AND m.confidence_score > 0.8
RETURN o.concept_id, o.concept_name, o.vocabulary_id, 
       u.preferred_name, u.semantic_types, m.confidence_score
ORDER BY m.confidence_score DESC;
```

---

## 🔧 Troubleshooting

### Common Issues

#### **No Results Returned**
```cypher
// Check if concept exists
MATCH (n)
WHERE n.concept_name CONTAINS 'your_search_term'
   OR n.preferred_name CONTAINS 'your_search_term'
RETURN labels(n), n.concept_name, n.preferred_name
LIMIT 5;
```

#### **Slow Query Performance**
```cypher
// Use EXPLAIN to analyze query
EXPLAIN MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE o.concept_name CONTAINS 'diabetes'
RETURN o.concept_name, u.preferred_name;
```

#### **Memory Issues**
- Reduce LIMIT clauses
- Use more specific WHERE conditions
- Break complex queries into smaller parts

### Query Optimization Tips

#### **Use Indexes Effectively**
```cypher
// Check available indexes
SHOW INDEXES;

// Use indexed properties in WHERE clauses
MATCH (o:OMOPConcept {vocabulary_id: 'SNOMED'})
WHERE o.concept_name CONTAINS 'diabetes'
RETURN o.concept_name;
```

#### **Limit Result Sets**
```cypher
// Always use LIMIT for exploration
MATCH (u:UMLSConcept)
WHERE u.preferred_name CONTAINS 'diabetes'
RETURN u.preferred_name, u.semantic_types
LIMIT 50;
```

---

## 📚 Best Practices

### 1. Query Design

#### **Start Simple**
- Begin with basic concept lookups
- Add complexity gradually
- Test with small result sets first

#### **Use Meaningful Names**
```cypher
// Good: Clear variable names
MATCH (diabetes:OMOPConcept)-[mapping:CROSSWALK_MAPPING]->(umls:UMLSConcept)
WHERE diabetes.concept_name CONTAINS 'diabetes'
RETURN diabetes.concept_name, umls.preferred_name, mapping.confidence_score;

// Avoid: Unclear variable names
MATCH (a)-[r]->(b)
WHERE a.concept_name CONTAINS 'diabetes'
RETURN a.concept_name, b.preferred_name, r.confidence_score;
```

### 2. Performance Considerations

#### **Efficient Traversals**
```cypher
// Good: Limit path length
MATCH path = (u1:UMLSConcept)-[:UMLS_RELATIONSHIP*1..3]-(u2:UMLSConcept)

// Avoid: Unbounded paths
MATCH path = (u1:UMLSConcept)-[:UMLS_RELATIONSHIP*]-(u2:UMLSConcept)
```

#### **Batch Processing**
- Process results in manageable chunks
- Use LIMIT and SKIP for pagination
- Consider exporting large result sets

### 3. Data Quality

#### **Validate Results**
```cypher
// Check mapping quality
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE m.confidence_score < 0.5
RETURN count(*) as low_confidence_mappings;
```

#### **Cross-Reference Verification**
```cypher
// Verify bidirectional mappings
MATCH (o:OMOPConcept)-[m1:CROSSWALK_MAPPING]->(u:UMLSConcept)
MATCH (u:UMLSConcept)-[m2:CROSSWALK_MAPPING]->(o2:OMOPConcept)
WHERE o.concept_id = o2.concept_id
RETURN o.concept_name, u.preferred_name, m1.confidence_score, m2.confidence_score;
```

---

## 📖 Learning Resources

### Cypher Query Language
- **Neo4j Cypher Manual**: https://neo4j.com/docs/cypher-manual/
- **Interactive Tutorial**: https://neo4j.com/developer/cypher/
- **Query Examples**: https://neo4j.com/developer/cypher/guide/cypher-examples/

### Biomedical Concepts
- **OMOP CDM Documentation**: https://ohdsi.github.io/CommonDataModel/
- **UMLS Documentation**: https://www.nlm.nih.gov/research/umls/
- **SNOMED CT**: https://www.snomed.org/

### Advanced Topics
- **Graph Algorithms**: https://neo4j.com/docs/graph-algorithms/
- **Machine Learning**: https://neo4j.com/docs/graph-data-science/
- **Data Visualization**: https://neo4j.com/docs/neo4j-browser-manual/

---

## 📞 Getting Help

### Support Resources
- **System Documentation**: Refer to `COMPLETE_SYSTEM_DOCUMENTATION.md`
- **Technical Guide**: Refer to `TECHNICAL_IMPLEMENTATION_GUIDE.md`
- **Code Repository**: Check source code and examples
- **Community Forums**: OHDSI and Neo4j communities

### Common Questions

#### **Q: How do I find all concepts related to a specific disease?**
A: Use the crosswalk mappings and UMLS relationships:
```cypher
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE u.preferred_name CONTAINS 'disease_name'
RETURN o.concept_name, u.preferred_name, m.confidence_score;
```

#### **Q: How can I validate the quality of mappings?**
A: Check confidence scores and use multiple mapping strategies:
```cypher
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE m.confidence_score > 0.8
RETURN count(*) as high_quality_mappings;
```

#### **Q: What's the difference between OMOP and UMLS concepts?**
A: OMOP provides standardized clinical data structures, while UMLS provides comprehensive biomedical terminology with semantic richness.

---

*User Manual v1.0*  
*Last Updated: December 2024*  
*For technical support, refer to the Technical Implementation Guide.*
