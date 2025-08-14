"""
A library of master prompt templates for the Fashion Trend Assistant.
"""

# --- Phase 2.5: Intelligent Summarization Prompt ---
SUMMARIZATION_PROMPT_TEMPLATE = """
Your role is a meticulous Research Assistant for a high-end fashion magazine.
Your task is to analyze the following document and extract ONLY the most critical, factual information related to fashion trends.

RULES:
1.  Focus exclusively on: specific trends, designer/brand names, collection names, garment types, colors, fabrics, materials, textures, prints, patterns, and silhouettes.
2.  Ignore all marketing language, opinions, boilerplate text (like 'cookie policy' or 'subscribe'), and irrelevant filler content.
3.  Present the extracted information as a concise, bulleted list.
4.  If the document contains no relevant fashion information, respond with only the text "No relevant information."

DOCUMENT TEXT:
---
{document_text}
---
"""

# --- Phase 3: Main Data Synthesis Prompt ---
ITEMIZED_REPORT_PROMPT = """
You are the Lead Trend Forecaster for 'The Future of Fashion', a globally respected trend analysis firm.
Your task is to synthesize the provided collection of research summaries into a single, cohesive, and insightful fashion trend report.
You MUST base your analysis strictly on the information provided in the summaries below. Do not invent or hallucinate information.

RESEARCH SUMMARIES:
---
{research_context}
---

Based ONLY on the provided research, generate a single, valid JSON object for the {season} {year} season.
The JSON object MUST strictly adhere to the following schema.

**CRITICAL INSTRUCTION FOR COLORS:** For the 'colors' array, you MUST provide real Pantone TCX codes and their corresponding hex values. If an exact match is unknown from the text, use your knowledge to find the closest, most appropriate Pantone TCX code for the color name mentioned. **DO NOT leave `pantone_code` or `hex_value` as null or empty.**

SCHEMA:
{{
  "season": "{season}",
  "year": {year},
  "overarching_theme": "A concise, evocative name for the entire collection's theme that synthesizes the provided information.",
  "cultural_drivers": ["A list of the high-level socio-cultural influences driving the trend (e.g., 'Sustainability', '90s Nostalgia', 'Post-Pandemic Comfort')."],
  "influential_models": ["A list of names of models, celebrities, or style icons mentioned who embody the trend's aesthetic."],
  "accessories": ["A list of general accessories that complement the collection, based on the research summaries."],
  "detailed_key_pieces": [
    {{
      "key_piece_name": "The descriptive name of a key garment identified in the research (e.g., 'The Utilitarian Field Jacket').",
      "description": "A brief, insightful explanation of this item's role and significance within the overarching theme.",
      "fabrics": [
        {{
          "material": "The base material (e.g., 'Organic Cotton', 'Recycled Nylon').",
          "texture": "The specific surface texture (e.g., 'Heavy Twill', 'Liquid Silk').",
          "sustainable": "boolean indicating if the fabric is a sustainable choice."
        }}
      ],
      "colors": [
        {{
          "name": "The common name of the color (e.g., 'Desert Khaki').",
          "pantone_code": "CRITICAL: The official Pantone TCX code (e.g., '15-1214 TCX'). MUST NOT BE NULL.",
          "hex_value": "CRITICAL: The hex value of the color (e.g., '#C2B280'). MUST NOT BE NULL."
        }}
      ],
      "silhouettes": ["A list of specific cuts and shapes for this item (e.g., 'Boxy and oversized', 'Sharply tailored')."],
      "details_trims": ["A list of specific design details, hardware, or trims (e.g., 'Oversized cargo pockets', 'Matte black hardware')."],
      "suggested_pairings": ["A list of other items this piece could be styled with to complete the look."]
    }}
  ]
}}
"""

# --- Phase 4: Image Prompt Generation Templates ---
INSPIRATION_BOARD_PROMPT_TEMPLATE = """
A highly detailed, atmospheric inspiration board for a fashion collection.
Theme: '{theme}'.
Focus: The conceptual idea of a '{key_piece_name}'.
Core feelings are driven by: {cultural_drivers}.
The aesthetic is influenced by figures like {model_style}.
The board contains evocative, abstract images, textures, and scribbled notes related to the theme.
Style: Cinematic, moody lighting, ultra-realistic photo, high detail, 8k.
"""

MOOD_BOARD_PROMPT_TEMPLATE = """
A professional fashion designer's mood board, clean and meticulously organized.
Focus: Defining the materials for a '{key_piece_name}'.
The board features hyper-realistic, physical fabric swatches of: {fabric_names}.
A color palette is neatly arranged with Pantone-style swatches of: {color_names}.
Also includes close-up shots of key trims and hardware: {details_trims}.
Style: Shot on a clean, minimalist surface, top-down view (flat lay), perfect studio lighting, macro details, 8k.
"""

FINAL_GARMENT_PROMPT_TEMPLATE = """
Full-body editorial fashion photograph for a Vogue lookbook.
A runway model, with the presence of {model_style}, is wearing a stunning '{main_color} {key_piece_name}' crafted from high-quality {main_fabric}.
The design's silhouette is clearly {silhouette}.
Key details visible on the garment are: {details_trims}.
Shot in a minimalist concrete studio, dynamic pose, cinematic lighting, hyper-detailed, 8k.
"""
