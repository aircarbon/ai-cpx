import os
from typing import List
import json
import asyncio

from app.core.types import Project, Chunk, RiskType, LLMRiskAnalysisResponse, RiskDimensionSpec, LLMEvidence, LLMDimensionRating
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.risk_type_repository import RiskTypeRepository
from app.repositories.source_document_repository import SourceDocumentRepository
from app.repositories.risk_dimension_repository import RiskDimensionRepository
from app.repositories.evidence_rating_repository import EvidenceRatingRepository
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.processing_state_repository import ProcessingStateRepository
from app.core.llm_service import get_llm_service

# Retry configuration for LLM analysis
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# Batch processing configuration
BATCH_SIZE = 5  # Number of concurrent LLM queries


async def get_all_risk_types() -> List[RiskType]:
    """Load all risk types from database. Cache this result to avoid repeated queries."""
    try:
        risk_types = await RiskTypeRepository.get_all()

        # Apply DEV mode risk type limits
        total_risk_types = len(risk_types)
        if os.getenv('APP_MODE') == 'DEV':
            max_risk_types = int(os.getenv('DEV_MAX_RISK_TYPES', '999'))
            if max_risk_types < total_risk_types:
                # Sort risk types by weight (descending) for most important risks first, then by name for consistency
                risk_types = sorted(risk_types, key=lambda rt: (-rt.weight, rt.risk_type))[:max_risk_types]
                print(f"🧪 DEV MODE: Using {len(risk_types)} of {total_risk_types} risk types (limited by DEV_MAX_RISK_TYPES={max_risk_types})")
                print(f"    Selected risk types: {', '.join([f'{rt.name} (weight: {rt.weight})' for rt in risk_types])}")

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
- **Name**: {risk_type.name}
- **Description**: {risk_type.description}

**RATING DIMENSIONS:**
{dimensions_text}

**TEXT TO ANALYZE:**
```
{chunk_content}
```

**INSTRUCTIONS:**
1. Carefully read and analyze the text for ANY evidence related to "{risk_type.name}" risks
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
        documents = await SourceDocumentRepository.get_by_project(project.id)
        
        if not documents:
            return []
        
        all_chunks = []
        for document in documents:
            chunks = await ChunkRepository.get_chunks_by_document(document.id)
            all_chunks.extend(chunks)
        
        return all_chunks
    except Exception as e:
        print(f"❌ Error fetching chunks for project '{project.name}': {str(e)}")
        return []


