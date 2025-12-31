"""LLM prompt builders for SEO Challenger generation.

Strict input -> strict output (JSON schema validation).
"""
import json
import logging
from typing import Any


logger = logging.getLogger(__name__)


class SEOChallengerPrompt:
    """Build prompts for SEO Challenger generation."""

    @staticmethod
    def build_refinement_prompt(
        product_snapshot: dict,
        diagnosis: str,
        metrics: dict,
        strategy_tag: str,
    ) -> str:
        """Build prompt for SEO refinement.

        Args:
            product_snapshot: Current SEO state
            diagnosis: Diagnosis type
            metrics: Performance metrics
            strategy_tag: Strategy tag context

        Returns:
            Prompt string
        """
        prompt = f"""You are an expert SEO copywriter for a handcrafted jewelry e-commerce store.

TASK: Refine product SEO based on performance diagnosis.

CURRENT PRODUCT STATE:
{json.dumps(product_snapshot, indent=2)}

PERFORMANCE DIAGNOSIS: {diagnosis}

METRICS (7-day window):
- CTR: {metrics['ctr']:.2%}
- ROAS: {metrics['roas']:.2f}
- Spend: ${metrics['spend']:.2f}
- Orders: {metrics['orders']}
- Click-through Proxy: {metrics['click_proxy']}

STRATEGY TAG: {strategy_tag}

INSTRUCTIONS:
1. Maintain brand voice: artisan, emotional connection, birthstone storytelling
2. Address the diagnosis (CTR_high_ROAS_low means landing mismatch)
3. Keep character limits:
   - Title: 70 chars max
   - Meta description: 160 chars max
4. Avoid prohibited claims (hypoallergenic, healing properties, etc.)
5. Output ONLY valid JSON (no markdown fences, no preamble)

OUTPUT SCHEMA:
{{
  "product_id": "{product_snapshot.get('product_id')}",
  "strategy_tag": "{strategy_tag}",
  "changes": {{
    "title": "...",
    "meta_description": "...",
    "tags": ["...", "..."],
    "alt_text_rules": ["..."]
  }},
  "rationale": {{
    "diagnosis": "{diagnosis}",
    "hypothesis": "...",
    "risk_notes": ["..."]
  }},
  "validation": {{
    "character_limits_ok": true,
    "prohibited_claims_ok": true
  }}
}}

Generate the Challenger SEO variant now:"""

        return prompt

    @staticmethod
    def validate_output(output: dict) -> tuple[bool, list[str]]:
        """Validate LLM output schema.

        Args:
            output: LLM JSON output

        Returns:
            (is_valid, errors)
        """
        errors = []

        required = ["product_id", "strategy_tag", "changes", "rationale", "validation"]
        for key in required:
            if key not in output:
                errors.append(f"Missing required key: {key}")

        changes = output.get("changes")
        if isinstance(changes, dict):
            title = changes.get("title")
            if isinstance(title, str) and len(title) > 70:
                errors.append(f"Title exceeds 70 chars: {len(title)}")

            description = changes.get("meta_description")
            if isinstance(description, str) and len(description) > 160:
                errors.append(
                    f"Description exceeds 160 chars: {len(description)}"
                )
        elif changes is not None:
            errors.append("changes must be an object")

        validation = output.get("validation")
        if isinstance(validation, dict):
            if not validation.get("character_limits_ok"):
                errors.append("Validation failed: character_limits_ok=false")
            if not validation.get("prohibited_claims_ok"):
                errors.append("Validation failed: prohibited_claims_ok=false")
        elif validation is not None:
            errors.append("validation must be an object")

        return (len(errors) == 0, errors)
