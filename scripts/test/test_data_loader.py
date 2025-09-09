"""
Test data loader for loading fixture data into test database.
Handles test-specific JSON files with MongoDB export format.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add path to access app modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.core.models import Project, SourceDocument, Chunk
from bson import ObjectId


def load_test_json(filename: str) -> List[Dict]:
    data_dir = Path(__file__).parent / "data"
    file_path = data_dir / filename
    
    if not file_path.exists():
        raise FileNotFoundError(f"Test data file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def clean_mongodb_fields(data: Dict) -> Dict:
    """Clean MongoDB export fields and preserve ObjectId relationships."""
    cleaned = {}
    
    for key, value in data.items():
        if key == "_id" and isinstance(value, dict) and "$oid" in value:
            # Convert MongoDB _id to Beanie id
            cleaned["id"] = ObjectId(value["$oid"])
        elif key in ["created_at", "updated_at"] and isinstance(value, dict) and "$date" in value:
            # Convert MongoDB date format to datetime
            cleaned[key] = datetime.fromisoformat(value["$date"].replace("Z", "+00:00"))
        elif key.endswith("_id") and isinstance(value, dict):
            # Handle different ObjectId formats
            if "$oid" in value:
                # Simple ObjectId format: {"$oid": "..."}
                cleaned[key] = ObjectId(value["$oid"])
            elif "$ref" in value and "$id" in value:
                # DBRef format: {"$ref": "collection", "$id": {"$oid": "..."}}
                if isinstance(value["$id"], dict) and "$oid" in value["$id"]:
                    cleaned[key] = ObjectId(value["$id"]["$oid"])
                else:
                    cleaned[key] = ObjectId(value["$id"])
        else:
            cleaned[key] = value
    
    return cleaned


async def load_test_projects() -> int:
    print("📁 Loading test projects...")
    
    try:
        projects_data = load_test_json("projects.json")
        created_count = 0
        
        for project_data in projects_data:
            clean_data = clean_mongodb_fields(project_data)
            
            existing = await Project.find_one(Project.id == clean_data["id"])
            if existing:
                print(f"   ⚠️  Project '{clean_data['name']}' (ID: {clean_data['id']}) already exists, skipping...")
                continue
            
            project = Project(**clean_data)
            await project.insert()
            created_count += 1
            print(f"   ✅ Created project: {clean_data['name']}")
        
        print(f"📁 Test projects loaded: {created_count} created, {len(projects_data) - created_count} already existed")
        return created_count
        
    except Exception as e:
        print(f"❌ Error loading test projects: {e}")
        raise


async def load_test_documents() -> int:
    print("📄 Loading test documents...")
    
    try:
        documents_data = load_test_json("documents.json")
        created_count = 0
        
        for document_data in documents_data:
            clean_data = clean_mongodb_fields(document_data)
            
            existing = await SourceDocument.find_one(SourceDocument.id == clean_data["id"])
            if existing:
                print(f"   ⚠️  Document '{clean_data['file_name']}' (ID: {clean_data['id']}) already exists, skipping...")
                continue
            
            document = SourceDocument(**clean_data)
            await document.insert()
            created_count += 1
            print(f"   ✅ Created document: {clean_data['file_name']}")
        
        print(f"📄 Test documents loaded: {created_count} created, {len(documents_data) - created_count} already existed")
        return created_count
        
    except FileNotFoundError:
        print("   ⚠️  No documents.json found, skipping document loading")
        return 0
    except Exception as e:
        print(f"❌ Error loading test documents: {e}")
        raise


async def load_test_chunks() -> int:
    print("🧩 Loading test chunks...")
    
    try:
        chunks_data = load_test_json("chunks.json")
        created_count = 0
        
        for chunk_data in chunks_data:
            clean_data = clean_mongodb_fields(chunk_data)
            
            existing = await Chunk.find_one(Chunk.id == clean_data["id"])  
            if existing:
                print(f"   ⚠️  Chunk {clean_data['chunk_index']} (ID: {clean_data['id']}) already exists, skipping...")
                continue
            
            chunk = Chunk(**clean_data)
            await chunk.insert()
            created_count += 1
            print(f"   ✅ Created chunk: {clean_data['chunk_index']}")
        
        print(f"🧩 Test chunks loaded: {created_count} created, {len(chunks_data) - created_count} already existed")
        return created_count
        
    except FileNotFoundError:
        print("   ⚠️  No chunks.json found, skipping chunk loading")
        return 0
    except Exception as e:
        print(f"❌ Error loading test chunks: {e}")
        raise


