from typing import List
import sys
import json

from app.core.types import Project, Chunk, RiskType, LLMRiskAnalysisResponse, RiskDimensionSpec
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.core.llm_service import get_llm_service


async def get_all_risk_types() -> List[RiskType]:
    """Load all risk types from database. Cache this result to avoid repeated queries."""
    try:
        risk_types = await RiskTypeRepository.get_all()
        return risk_types
    except Exception as e:
        print(f"❌ Error fetching risk types: {str(e)}")
        return []


async def get_all_risk_dimensions() -> List[RiskDimensionSpec]:
    return await RiskDimensionRepository.get_all()


def build_risk_analysis_prompt(chunk_content: str, risk_type: RiskType, dimensions: List[RiskDimensionSpec]) -> str:
    
    # Build dimensions section
    dimensions_text = ""
    for dim in dimensions:
        scale_desc = " → ".join(dim.scale)
        dimensions_text += f"""
**{dim.label}** ({dim.key}):
- Description: {dim.description}
- Rationale: {dim.rationale} 
- Guidance: {dim.guidance}
- Scale: {scale_desc} {'(higher = riskier)' if dim.higher_is_riskier else '(higher = less risky)'}
"""
    
    # Build the main prompt
    prompt = f"""You are an expert risk analyst for carbon credit projects. Your task is to analyze a text chunk for evidence of a specific risk type and rate each evidence across multiple dimensions.

**RISK TYPE TO ANALYZE:**
- **Name**: {risk_type.risk_type}
- **Description**: {risk_type.description}

**RATING DIMENSIONS:**
{dimensions_text}

**TEXT TO ANALYZE:**
```
{chunk_content}
```

**INSTRUCTIONS:**
1. Carefully read and analyze the text for ANY evidence related to "{risk_type.risk_type}" risks
2. For each piece of evidence found:
   - Write a clear claim summarizing the evidence
   - Extract the exact supporting text from the chunk
   - Rate the evidence on ALL {len(dimensions)} dimensions using the provided scales
   - Provide reasoning for each dimension rating
   - Assign overall confidence (0.0-1.0) in this evidence
3. If NO evidence is found, explain why this text doesn't contain relevant risk indicators
4. Provide a brief summary of what the text chunk contains

**RESPONSE FORMAT:**
You MUST respond with valid JSON in exactly this structure:

{{
  "risk_type": "{risk_type.risk_type}",
  "evidences": [
    {{
      "claim_text": "Clear summary of the evidence",
      "supporting_text": "Exact quote from the text",
      "dimension_ratings": [
        {{
          "dimension_key": "impact",
          "scale_value": "moderate",
          "reasoning": "Explanation for this rating",
          "confidence": 0.8
        }},
        // ... ratings for all dimensions
      ],
      "confidence": 0.7,
      "metadata": {{}}
    }}
    // ... more evidences if found
  ],
  "chunk_summary": "Brief description of chunk content",
  "no_evidence_reasoning": "If no evidences found, explain why"
}}

**CRITICAL REQUIREMENTS:**
- Use ONLY the exact scale values provided for each dimension
- Rate ALL dimensions for each evidence found
- Be thorough but precise - don't fabricate evidence
- Maintain objectivity and accuracy
- Provide clear, specific reasoning for each rating"""

    return prompt


async def get_project_chunks(project: Project) -> List[Chunk]:
    """Get all chunks for a project by getting chunks from all its documents."""
    try:
        # First, get all documents for this project
        documents = await SourceDocumentRepository.get_by_project(project.id)
        
        if not documents:
            return []
        
        # Then, get all chunks for each document
        all_chunks = []
        for document in documents:
            chunks = await ChunkRepository.get_chunks_by_document(document.id)
            all_chunks.extend(chunks)
        
        return all_chunks
    except Exception as e:
        print(f"❌ Error fetching chunks for project '{project.name}': {str(e)}")
        return []


