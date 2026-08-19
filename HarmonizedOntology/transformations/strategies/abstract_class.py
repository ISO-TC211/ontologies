from rdflib import BNode, Literal, Namespace
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF

from .base import DecisionStrategy
ISO191502 = Namespace("http://def.isotc211.org/iso19150/-2/2012/base#")


class AnnotationStrategy(DecisionStrategy):
    name = "annotation"
    source = "ISO/TC 211 isAbstract annotation"

    def apply(self, context, **kwargs):
        if kwargs.get("is_abstract"):
            context.graph.add((kwargs["class_iri"], ISO191502.isAbstract, Literal(True)))
        return context


class DisjointUnionStrategy(DecisionStrategy):
    name = "disjoint_union"
    source = "Zedlitz & Luttenberger, 2012"

    def apply(self, context, **kwargs):
        children = kwargs.get("children", [])
        if kwargs.get("is_abstract") and children:
            node = BNode()
            context.graph.add((kwargs["class_iri"], OWL.disjointUnionOf, node))
            Collection(context.graph, node, children)
        return context