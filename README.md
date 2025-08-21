# OMOP-UMLS Crosswalk System 🧬🔗

A comprehensive biomedical knowledge integration system that creates a unified crosswalk between the OMOP Common Data Model (CDM) and the Unified Medical Language System (UMLS), preserving full semantic richness and enabling advanced clinical research and healthcare analytics.

## 🎯 Project Overview

The OMOP-UMLS Crosswalk System represents a breakthrough in biomedical knowledge integration, combining the standardized clinical data structures of OMOP CDM 5.4 with the comprehensive semantic richness of UMLS. This system creates a unified knowledge graph that enables researchers and clinicians to leverage the full power of both systems in a single, queryable interface.

### Key Features
- **Complete Integration**: 9.66M OMOP + 3.4M UMLS concepts
- **Semantic Preservation**: 100% UMLS semantic types, definitions, and hierarchical relationships
- **Crosswalk Mappings**: 2.6M validated mappings between systems
- **Knowledge Graph**: 17.8M UMLS relationships + 2.6M crosswalk relationships
- **Production Ready**: Robust error handling, batch processing, and Neo4j persistence

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Neo4j 4.4+ Enterprise Edition
- 16GB+ RAM (32GB+ recommended)
- 100GB+ available storage

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd omop-umls-crosswalk

# Create virtual environment
python3 -m venv omop_umls_env
source omop_umls_env/bin/activate  # Linux/macOS
# or
omop_umls_env\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_production.txt

# Configure environment
cp env_template.txt .env
# Edit .env with your Neo4j credentials
```

### Basic Usage
```python
# Test Neo4j connection
python test_neo4j_connection.py

# Run complete integration
python robust_neo4j_integration.py

# Explore the knowledge graph
# Open Neo4j Browser at http://localhost:7474
```

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OMOP CDM     │    │   UMLS RRF      │    │   BioPortal     │
│   (9.66M)      │    │   (3.4M)        │    │   Ontologies    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CROSSWALK ENGINE                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   Direct    │  │   Semantic  │  │  Hierarchical│           │
│  │   Mapping   │  │  Similarity │  │   Mapping   │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE GRAPH                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │   OMOP      │  │   UMLS      │  │ Crosswalk   │           │
│  │  Concepts   │  │  Concepts   │  │ Mappings    │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NEO4J PERSISTENCE                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│  │  Constraints│  │   Indexes   │  │  Graph      │           │
│  │             │  │             │  │  Algorithms │           │
│  └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## 🔬 Scientific Foundation

### OMOP Common Data Model (CDM)
- **Purpose**: Standardized data model for observational health data
- **Version**: 5.4 (latest approved version)
- **Scope**: Clinical concepts, procedures, medications, conditions, measurements
- **Reference**: OHDSI (Observational Health Data Sciences and Informatics)

### Unified Medical Language System (UMLS)
- **Purpose**: Comprehensive biomedical terminology and ontology repository
- **Components**: Metathesaurus (3.4M concepts), Semantic Network, SPECIALIST Lexicon
- **Semantic Richness**: Hierarchical relationships, definitions, synonyms, semantic types
- **Reference**: National Library of Medicine (NLM)

### Crosswalk Methodology
- **Direct CUI Mapping**: Exact concept identifier matches
- **String Similarity**: TF-IDF and cosine similarity algorithms
- **Hierarchical Mapping**: Parent-child relationship preservation
- **Vocabulary Prioritization**: OMOP2OBO knowledge integration
- **Confidence Scoring**: Multi-factor mapping quality assessment

## 📁 Project Structure

```
omop-umls-crosswalk/
├── 📚 Core Components/
│   ├── omop_cdm_processor.py          # OMOP CDM data processor
│   ├── umls_omop_mapper.py            # Multi-strategy mapping engine
│   ├── omop_umls_integrator.py        # Knowledge graph construction
│   └── robust_neo4j_integration.py    # Production Neo4j integration
├── ⚡ Optimization/
│   ├── production_optimizer.py         # GRAPE-style optimization
│   ├── persistent_infrastructure.py    # Caching and persistence
│   └── complete_production_setup.py    # Production orchestration
├── 🔗 Crosswalk Generation/
│   ├── create_complete_crosswalk.py    # Complete crosswalk creation
│   └── COMPLETE_PRODUCTION_CROSSWALK/  # Generated mappings
├── 📊 Data Processing/
│   ├── process_complete_omop.py        # OMOP CDM processing
│   └── complete_omop_processed.pkl     # Processed OMOP data
├── 📖 Documentation/
│   ├── COMPLETE_SYSTEM_DOCUMENTATION.md    # Comprehensive technical docs
│   ├── TECHNICAL_IMPLEMENTATION_GUIDE.md   # Developer guide
│   ├── USER_MANUAL.md                      # End-user manual
│   └── README.md                           # This file
├── ⚙️ Configuration/
│   ├── requirements.txt                   # Core dependencies
│   ├── requirements_production.txt        # Production dependencies
│   ├── env_template.txt                   # Environment template
│   └── .env                              # Environment variables
└── 🧪 Testing and Validation/
    ├── test_neo4j_connection.py          # Connection testing
    ├── check_umls_richness.py            # Data validation
    └── examine_production_results.py      # Results analysis
