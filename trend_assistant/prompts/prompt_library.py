"""
A library of master prompt templates for the Fashion Trend Assistant.
(A+ version, upgraded for cultural specificity and garment name preservation)
"""

# --- Phase 2.5: Intelligent Summarization Prompt (UPGRADED) ---
SUMMARIZATION_PROMPT_TEMPLATE = """
Your role is a meticulous Research Analyst for a top-tier fashion forecasting agency.
Your task is to analyze the following document and extract ONLY the most critical, factual information related to fashion trends.

RULES:
1.  **CRITICAL:** Prioritize and preserve the specific names of garments, especially those that are culturally or regionally significant (e.g., 'Saree', 'Lehenga', 'Kimono', 'Abaya', 'Kurta'). Do not replace them with generic terms like 'dress' or 'jacket'.
2.  Focus on: specific trends, designer/brand names, collection names, garment types, colors, fabrics, materials, textures, prints, patterns, and silhouettes.
3.  Ignore all marketing fluff, subjective opinions, boilerplate text, and irrelevant content.
4.  Present the extracted information as dense, factual bullet points.
5.  If the document contains no relevant fashion information, respond with only the text "No relevant information."

DOCUMENT TEXT:
---
{document_text}
---
"""

# --- Phase 3: Main Data Synthesis Prompt (UPGRADED) ---
ITEMIZED_REPORT_PROMPT = """
You are the Director of Strategy for 'The Future of Fashion', a globally respected trend analysis firm.
Your task is to synthesize the provided research summaries into a single, cohesive, and insightful fashion trend report.
You MUST base your analysis strictly on the information provided. Do not invent or hallucinate information.

**CRITICAL RULES:**
1.  **Prioritize Specificity:** For the 'key_piece_name', you MUST use the specific, culturally relevant garment names found in the research (e.g., "The Embroidered Punjabi," "The Deconstructed Saree"). AVOID overly generic terms like "coat," "dress," or "jacket" unless no specific alternative is mentioned.
2.  **De-duplicate Lists:** All lists in your response must contain only unique items.
3.  **Complete Color Codes:** For the 'colors' array, you MUST provide real Pantone TCX codes and their corresponding hex values. Find the closest match if the exact one is unknown. **DO NOT leave `pantone_code` or `hex_value` as null.**

RESEARCH SUMMARIES:
---
{research_context}
---

Based ONLY on the provided research, generate a single, valid JSON object for the {season} {year} season.
The JSON object MUST strictly adhere to the following schema.

SCHEMA:
{{
  "season": "{season}",
  "year": {year},
  "overarching_theme": "...",
  "cultural_drivers": ["..."],
  "influential_models": ["..."],
  "accessories": {{ ... }},
  "detailed_key_pieces": [
    {{
      "key_piece_name": "The descriptive name of a key garment. MUST BE SPECIFIC AND AVOID GENERIC DEFAULTS.",
      "description": "A brief, insightful explanation of this item's role. CRITICAL: Connect its significance directly to one or more of the 'cultural_drivers'.",
      "inspired_by_designers": ["..."],
      "wearer_profile": "A short description of the person who would wear this piece, their lifestyle, and attitude.",
      "fabrics": [ {{ ... }} ],
      "colors": [ {{ ... }} ],
      "silhouettes": ["..."],
      "details_trims": ["..."],
      "suggested_pairings": ["..."]
    }}
  ]
}}
"""

# --- Phase 4: Image Prompt Generation Templates (UPGRADED) ---
INSPIRATION_BOARD_PROMPT_TEMPLATE = """
Create a hyper-detailed, atmospheric flat lay of a fashion designer's physical inspiration board or workbench.

Theme: '{theme}'.
Aesthetic Focus: The conceptual idea of a '{key_piece_name}'.
Cultural Drivers: {cultural_drivers}.
Muse: The style of {model_style}.

Composition: The board is a chaotic yet artfully arranged collage with multiple layers of pinned and taped elements. It should feel like a real, work-in-progress creative space.

Included Items: It features a mix of: blurry, cinematic film stills; close-up photos of architectural textures (e.g., raw concrete, weathered wood); torn pages from vintage art books with handwritten annotations in the margins; rough charcoal sketches of garment details like collars and seams; and physical fabric swatches with frayed edges.

Overall Mood: Tactile, authentic, intellectual, work-in-progress, moody, cinematic, nostalgic.

Style: Ultra-realistic photograph, top-down perspective, shot on a Hasselblad camera, dramatic and moody lighting with deep shadows, extreme detail, 8k.
"""

MOOD_BOARD_PROMPT_TEMPLATE = """
Create a professional fashion designer's mood board, meticulously organized on a raw concrete or linen surface.
Focus: Defining the physical materials for a '{key_piece_name}'.
Fabric Swatches: The board features hyper-realistic, neatly cut physical fabric swatches of: {fabric_names}. Show the texture and drape.
Color Palette: A color story is arranged with official Pantone-style color chips for: {color_names}.
Hardware & Trims: Include close-up, macro shots of key trims and hardware like: {details_trims}.
Style: Professional studio photography, top-down view (flat lay), soft and diffused lighting, extreme detail, macro photography, 8k.
"""

FINAL_GARMENT_PROMPT_TEMPLATE = """
Full-body editorial fashion photograph for a Vogue or Dazed Magazine lookbook.
Model: A runway model with the specific attitude and presence of {model_style}.
Garment: The model is wearing a stunning '{main_color} {key_piece_name}' crafted from high-quality, hyper-realistic {main_fabric}.
Silhouette: The design's silhouette is clearly {silhouette}.
Key Details: Macro details of the garment are visible, showing: {details_trims}.
Pose & Attitude: The model has a confident, nonchalant, and powerful pose.
Setting: Shot in a minimalist brutalist architectural setting with dramatic shadows and a single light source.
Style: Cinematic fashion photography, shot on a 50mm lens, hyper-detailed, dramatic lighting, professional color grading, 8k.
Negative Prompt: -nsfw, -deformed, -bad anatomy, -blurry, -low quality
"""
