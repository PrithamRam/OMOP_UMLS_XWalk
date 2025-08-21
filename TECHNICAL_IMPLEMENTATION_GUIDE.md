# OMOP-UMLS Crosswalk System: Technical Implementation Guide

## 📋 Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation and Setup](#installation-and-setup)
3. [Configuration](#configuration)
4. [Data Processing Pipeline](#data-processing-pipeline)
5. [Neo4j Integration](#neo4j-integration)
6. [Performance Optimization](#performance-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)

---

## 🖥️ System Requirements

### Hardware Requirements
- **CPU**: Multi-core processor (8+ cores recommended)
- **Memory**: Minimum 16GB RAM, 32GB+ recommended
- **Storage**: 100GB+ available space
- **Network**: Stable internet connection for data downloads

### Software Requirements
- **Operating System**: macOS 12+, Ubuntu 20.04+, Windows 10+
- **Python**: 3.8+ with pip support
- **Neo4j**: 4.4+ Enterprise Edition
- **Java**: OpenJDK 11+ (for Neo4j)

### Dependencies
```bash
# Core Python packages
pandas>=1.5.0
numpy>=1.21.0
networkx>=2.8.0
scikit-learn>=1.1.0

# Neo4j integration
neo4j>=5.0.0

# Data processing
pickle5>=0.0.11
psutil>=5.9.0

# Environment management
python-dotenv>=0.19.0
```

---

## 🚀 Installation and Setup

### 1. Environment Setup
```bash
# Clone or download the project
cd /path/to/project

# Create virtual environment
python3 -m venv omop_umls_env

# Activate environment
source omop_umls_env/bin/activate  # Linux/macOS
# or
omop_umls_env\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_production.txt
```

### 2. Neo4j Setup
```bash
# Download Neo4j Desktop from https://neo4j.com/download/
# Create new database instance: "OMOP-UMLS Crosswalk"
# Set password and note it for .env file
```

### 3. Environment Configuration
```bash
# Create .env file
cp env_template.txt .env

# Edit .env with your settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
OPENAI_API_KEY=your_openai_key_here
```

---

## ⚙️ Configuration

### Core Configuration Files

#### `omop_cdm_processor.py` Configuration
```python
@dataclass
class OMOPConfig:
    chunk_size: int = 50000
    max_workers: int = mp.cpu_count()
    memory_limit_gb: float = 8.0
    enable_parallel: bool = True
    cache_results: bool = True
    output_format: str = 'pickle'
    quality_threshold: float = 0.8
```

#### `umls_omop_mapper.py` Configuration
```python
@dataclass
class MappingConfig:
    similarity_threshold: float = 0.7
    confidence_threshold: float = 0.8
    max_candidates: int = 10
    enable_fuzzy_matching: bool = True
    enable_semantic_similarity: bool = True
    enable_hierarchical_mapping: bool = True
    batch_size: int = 1000
```

### Environment Variables
```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# OpenAI Configuration (optional)
OPENAI_API_KEY=your_api_key

# Processing Configuration
BATCH_SIZE=1000
MAX_WORKERS=8
MEMORY_LIMIT_GB=16
```

---

## 📊 Data Processing Pipeline

### 1. OMOP CDM Data Preparation

#### Download OMOP CDM 5.4
```bash
# Visit ATHENA: https://athena.ohdsi.org/
# Download CONCEPT.csv, VOCABULARY.csv, DOMAIN.csv
# Note: Files are tab-separated, not comma-separated
```

#### Process OMOP Data
```python
from omop_cdm_processor import OMOPCDMProcessor

# Initialize processor
processor = OMOPCDMProcessor()

# Process concepts
concepts = processor.process_concepts('CONCEPT.csv')

# Save processed data
processor.save_processed_data(concepts, 'complete_omop_processed.pkl')
```

### 2. UMLS Data Preparation

#### Load UMLS Knowledge Graph
```python
# Ensure you have the UMLS knowledge graph from RAG Literature work
umls_graph_path = "/path/to/RAG Literature/RRF FILES/full_scale_output/full_scale_knowledge_graph.pkl"

# Verify the file exists and contains the expected data
import pickle
with open(umls_graph_path, 'rb') as f:
    umls_graph = pickle.load(f)
    
print(f"UMLS Graph: {umls_graph.number_of_nodes():,} nodes, {umls_graph.number_of_edges():,} edges")
```

### 3. Crosswalk Generation

#### Generate Mappings
```python
from create_complete_crosswalk import create_production_scale_mappings

# Load data
omop_concepts = load_omop_concepts()
umls_concepts = load_umls_concepts()

# Generate mappings
mappings = create_production_scale_mappings(
    omop_concepts, 
    umls_concepts, 
    max_mappings=None  # No limit for complete mapping
)

# Save mappings
save_complete_crosswalk(mappings, 'COMPLETE_PRODUCTION_CROSSWALK/')
```

---

## 🗄️ Neo4j Integration

### 1. Database Preparation

#### Start Neo4j Instance
```bash
# In Neo4j Desktop:
# 1. Start "OMOP-UMLS Crosswalk" database
# 2. Verify connection at http://localhost:7474
# 3. Default credentials: neo4j/your_password
```

#### Test Connection
```python
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "your_password"))

# Test connection
with driver.session() as session:
    result = session.run("RETURN 1 as test")
    print("Connection successful!")
```

### 2. Data Loading

#### Run Complete Integration
```python
# Use the robust integration script
python robust_neo4j_integration.py
```

#### Monitor Progress
```bash
# The script provides real-time progress updates:
# - OMOP concepts: 1000 concepts per batch
# - UMLS concepts: 1000 concepts per batch  
# - UMLS relationships: 2000 relationships per batch
# - Crosswalk mappings: 2000 mappings per batch
```

### 3. Verification Queries

#### Check Data Integrity
```cypher
// Count total nodes
MATCH (n) RETURN labels(n) as node_type, count(n) as count ORDER BY count DESC;

// Count relationships
MATCH ()-[r]->() RETURN type(r) as rel_type, count(r) as count ORDER BY count DESC;

// Verify UMLS semantic richness
MATCH (u:UMLSConcept) 
WHERE u.semantic_types IS NOT NULL AND size(u.semantic_types) > 0
RETURN count(u) as concepts_with_semantic_types;
```

---

## ⚡ Performance Optimization

### 1. Memory Management

#### Batch Size Optimization
```python
# For large datasets, use smaller batch sizes
BATCH_SIZE = 1000  # Default
BATCH_SIZE = 500   # For memory-constrained systems
BATCH_SIZE = 2000  # For high-memory systems
```

#### Memory Monitoring
```python
import psutil

def check_memory_usage():
    memory = psutil.virtual_memory()
    print(f"Memory usage: {memory.percent}%")
    print(f"Available: {memory.available / 1024**3:.1f} GB")
    
    if memory.percent > 80:
        print("⚠️  High memory usage detected")
```

### 2. Neo4j Performance

#### Index Creation
```cypher
// Create indexes for common query patterns
CREATE INDEX omop_concept_name IF NOT EXISTS FOR (c:OMOPConcept) ON (c.concept_name);
CREATE INDEX umls_preferred_name IF NOT EXISTS FOR (c:UMLSConcept) ON (c.preferred_name);
CREATE INDEX vocabulary_id IF NOT EXISTS FOR (c:OMOPConcept) ON (c.vocabulary_id);
CREATE INDEX domain_id IF NOT EXISTS FOR (c:OMOPConcept) ON (c.domain_id);
```

#### Constraint Optimization
```cypher
// Create constraints for data integrity
CREATE CONSTRAINT omop_concept_id IF NOT EXISTS FOR (c:OMOPConcept) REQUIRE c.concept_id IS UNIQUE;
CREATE CONSTRAINT umls_cui IF NOT EXISTS FOR (c:UMLSConcept) REQUIRE c.cui IS UNIQUE;
```

### 3. Parallel Processing

#### Worker Configuration
```python
import multiprocessing as mp

# Use available CPU cores
MAX_WORKERS = mp.cpu_count()

# For memory-constrained systems
MAX_WORKERS = min(mp.cpu_count(), 4)

# For high-performance systems
MAX_WORKERS = mp.cpu_count() * 2
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Neo4j Connection Issues
```bash
# Problem: Connection refused
# Solution: Check if Neo4j is running
ps aux | grep neo4j

# Problem: Authentication failed
# Solution: Verify password in .env file
cat .env | grep NEO4J_PASSWORD
```

#### 2. Memory Issues
```bash
# Problem: Out of memory during processing
# Solution: Reduce batch size
export BATCH_SIZE=500

# Problem: Neo4j memory pool exhausted
# Solution: Increase Neo4j heap size in neo4j.conf
dbms.memory.heap.initial_size=2G
dbms.memory.heap.max_size=4G
```

#### 3. Data Processing Issues
```bash
# Problem: OMOP CSV parsing errors
# Solution: Verify file format (tab-separated)
head -5 CONCEPT.csv

# Problem: UMLS graph loading fails
# Solution: Check file path and permissions
ls -la /path/to/umls_graph.pkl
```

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable verbose output in scripts
VERBOSE = True
DEBUG_MODE = True
```

---

## 📊 Monitoring and Maintenance

### 1. System Monitoring

#### Performance Metrics
```python
# Monitor processing progress
def log_progress(current, total, stage):
    percentage = (current / total) * 100
    print(f"{stage}: {current:,}/{total:,} ({percentage:.1f}%)")
    
    # Log to file
    with open('processing.log', 'a') as f:
        f.write(f"{datetime.now()}: {stage} - {percentage:.1f}%\n")
```

#### Resource Monitoring
```python
# Monitor system resources
def monitor_resources():
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    print(f"CPU: {cpu_percent}%")
    print(f"Memory: {memory.percent}%")
    print(f"Disk: {disk.percent}%")
```

### 2. Data Maintenance

#### Regular Backups
```bash
# Backup Neo4j database
neo4j-admin backup --database=neo4j --backup-dir=/backup/path

# Backup processed data files
tar -czf omop_umls_backup_$(date +%Y%m%d).tar.gz \
    complete_omop_processed.pkl \
    COMPLETE_PRODUCTION_CROSSWALK/
```

#### Data Validation
```python
# Regular data integrity checks
def validate_data_integrity():
    # Check Neo4j constraints
    # Verify mapping quality
    # Validate semantic richness preservation
    pass
```

### 3. Performance Tuning

#### Query Optimization
```cypher
// Use EXPLAIN to analyze query performance
EXPLAIN MATCH (o:OMOPConcept)-[:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE o.concept_name CONTAINS 'diabetes'
RETURN o.concept_name, u.preferred_name LIMIT 10;

// Use PROFILE to see actual execution
PROFILE MATCH (o:OMOPConcept)-[:CROSSWALK_MAPPING]->(u:UMLSConcept)
WHERE o.concept_name CONTAINS 'diabetes'
RETURN o.concept_name, u.preferred_name LIMIT 10;
```

#### Index Optimization
```cypher
// Monitor index usage
SHOW INDEXES;

// Drop unused indexes
DROP INDEX index_name;

// Create composite indexes for complex queries
CREATE INDEX omop_vocab_domain IF NOT EXISTS 
FOR (c:OMOPConcept) ON (c.vocabulary_id, c.domain_id);
```

---

## 📝 Best Practices

### 1. Development Workflow
- Use virtual environments for dependency isolation
- Test with small datasets before full-scale processing
- Implement proper error handling and logging
- Use configuration files for environment-specific settings

### 2. Production Deployment
- Monitor system resources continuously
- Implement automated backup procedures
- Use production-grade Neo4j configuration
- Set up alerting for system issues

### 3. Data Quality
- Validate input data before processing
- Implement data quality checks throughout the pipeline
- Monitor mapping quality metrics
- Regular data integrity validation

### 4. Performance
- Use appropriate batch sizes for your system
- Monitor memory usage and adjust accordingly
- Optimize Neo4j queries with proper indexing
- Implement caching for frequently accessed data

---

*Technical Implementation Guide v1.0*  
*Last Updated: December 2024*  
*For technical support, refer to the troubleshooting section or create an issue in the project repository.*