```

## 💡 Use Cases

### Clinical Research
- **Phenotype Development**: Standardized definitions with semantic enrichment
- **Data Harmonization**: Multi-institutional study standardization
- **Cross-Validation**: Multi-source concept verification

### Healthcare Analytics
- **Clinical Decision Support**: Diagnosis mapping and treatment planning
- **Population Health**: Disease surveillance and outcome analysis
- **Risk Assessment**: Factor-to-risk relationship analysis

### Biomedical Informatics
- **Knowledge Discovery**: Novel association identification
- **Natural Language Processing**: Biomedical concept recognition
- **Semantic Networks**: Meaningful relationship analysis

### Regulatory Compliance
- **Standards Compliance**: CDISC, HL7 FHIR, ICD-10/11, SNOMED CT
- **Audit and Validation**: Automated quality assessment
- **Change Tracking**: Concept evolution monitoring

## 🔍 Query Examples

### Basic Concept Search
```cypher
// Find OMOP concepts containing "diabetes"
MATCH (o:OMOPConcept)
WHERE o.concept_name CONTAINS 'diabetes'
RETURN o.concept_id, o.concept_name, o.domain_id, o.vocabulary_id
LIMIT 10;
```

### Crosswalk Exploration
```cypher
// Find UMLS mappings for a concept
MATCH (o:OMOPConcept)-[m:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE o.concept_name CONTAINS 'myocardial infarction'
RETURN o.concept_name, u.preferred_name, m.confidence_score, m.mapping_type
ORDER BY m.confidence_score DESC;
```

### Hierarchical Analysis
```cypher
// Find parent concepts
MATCH (u1:UMLSConcept)-[r:UMLS_RELATIONSHIP]->(u2:UMLSConcept)
WHERE u1.preferred_name CONTAINS 'diabetes mellitus'
AND r.relationship_type = 'RB'  // Broader than
RETURN u1.preferred_name, u2.preferred_name, r.relationship_type;
```

## 📈 Performance Characteristics

### Processing Times
- **OMOP Concepts**: ~15 minutes (9.66M concepts)
- **UMLS Concepts**: ~45 minutes (3.4M concepts)
- **UMLS Relationships**: ~2 hours (17.8M relationships)
- **Crosswalk Mappings**: ~30 minutes (2.6M mappings)
- **Total Integration**: ~3.5 hours

### Memory Usage
- **Peak Memory**: 8-12GB during processing
- **Neo4j Database**: 15-25GB storage
- **Cache Files**: 5-10GB temporary storage

### Query Performance
- **Concept Lookup**: <10ms for indexed properties
- **Relationship Traversal**: <100ms for 3-hop paths
- **Semantic Search**: <500ms for complex queries
- **Crosswalk Queries**: <50ms for mapping lookups

## 🚀 Getting Started

### 1. System Setup
1. **Install Dependencies**: Follow installation instructions above
2. **Configure Neo4j**: Create database instance and set credentials
3. **Environment Setup**: Configure .env file with your settings

### 2. Data Processing
1. **Download OMOP CDM**: Get data from ATHENA (https://athena.ohdsi.org/)
2. **Verify UMLS Data**: Ensure UMLS knowledge graph is available
3. **Run Integration**: Execute robust_neo4j_integration.py

### 3. Exploration
1. **Open Neo4j Browser**: Navigate to http://localhost:7474
2. **Run Sample Queries**: Start with basic concept searches
3. **Build Complex Queries**: Explore relationships and hierarchies

## 📚 Documentation

### For Users
- **[User Manual](USER_MANUAL.md)**: End-user guide with query examples
- **[System Documentation](COMPLETE_SYSTEM_DOCUMENTATION.md)**: Comprehensive technical overview

### For Developers
- **[Technical Implementation Guide](TECHNICAL_IMPLEMENTATION_GUIDE.md)**: Setup, configuration, and troubleshooting
- **[Code Repository**: Source code with inline documentation

### For Researchers
- **Scientific Foundation**: Detailed methodology and validation
- **Use Cases**: Real-world application examples
- **Performance Metrics**: System capabilities and limitations

## 🤝 Contributing

We welcome contributions from the biomedical and informatics communities! Please see our contributing guidelines for:

- **Bug Reports**: Issues and problems
- **Feature Requests**: New functionality ideas
- **Code Contributions**: Pull requests and improvements
- **Documentation**: Updates and clarifications

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **OHDSI Community**: For OMOP CDM development and support
- **National Library of Medicine**: For UMLS terminology resources
- **Neo4j**: For graph database technology and support
- **Open Source Community**: For the many libraries and tools used

## 📞 Support

### Getting Help
- **Documentation**: Start with the user manual and technical guide
- **Issues**: Report problems through the issue tracker
- **Community**: Join OHDSI and Neo4j community forums
- **Research**: Refer to scientific literature and standards

### Contact Information
- **Project Repository**: [GitHub Repository URL]
- **Documentation**: [Documentation URL]
- **Community**: [Community Forum URL]

---

## 🎉 What We've Accomplished

This system represents a significant advancement in biomedical knowledge integration:

✅ **Complete Integration**: Full coverage of both OMOP and UMLS systems  
✅ **Semantic Preservation**: 100% UMLS richness maintained  
✅ **Production Ready**: Robust, scalable, and maintainable  
✅ **Standards Compliant**: Healthcare data standards adherence  
✅ **Research Enabled**: Foundation for advanced clinical research  

**The OMOP-UMLS Crosswalk System bridges the gap between research and clinical practice, enabling researchers and clinicians to leverage the full power of both knowledge systems in a unified, queryable knowledge graph.**

---

*Project Version: 1.0*  
*Last Updated: December 2024*  
*System Version: OMOP CDM 5.4 + UMLS 2024*  
*For questions and support, refer to the documentation or create an issue in the repository.*