async def analyze_chunk_for_risk_type(chunk: Chunk, risk_type: RiskType) -> None:
    """Analyze a single chunk for a specific risk type."""
    print(f"    🔍 Analyzing chunk {chunk.chunk_index} for risk type: {risk_type.risk_type}")
    
    try:
        # For now, let's test with a comprehensive query
        if chunk.chunk_index == 0 and risk_type.risk_type:  # Only test on first chunk/risk combo
            print(f"    📋 Loading risk dimensions...")
            try:
                dimensions = await get_all_risk_dimensions()
                print(f"    ✅ Risk dimensions loaded successfully")
            except Exception as e:
                print(f"    ❌ Failed to load risk dimensions: {type(e).__name__}: {str(e)}")
                print(f"    🔍 Error details: {repr(e)}")
                import traceback
                traceback.print_exc()
                return
            
            if not dimensions:
                print(f"    ⚠️ No risk dimensions found in database - cannot perform analysis")
                print(f"    💡 Hint: Run database initialization first:")
                print(f"       docker build -t db-init -f docker/Dockerfile.db-init .")
                print(f"       docker run --rm --network internal db-init")
                return
            
            print(f"    📊 Found {len(dimensions)} risk dimensions")
            
            print(f"    🤖 Building analysis prompt...")
            prompt = build_risk_analysis_prompt(chunk.content, risk_type, dimensions)
            
            print(f"    🧠 Querying LLM for risk analysis...")
            llm_service = get_llm_service()
            session_id = f"risk_analysis_{risk_type.risk_type}_{chunk.chunk_index}"
            response = await llm_service.query(prompt, session_id=session_id)
            
            print(f"    📝 Raw LLM Response:")
            print(f"{'='*50}")
            print(response)
            print(f"{'='*50}")
            
            # Try to parse JSON response
            try:
                response_data = json.loads(response)
                print(f"    ✅ Successfully parsed JSON response")
                print(f"    📈 Found {len(response_data.get('evidences', []))} evidences")
                
                # Display evidences summary
                for i, evidence in enumerate(response_data.get('evidences', []), 1):
                    print(f"        Evidence {i}: {evidence.get('claim_text', 'No claim')}")
                    print(f"        Confidence: {evidence.get('confidence', 0.0)}")
                    ratings = evidence.get('dimension_ratings', [])
                    print(f"        Dimensions rated: {len(ratings)}")
                
                if not response_data.get('evidences'):
                    print(f"    📄 No evidence reasoning: {response_data.get('no_evidence_reasoning', 'Not provided')}")
                    
            except json.JSONDecodeError as e:
                print(f"    ❌ Failed to parse JSON response: {str(e)}")
                print(f"    📝 Response may not be in valid JSON format")
            
            # TODO: Convert to LLMRiskAnalysisResponse dataclass and save to database
            
        else:
            print(f"    ⏩ Skipping LLM call for this chunk/risk (testing only first)")
            
    except Exception as e:
        print(f"    ❌ Error in LLM analysis: {str(e)}")

    # Debug: Exit after first chunk
    print(f"\n🛑 DEBUG: Exiting after analyzing first chunk (chunk {chunk.chunk_index})")
    sys.exit()


async def analyze_chunk_for_all_risks(chunk: Chunk, risk_types: List[RiskType]) -> None:
    """Analyze a single chunk against all risk types."""
    for risk_type in risk_types:
        await analyze_chunk_for_risk_type(chunk, risk_type)


async def process_project_risk_analysis(project: Project, risk_types: List[RiskType]) -> int:
    """Process risk analysis for all chunks in a project. Returns number of chunks analyzed."""
    print(f"\n🎯 Analyzing risks for project: {project.name}")
    
    try:
        # Get all chunks for this project
        chunks = await get_project_chunks(project)
        
        if not chunks:
            print(f"⚠️  No chunks found for project '{project.name}'")
            return 0
        
        print(f"📝 Found {len(chunks)} chunks to analyze")
        print(f"⚡ Will analyze against {len(risk_types)} risk types")
        
        # Process each chunk against all risk types
        analyzed_count = 0
        for chunk in chunks:
            print(f"  📊 Analyzing chunk {chunk.chunk_index + 1}/{len(chunks)}")
            await analyze_chunk_for_all_risks(chunk, risk_types)
            analyzed_count += 1
        
        print(f"✅ Completed risk analysis for {analyzed_count} chunks in project '{project.name}'")
        return analyzed_count
        
    except Exception as e:
        print(f"❌ Error in risk analysis for project '{project.name}': {str(e)}")
        return 0
