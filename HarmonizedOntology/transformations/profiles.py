from __future__ import annotations

from dataclasses import dataclass

from .strategies.abstract_class import AnnotationStrategy, DisjointUnionStrategy
from .strategies.enumeration import InspireEnumerationStrategy, IsoEnumerationStrategy
from .strategies.inheritance import DirectSubclassStrategy, IntersectionStrategy


@dataclass(frozen=True)
class PaperProfile:
    identifier: str
    title: str
    citation: str
    strategies: dict
    baselines: dict


PROFILES = {
    "jetlund": PaperProfile(
        "jetlund", "Jetlund et al.", "Jetlund et al.",
        {"abstract_class": {"annotation": AnnotationStrategy, "disjoint_union": DisjointUnionStrategy},
         "inheritance": {"direct_subclass": DirectSubclassStrategy, "intersection": IntersectionStrategy},
         "enumeration": {"iso": IsoEnumerationStrategy}},
        {"abstract_class": "annotation", "inheritance": "direct_subclass", "enumeration": "iso"},
    ),
    "zedlitz_luttenberger_2012": PaperProfile(
        "zedlitz_luttenberger_2012", "Zedlitz and Luttenberger (2012)", "Zedlitz & Luttenberger, 2012",
        {"abstract_class": {"annotation": AnnotationStrategy, "disjoint_union": DisjointUnionStrategy}},
        {"abstract_class": "disjoint_union"},
    ),
    "hajjamy_2016": PaperProfile(
        "hajjamy_2016", "Hajjamy et al. (2016)", "Hajjamy et al., 2016",
        {"inheritance": {"direct_subclass": DirectSubclassStrategy, "intersection": IntersectionStrategy}},
        {"inheritance": "intersection"},
    ),
    "iso": PaperProfile(
        "iso", "ISO/TC 211", "ISO/TC 211 implementation profile",
        {"abstract_class": {"annotation": AnnotationStrategy, "disjoint_union": DisjointUnionStrategy},
         "inheritance": {"direct_subclass": DirectSubclassStrategy, "intersection": IntersectionStrategy},
         "enumeration": {"iso": IsoEnumerationStrategy}},
        {"abstract_class": "annotation", "inheritance": "direct_subclass", "enumeration": "iso"},
    ),
    "inspire": PaperProfile(
        "inspire", "INSPIRE", "INSPIRE implementation profile",
        {"inheritance": {"direct_subclass": DirectSubclassStrategy, "intersection": IntersectionStrategy},
         "enumeration": {"inspire": InspireEnumerationStrategy}},
        {"inheritance": "direct_subclass", "enumeration": "inspire"},
    ),
}