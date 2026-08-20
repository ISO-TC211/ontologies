from rdflib import BNode, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from .base import RuleStrategy


def _datatype_range(graph, values):
    node = BNode()
    graph.add((node, RDF.type, RDFS.Datatype))
    members = BNode()
    graph.add((node, OWL.oneOf, members))
    Collection(graph, members, [Literal(value) for value in values])
    return node


def _mark_datatype_attributes(graph, attributes, data_range):
    for attribute in attributes:
        graph.add((attribute, RDF.type, OWL.DatatypeProperty))
        graph.add((attribute, RDFS.range, data_range))


class IsoEnumerationStrategy(RuleStrategy):
    name = "iso"
    source = "ISO/TC 211 enumeration to DatatypeProperty with owl:oneOf"

    def apply(self, context, **kwargs):
        values = kwargs.get("values", [])
        if values:
            data_range = _datatype_range(context.graph, values)
            _mark_datatype_attributes(context.graph, kwargs.get("attributes", []), data_range)
        return context


class InspireEnumerationStrategy(RuleStrategy):
    name = "inspire"
    source = "INSPIRE Guidelines enumeration encoding"

    def apply(self, context, **kwargs):
        values = kwargs.get("values", [])
        if not values:
            return context
        if kwargs.get("self_describing"):
            data_range = _datatype_range(context.graph, values)
            _mark_datatype_attributes(context.graph, kwargs.get("attributes", []), data_range)
        else:
            scheme = URIRef(str(kwargs["class_iri"]) + "/skos")
            context.graph.add((scheme, RDF.type, SKOS.ConceptScheme))
            context.graph.add((kwargs["class_iri"], RDFS.seeAlso, scheme))
            concepts = []
            for value in values:
                concept = URIRef(str(scheme) + "/" + str(value).replace(" ", ""))
                concepts.append(concept)
                context.graph.add((concept, RDF.type, SKOS.Concept))
                context.graph.add((concept, SKOS.inScheme, scheme))
                context.graph.add((concept, SKOS.prefLabel, Literal(value)))
            for attribute in kwargs.get("attributes", []):
                context.graph.add((attribute, RDF.type, OWL.ObjectProperty))
                context.graph.add((attribute, RDFS.range, SKOS.Concept))
        return context