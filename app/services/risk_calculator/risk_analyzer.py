from typing import List
import sys
import json
import os

from app.core.types import Project, Chunk, RiskType, LLMRiskAnalysisResponse, RiskDimensionSpec, LLMEvidence, LLMDimensionRating
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.repositories.evidence_rating_repository import EvidenceRatingRepository
from app.repositories.evidence_repository import EvidenceRepository
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


def parse_llm_response(response_data: dict) -> LLMRiskAnalysisResponse:
    """Parse JSON response from LLM into our dataclass structure."""
    evidences = []
    
    for evidence_data in response_data.get('evidences', []):
        dimension_ratings = []
        
        for rating_data in evidence_data.get('dimension_ratings', []):
            dimension_rating = LLMDimensionRating(
                dimension_key=rating_data.get('dimension_key', ''),
                scale_value=rating_data.get('scale_value', ''),
                reasoning=rating_data.get('reasoning', ''),
                confidence=rating_data.get('confidence', 0.0)
            )
            dimension_ratings.append(dimension_rating)
        
        evidence = LLMEvidence(
            claim_text=evidence_data.get('claim_text', ''),
            supporting_text=evidence_data.get('supporting_text', ''),
            dimension_ratings=dimension_ratings,
            confidence=evidence_data.get('confidence', 0.0)
        )
        evidences.append(evidence)
    
    return LLMRiskAnalysisResponse(
        risk_type=response_data.get('risk_type', ''),
        evidences=evidences,
        chunk_summary=response_data.get('chunk_summary', ''),
        no_evidence_reasoning=response_data.get('no_evidence_reasoning', '')
    )


async def save_evidences_to_database(llm_response: LLMRiskAnalysisResponse, risk_type: RiskType, chunk: Chunk, dimensions: List[RiskDimensionSpec]) -> int:
    """Save LLM evidences and evidence ratings to database. Returns number of evidences saved."""
    saved_count = 0
    
    # Create a lookup dict for dimensions by key
    dimensions_dict = {dim.key: dim for dim in dimensions}
    
    for llm_evidence in llm_response.evidences:
        try:
            # Create evidence ratings for each dimension
            evidence_ratings = []
            
            for llm_rating in llm_evidence.dimension_ratings:
                dimension_spec = dimensions_dict.get(llm_rating.dimension_key)
                if not dimension_spec:
                    print(f"        ⚠️ Warning: Unknown dimension key '{llm_rating.dimension_key}', skipping rating")
                    continue
                
                # Validate scale value
                if llm_rating.scale_value not in dimension_spec.mapping:
                    print(f"        ⚠️ Warning: Invalid scale value '{llm_rating.scale_value}' for dimension '{llm_rating.dimension_key}', skipping rating")
                    continue
                
                rating = await EvidenceRatingRepository.create_from_llm_rating(
                    llm_rating, risk_type, dimension_spec
                )
                evidence_ratings.append(rating)
            
            if not evidence_ratings:
                print(f"        ⚠️ No valid evidence ratings created for evidence: {llm_evidence.claim_text[:50]}...")
                continue
            
            # Create evidence with associated ratings
            evidence = await EvidenceRepository.create_from_llm_evidence(
                llm_evidence, risk_type, chunk, evidence_ratings
            )
            
            saved_count += 1
            print(f"        ✅ Saved evidence: {evidence.claim_text[:50]}... (score: {evidence.score:.2f})")
            
        except Exception as e:
            print(f"        ❌ Error saving evidence '{llm_evidence.claim_text[:50]}...': {str(e)}")
    
    return saved_count


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
        # For debugging, analyze all risk types for all chunks (no chunk restriction)
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
            
            # Parse into our dataclass structure
            llm_response = parse_llm_response(response_data)
            print(f"    📈 Found {llm_response.evidence_count} evidences")
            
            if llm_response.has_evidences:
                # Display evidences summary
                for i, evidence in enumerate(llm_response.evidences, 1):
                    print(f"        Evidence {i}: {evidence.claim_text[:50]}...")
                    print(f"        Confidence: {evidence.confidence}")
                    print(f"        Dimensions rated: {len(evidence.dimension_ratings)}")
                
                # Save evidences and evidence ratings to database
                print(f"    💾 Saving evidences to database...")
                saved_count = await save_evidences_to_database(llm_response, risk_type, chunk, dimensions)
                print(f"    ✅ Saved {saved_count} evidences to database")
                
            else:
                print(f"    📄 No evidence reasoning: {llm_response.no_evidence_reasoning}")
                
        except json.JSONDecodeError as e:
            print(f"    ❌ Failed to parse JSON response: {str(e)}")
            print(f"    📝 Response may not be in valid JSON format")
        except Exception as e:
            print(f"    ❌ Error processing LLM response: {str(e)}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"    ❌ Error in LLM analysis: {str(e)}")


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
        
        # Apply mode-based chunk limiting
        app_mode = os.getenv('APP_MODE', 'DEV').upper()
        chunks_to_process = chunks
        
        if app_mode == 'DEV':
            max_chunks = int(os.getenv('DEV_MAX_CHUNKS_PER_PROJECT', '10'))
            if len(chunks) > max_chunks:
                chunks_to_process = chunks[:max_chunks]
                print(f"🔧 DEV MODE: Limiting processing to {max_chunks} chunks (out of {len(chunks)} total)")
            else:
                print(f"🔧 DEV MODE: Processing all {len(chunks)} chunks (under limit of {max_chunks})")
        else:
            print(f"🚀 PROD MODE: Processing all {len(chunks)} chunks")
        
        print(f"📝 Found {len(chunks)} total chunks, processing {len(chunks_to_process)} chunks")
        print(f"⚡ Will analyze against {len(risk_types)} risk types")
        
        # Process each chunk against all risk types
        analyzed_count = 0
        for chunk in chunks_to_process:
            print(f"  📊 Analyzing chunk {chunk.chunk_index + 1}/{len(chunks_to_process)}")
            await analyze_chunk_for_all_risks(chunk, risk_types)
            analyzed_count += 1
        
        print(f"✅ Completed risk analysis for {analyzed_count} chunks in project '{project.name}'")
        return analyzed_count
        
    except Exception as e:
        print(f"❌ Error in risk analysis for project '{project.name}': {str(e)}")
        return 0
