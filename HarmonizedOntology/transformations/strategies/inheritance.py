from rdflib import BNode
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS

from .base import DecisionStrategy


class DirectSubclassStrategy(DecisionStrategy):
    name = "direct_subclass"
    source = "INSPIRE and ISO/TC 211"

    def apply(self, context, **kwargs):
        context.graph.add((kwargs["subclass"], RDFS.subClassOf, kwargs["superclass"]))
        return context


class IntersectionStrategy(DecisionStrategy):
    name = "intersection"
    source = "Hajjamy et al., 2016"

    def apply(self, context, **kwargs):
        expression = BNode()
        context.graph.add((kwargs["subclass"], RDFS.subClassOf, expression))
        context.graph.add((expression, RDF.type, OWL.Class))
        members = kwargs.get("superclasses", [kwargs["superclass"]])
        context.graph.add((expression, OWL.intersectionOf, Collection(context.graph, expression, members)))
        return context