"""
Pydantic Models for Fashion Trend Data Structures.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ColorTrend(BaseModel):
    name: str = Field(..., description="The common name of the color.")
    pantone_code: Optional[str] = Field(
        None, description="The official Pantone TCX code."
    )
    hex_value: Optional[str] = Field(
        None, description="The hexadecimal representation."
    )


class FabricTrend(BaseModel):
    material: str = Field(..., description="The base material of the fabric.")
    texture: Optional[str] = Field(
        None, description="The surface texture of the fabric."
    )
    sustainable: bool = Field(
        ..., description="Indicates if the fabric is sustainable."
    )


class KeyPieceDetail(BaseModel):
    key_piece_name: str = Field(..., description="The descriptive name of the garment.")
    description: str = Field(..., description="This item's role and significance.")
    fabrics: List[FabricTrend] = Field(..., description="Recommended fabrics.")
    colors: List[ColorTrend] = Field(
        ..., description="Curated list of suitable colors."
    )
    silhouettes: List[str] = Field(..., description="Specific cuts and shapes.")
    details_trims: List[str] = Field(
        ..., description="Specific design details or trims."
    )
    suggested_pairings: List[str] = Field(..., description="Other items to style with.")


class FashionTrendReport(BaseModel):
    season: str = Field(..., description="The target season.")
    year: int = Field(..., description="The target year.")
    overarching_theme: str = Field(
        ..., description="The high-level theme of the collection."
    )
    cultural_drivers: List[str] = Field(..., description="Socio-cultural influences.")
    influential_models: List[str] = Field(
        ..., description="Style icons who embody the trend."
    )
    accessories: List[str] = Field(
        ..., description="General accessories for the collection."
    )
    detailed_key_pieces: List[KeyPieceDetail] = Field(
        ..., description="Detailed breakdown of each garment."
    )
