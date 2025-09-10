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

from app.core.models import Project, SourceDocument, Chunk, EvidenceRating, Evidence
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
        elif isinstance(value, list):
            # Handle arrays (like evidence_ratings)
            cleaned_list = []
            for item in value:
                if isinstance(item, dict) and "$ref" in item and "$id" in item:
                    # DBRef in array: {"$ref": "collection", "$id": {"$oid": "..."}}
                    if isinstance(item["$id"], dict) and "$oid" in item["$id"]:
                        cleaned_list.append(ObjectId(item["$id"]["$oid"]))
                    else:
                        cleaned_list.append(ObjectId(item["$id"]))
                elif isinstance(item, dict) and "$oid" in item:
                    # Simple ObjectId in array: {"$oid": "..."}
                    cleaned_list.append(ObjectId(item["$oid"]))
                else:
                    cleaned_list.append(item)
            cleaned[key] = cleaned_list
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


async def load_test_evidence_ratings() -> int:
    print("📊 Loading test evidence ratings...")
    
    try:
        evidence_ratings_data = load_test_json("evidence_ratings.json")
        created_count = 0
        
        for rating_data in evidence_ratings_data:
            clean_data = clean_mongodb_fields(rating_data)
            
            existing = await EvidenceRating.find_one(EvidenceRating.id == clean_data["id"])
            if existing:
                print(f"   ⚠️  Evidence rating (ID: {clean_data['id']}) already exists, skipping...")
                continue
            
            evidence_rating = EvidenceRating(**clean_data)
            await evidence_rating.insert()
            created_count += 1
            print(f"   ✅ Created evidence rating: {clean_data['scale_value']} (score: {clean_data.get('score', 'N/A')})")
        
        print(f"📊 Test evidence ratings loaded: {created_count} created, {len(evidence_ratings_data) - created_count} already existed")
        return created_count
        
    except FileNotFoundError:
        print("   ⚠️  No evidence_ratings.json found, skipping evidence ratings loading")
        return 0
    except Exception as e:
        print(f"❌ Error loading test evidence ratings: {e}")
        raise


async def load_test_evidences() -> int:
    print("🔍 Loading test evidences...")
    
    try:
        evidences_data = load_test_json("evidences.json")
        created_count = 0
        
        for evidence_data in evidences_data:
            clean_data = clean_mongodb_fields(evidence_data)
            
            existing = await Evidence.find_one(Evidence.id == clean_data["id"])
            if existing:
                print(f"   ⚠️  Evidence (ID: {clean_data['id']}) already exists, skipping...")
                continue
            
            evidence = Evidence(**clean_data)
            await evidence.insert()
            created_count += 1
            print(f"   ✅ Created evidence: {clean_data['claim_text'][:50]}... (score: {clean_data.get('score', 'N/A')})")
        
        print(f"🔍 Test evidences loaded: {created_count} created, {len(evidences_data) - created_count} already existed")
        return created_count
        
    except FileNotFoundError:
        print("   ⚠️  No evidences.json found, skipping evidences loading")
        return 0
    except Exception as e:
        print(f"❌ Error loading test evidences: {e}")
        raise