async def analyze_with_retry(chunk: Chunk, risk_type: RiskType, dimensions: List[RiskDimensionSpec]) -> int:
    """Analyze chunk with retry logic for LLM failures. Returns number of evidences saved."""
    for attempt in range(MAX_RETRIES):
        try:
            prompt = build_risk_analysis_prompt(chunk.content, risk_type, dimensions)
            llm_service = get_llm_service()
            session_id = f"risk_analysis_{risk_type.risk_type}_{chunk.chunk_index}"
            response = await llm_service.query(prompt, session_id=session_id)

            # Try to parse JSON response
            try:
                response_data = json.loads(response)
                llm_response = parse_llm_response(response_data)

                if llm_response.has_evidences:
                    saved_count = await save_evidences_to_database(llm_response, risk_type, chunk, dimensions)
                    return saved_count
                else:
                    # No evidences found, but this is not an error
                    return 0

            except json.JSONDecodeError as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"      ⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: JSON parsing failed, retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"      ❌ Failed to parse JSON response after {MAX_RETRIES} attempts: {str(e)}")
                    return 0

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"      ⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: Processing error, retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"      ❌ Error processing LLM response after {MAX_RETRIES} attempts: {str(e)}")
                    return 0

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                print(f"      ⚠️ Attempt {attempt + 1}/{MAX_RETRIES}: LLM query failed, retrying in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
                continue
            else:
                print(f"      ❌ LLM query failed after {MAX_RETRIES} attempts: {str(e)}")
                return 0

    return 0


async def analyze_chunk_for_risk_type(chunk: Chunk, risk_type: RiskType, project_id: str, project_index: int, total_projects: int, chunk_index: int, total_chunks: int, risk_index: int, total_risks: int) -> None:
    """Analyze a single chunk for a specific risk type."""
    print(f"    🔍 Analyzing project {project_index}/{total_projects}, chunk {chunk_index}/{total_chunks}, risk type {risk_index}/{total_risks}: {risk_type.name}")

    # Check if evidence extraction is already completed for this chunk + risk type
    is_completed = await ProcessingStateRepository.is_completed(
        stage="evidence_extraction",
        project_id=project_id,
        chunk_id=chunk.id,
        risk_type_id=risk_type.id
    )

    if is_completed:
        print(f"      ⏭️  Skipping (already completed)")
        return

    # Update status to in_progress
    await ProcessingStateRepository.update_status(
        stage="evidence_extraction",
        project_id=project_id,
        chunk_id=chunk.id,
        risk_type_id=risk_type.id,
        status="in_progress"
    )

    try:
        dimensions = await get_all_risk_dimensions()
        if not dimensions:
            await ProcessingStateRepository.update_status(
                stage="evidence_extraction",
                project_id=project_id,
                chunk_id=chunk.id,
                risk_type_id=risk_type.id,
                status="failed",
                error_message="No risk dimensions found"
            )
            return

        # Retry LLM analysis with error handling
        saved_count = await analyze_with_retry(chunk, risk_type, dimensions)

        # Mark as completed with results
        await ProcessingStateRepository.update_status(
            stage="evidence_extraction",
            project_id=project_id,
            chunk_id=chunk.id,
            risk_type_id=risk_type.id,
            status="completed",
            results={"evidence_count": saved_count}
        )

        if saved_count > 0:
            print(f"      ✅ Saved {saved_count} evidences")

    except Exception as e:
        await ProcessingStateRepository.update_status(
            stage="evidence_extraction",
            project_id=project_id,
            chunk_id=chunk.id,
            risk_type_id=risk_type.id,
            status="failed",
            error_message=str(e)
        )
        print(f"      ❌ Error in LLM analysis: {str(e)}")


async def analyze_chunk_for_all_risks(chunk: Chunk, risk_types: List[RiskType], project_id: str, project_index: int, total_projects: int, chunk_index: int, total_chunks: int) -> None:
    """Analyze a single chunk against all risk types using parallel batches."""
    # Process risk types in batches for parallel execution
    for batch_start in range(0, len(risk_types), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(risk_types))
        batch_risk_types = risk_types[batch_start:batch_end]

        # Create tasks for this batch
        tasks = []
        for i, risk_type in enumerate(batch_risk_types):
            risk_index = batch_start + i + 1  # 1-based index
            task = analyze_chunk_for_risk_type(
                chunk, risk_type, project_id, project_index, total_projects,
                chunk_index, total_chunks, risk_index, len(risk_types)
            )
            tasks.append(task)

        # Execute batch in parallel
        print(f"    📦 Processing batch {batch_start//BATCH_SIZE + 1} ({len(batch_risk_types)} risk types in parallel)")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any exceptions that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                risk_type = batch_risk_types[i]
                print(f"      ❌ Error processing {risk_type.name}: {str(result)}")


async def process_project_risk_analysis(project: Project, risk_types: List[RiskType], project_index: int, total_projects: int) -> int:
    """Process risk analysis for all chunks in a project."""
    chunks = await get_project_chunks(project)

    if not chunks:
        print(f"    ⚠️  No chunks found for project '{project.name}'")
        return 0

    # Process each chunk against all risk types
    for chunk_index, chunk in enumerate(chunks):
        await analyze_chunk_for_all_risks(chunk, risk_types, project.id, project_index, total_projects, chunk_index + 1, len(chunks))

    # Return total combinations processed
    return len(chunks) * len(risk_types)
