#!/usr/bin/env python3
"""
Critical Backup Archive Creator for OMOP-UMLS Crosswalk System
Creates comprehensive backups of all critical assets
"""

import os
import shutil
import tarfile
import zipfile
import json
import pickle
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class CriticalBackupCreator:
    """Creates comprehensive backups of all critical system assets"""
    
    def __init__(self):
        """Initialize backup creator"""
        self.backup_dir = Path("CRITICAL_BACKUP_ARCHIVE")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_name = f"OMOP_UMLS_CRITICAL_BACKUP_{self.timestamp}"
        self.backup_path = self.backup_dir / self.backup_name
        
        # Create backup directory
        self.backup_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Creating critical backup: {self.backup_name}")
        print(f"📁 Backup location: {self.backup_path}")
    
    def create_backup_manifest(self):
        """Create a manifest of all backup contents"""
        manifest = {
            "backup_info": {
                "timestamp": self.timestamp,
                "backup_name": self.backup_name,
                "system": "OMOP-UMLS Crosswalk System",
                "version": "1.0",
                "description": "Critical backup of all system assets"
            },
            "backup_contents": {
                "data_files": [],
                "documentation": [],
                "configuration": [],
                "scripts": [],
                "neo4j_backup": None
            },
            "system_stats": {},
            "restore_instructions": []
        }
        
        return manifest
    
    def backup_data_files(self, manifest):
        """Backup all critical data files"""
        print("\n📊 Backing up critical data files...")
        
        data_backup_dir = self.backup_path / "DATA_FILES"
        data_backup_dir.mkdir(exist_ok=True)
        
        # 1. OMOP processed data
        if os.path.exists("complete_omop_processed.pkl"):
            print("   📁 Backing up OMOP processed data...")
            shutil.copy2("complete_omop_processed.pkl", data_backup_dir / "complete_omop_processed.pkl")
            manifest["backup_contents"]["data_files"].append("complete_omop_processed.pkl")
            
            # Get file size info
            file_size = os.path.getsize("complete_omop_processed.pkl") / (1024**3)  # GB
            print(f"      ✅ OMOP data backed up ({file_size:.2f} GB)")
        
        # 2. Crosswalk data
        if os.path.exists("COMPLETE_PRODUCTION_CROSSWALK"):
            print("   📁 Backing up crosswalk data...")
            crosswalk_backup = data_backup_dir / "COMPLETE_PRODUCTION_CROSSWALK"
            shutil.copytree("COMPLETE_PRODUCTION_CROSSWALK", crosswalk_backup, dirs_exist_ok=True)
            manifest["backup_contents"]["data_files"].append("COMPLETE_PRODUCTION_CROSSWALK/")
            
            # Count files and get size
            file_count = len(list(crosswalk_backup.rglob("*")))
            print(f"      ✅ Crosswalk data backed up ({file_count} files)")
        
        # 3. Any other critical data files
        critical_data_files = [
            "complete_omop_processed.pkl",
            "COMPLETE_PRODUCTION_CROSSWALK/",
            "*.pkl",  # Any other pickle files
            "*.csv",  # Any other CSV files
            "*.json"  # Any other JSON files
        ]
        
        for pattern in critical_data_files:
            if "*" in pattern:
                # Handle wildcard patterns
                import glob
                for file_path in glob.glob(pattern):
                    if os.path.isfile(file_path) and file_path not in manifest["backup_contents"]["data_files"]:
                        print(f"   📁 Backing up additional file: {file_path}")
                        shutil.copy2(file_path, data_backup_dir / os.path.basename(file_path))
                        manifest["backup_contents"]["data_files"].append(file_path)
        
        return manifest
    
    def backup_documentation(self, manifest):
        """Backup all documentation files"""
        print("\n📚 Backing up documentation...")
        
        docs_backup_dir = self.backup_path / "DOCUMENTATION"
        docs_backup_dir.mkdir(exist_ok=True)
        
        # Documentation files to backup
        doc_files = [
            "COMPLETE_SYSTEM_DOCUMENTATION.md",
            "TECHNICAL_IMPLEMENTATION_GUIDE.md",
            "USER_MANUAL.md",
            "README.md",
            "demo_system_capabilities.py"
        ]
        
        for doc_file in doc_files:
            if os.path.exists(doc_file):
                print(f"   📄 Backing up: {doc_file}")
                shutil.copy2(doc_file, docs_backup_dir / doc_file)
                manifest["backup_contents"]["documentation"].append(doc_file)
        
        print(f"      ✅ Documentation backed up ({len(manifest['backup_contents']['documentation'])} files)")
        return manifest
    
    def backup_configuration(self, manifest):
        """Backup configuration files"""
        print("\n⚙️ Backing up configuration...")
        
        config_backup_dir = self.backup_path / "CONFIGURATION"
        config_backup_dir.mkdir(exist_ok=True)
        
        # Configuration files to backup
        config_files = [
            "requirements.txt",
            "requirements_production.txt",
            "env_template.txt",
            ".env"  # Be careful with this - contains sensitive info
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                print(f"   ⚙️ Backing up: {config_file}")
                shutil.copy2(config_file, config_backup_dir / config_file)
                manifest["backup_contents"]["configuration"].append(config_file)
        
        print(f"      ✅ Configuration backed up ({len(manifest['backup_contents']['configuration'])} files)")
        return manifest
    
    def backup_scripts(self, manifest):
        """Backup all Python scripts"""
        print("\n🐍 Backing up Python scripts...")
        
        scripts_backup_dir = self.backup_path / "SCRIPTS"
        scripts_backup_dir.mkdir(exist_ok=True)
        
        # Python scripts to backup
        script_files = [
            "omop_cdm_processor.py",
            "umls_omop_mapper.py",
            "omop_umls_integrator.py",
            "robust_neo4j_integration.py",
            "production_optimizer.py",
            "persistent_infrastructure.py",
            "complete_production_setup.py",
            "create_complete_crosswalk.py",
            "enhanced_neo4j_integration.py",
            "check_umls_richness.py"
        ]
        
        for script_file in script_files:
            if os.path.exists(script_file):
                print(f"   🐍 Backing up: {script_file}")
                shutil.copy2(script_file, scripts_backup_dir / script_file)
                manifest["backup_contents"]["scripts"].append(script_file)
        
        print(f"      ✅ Scripts backed up ({len(manifest['backup_contents']['scripts'])} files)")
        return manifest
    
    def backup_neo4j_info(self, manifest):
        """Backup Neo4j database information and connection details"""
        print("\n🗄️ Backing up Neo4j information...")
        
        neo4j_backup_dir = self.backup_path / "NEO4J_INFO"
        neo4j_backup_dir.mkdir(exist_ok=True)
        
        # Create Neo4j connection info file
        neo4j_info = {
            "database_name": "OMOP-UMLS Crosswalk",
            "connection_uri": os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            "username": os.getenv('NEO4J_USER', 'neo4j'),
            "backup_instructions": [
                "1. Stop the Neo4j database instance",
                "2. Run: neo4j-admin backup --database=neo4j --backup-dir=/backup/path",
                "3. Restart the database instance"
            ],
            "restore_instructions": [
                "1. Stop the Neo4j database instance",
                "2. Run: neo4j-admin restore --database=neo4j --from=/backup/path",
                "3. Restart the database instance"
            ]
        }
        
        with open(neo4j_backup_dir / "neo4j_backup_info.json", 'w') as f:
            json.dump(neo4j_info, f, indent=2)
        
        manifest["backup_contents"]["neo4j_backup"] = "neo4j_backup_info.json"
        print("      ✅ Neo4j information backed up")
        
        return manifest
    
    def create_system_stats(self, manifest):
        """Create system statistics for the backup"""
        print("\n📈 Creating system statistics...")
        
        stats = {}
        
        # Data file statistics
        if os.path.exists("complete_omop_processed.pkl"):
            try:
                with open("complete_omop_processed.pkl", 'rb') as f:
                    omop_data = pickle.load(f)
                stats["omop_concepts"] = len(omop_data.get('concepts', []))
            except:
                stats["omop_concepts"] = "Unknown"
        
        # Crosswalk statistics
        if os.path.exists("COMPLETE_PRODUCTION_CROSSWALK/COMPLETE_OMOP_UMLS_CROSSWALK.csv"):
            try:
                df = pd.read_csv("COMPLETE_PRODUCTION_CROSSWALK/COMPLETE_OMOP_UMLS_CROSSWALK.csv", low_memory=False)
                stats["crosswalk_mappings"] = len(df)
            except:
                stats["crosswalk_mappings"] = "Unknown"
        
        # File system statistics
        stats["backup_timestamp"] = self.timestamp
        stats["total_files_backed_up"] = (
            len(manifest["backup_contents"]["data_files"]) +
            len(manifest["backup_contents"]["documentation"]) +
            len(manifest["backup_contents"]["configuration"]) +
            len(manifest["backup_contents"]["scripts"])
        )
        
        manifest["system_stats"] = stats
        print(f"      ✅ System statistics created")
        
        return manifest
    
    def create_restore_instructions(self, manifest):
        """Create comprehensive restore instructions"""
        print("\n📋 Creating restore instructions...")
        
        restore_instructions = [
            "OMOP-UMLS CROSSWALK SYSTEM RESTORE INSTRUCTIONS",
            "=" * 50,
            "",
            "1. SYSTEM SETUP:",
            "   - Install Python 3.8+ and create virtual environment",
            "   - Install dependencies: pip install -r requirements.txt",
            "   - Install production dependencies: pip install -r requirements_production.txt",
            "",
            "2. NEO4J SETUP:",
            "   - Install Neo4j Desktop and create 'OMOP-UMLS Crosswalk' instance",
            "   - Configure .env file with Neo4j credentials",
            "   - Restore Neo4j database from backup if available",
            "",
            "3. DATA RESTORATION:",
            "   - Copy complete_omop_processed.pkl to project root",
            "   - Copy COMPLETE_PRODUCTION_CROSSWALK/ to project root",
            "   - Verify all data files are present",
            "",
            "4. SYSTEM VERIFICATION:",
            "   - Run: python test_neo4j_connection.py",
            "   - Run: python demo_system_capabilities.py",
            "   - Verify data integrity in Neo4j Browser",
            "",
            "5. TROUBLESHOOTING:",
            "   - Check .env file configuration",
            "   - Verify Neo4j instance is running",
            "   - Check file permissions and paths",
            "",
            "For detailed instructions, refer to TECHNICAL_IMPLEMENTATION_GUIDE.md"
        ]
        
        manifest["restore_instructions"] = restore_instructions
        
        # Write restore instructions to file
        with open(self.backup_path / "RESTORE_INSTRUCTIONS.txt", 'w') as f:
            f.write('\n'.join(restore_instructions))
        
        print("      ✅ Restore instructions created")
        return manifest
    
    def create_backup_archive(self, manifest):
        """Create compressed archive of the backup"""
        print("\n🗜️ Creating compressed backup archive...")
        
        # Save manifest
        with open(self.backup_path / "BACKUP_MANIFEST.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create tar.gz archive
        archive_name = f"{self.backup_name}.tar.gz"
        archive_path = self.backup_dir / archive_name
        
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(self.backup_path, arcname=self.backup_name)
        
        # Create ZIP archive as alternative
        zip_name = f"{self.backup_name}.zip"
        zip_path = self.backup_dir / zip_name
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.backup_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.backup_path)
                    zipf.write(file_path, arcname)
        
        print(f"      ✅ Backup archive created: {archive_name}")
        print(f"      ✅ ZIP archive created: {zip_name}")
        
        return archive_path, zip_path
    
    def create_backup_summary(self, manifest, archive_path, zip_path):
        """Create a summary of the backup"""
        print("\n📋 Creating backup summary...")
        
        summary = f"""
OMOP-UMLS CROSSWALK SYSTEM - CRITICAL BACKUP SUMMARY
{'='*60}

Backup Information:
- Backup Name: {manifest['backup_info']['backup_name']}
- Timestamp: {manifest['backup_info']['timestamp']}
- System Version: {manifest['backup_info']['version']}

Backup Contents:
- Data Files: {len(manifest['backup_contents']['data_files'])} items
- Documentation: {len(manifest['backup_contents']['documentation'])} files
- Configuration: {len(manifest['backup_contents']['configuration'])} files
- Scripts: {len(manifest['backup_contents']['scripts'])} files
- Neo4j Info: {manifest['backup_contents']['neo4j_backup']}

System Statistics:
- OMOP Concepts: {manifest['system_stats'].get('omop_concepts', 'Unknown')}
- Crosswalk Mappings: {manifest['system_stats'].get('crosswalk_mappings', 'Unknown')}
- Total Files Backed Up: {manifest['system_stats'].get('total_files_backed_up', 'Unknown')}

Archive Files Created:
- TAR.GZ: {archive_path.name}
- ZIP: {zip_path.name}

Backup Location: {self.backup_path}

IMPORTANT: Store these archive files in a safe location!
You can restore the entire system from these archives.
"""
        
        # Write summary to file
        with open(self.backup_path / "BACKUP_SUMMARY.txt", 'w') as f:
            f.write(summary)
        
        print("      ✅ Backup summary created")
        return summary
    
    def run_complete_backup(self):
        """Run the complete backup process"""
        print("🚀 Starting complete critical backup process...")
        
        # Create manifest
        manifest = self.create_backup_manifest()
        
        # Backup all components
        manifest = self.backup_data_files(manifest)
        manifest = self.backup_documentation(manifest)
        manifest = self.backup_configuration(manifest)
        manifest = self.backup_scripts(manifest)
        manifest = self.backup_neo4j_info(manifest)
        
        # Create additional information
        manifest = self.create_system_stats(manifest)
        manifest = self.create_restore_instructions(manifest)
        
        # Create archives
        archive_path, zip_path = self.create_backup_archive(manifest)
        
        # Create summary
        summary = self.create_backup_summary(manifest, archive_path, zip_path)
        
        print("\n" + "="*60)
        print("🎉 CRITICAL BACKUP COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(summary)
        
        print("\n💾 BACKUP FILES CREATED:")
        print(f"   📁 Full Backup Directory: {self.backup_path}")
        print(f"   🗜️ Compressed Archive: {archive_path}")
        print(f"   📦 ZIP Archive: {zip_path}")
        
        print("\n🚨 CRITICAL NEXT STEPS:")
        print("   1. Copy the .tar.gz and .zip files to a safe location")
        print("   2. Store them on external drives or cloud storage")
        print("   3. Test the restore process on a test system")
        print("   4. Keep multiple copies in different locations")
        
        return manifest, archive_path, zip_path

def main():
    """Main backup function"""
    print("🚀 OMOP-UMLS CROSSWALK SYSTEM - CRITICAL BACKUP CREATOR")
    print("="*70)
    
    try:
        backup_creator = CriticalBackupCreator()
        manifest, archive_path, zip_path = backup_creator.run_complete_backup()
        
        print("\n✅ Backup process completed successfully!")
        print(f"📁 Your backup is ready at: {backup_creator.backup_path}")
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
