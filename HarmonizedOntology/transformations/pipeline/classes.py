from ..context import HO, NS, SCHEMA, bind_iso_prefixes, extract_description, has_excluded_stereotype
from ..identifiers import element_name
from .base import TransformationStep
from ..strategies.inheritance import IntersectionStrategy
from rdflib import Literal, OWL, RDF, RDFS, SDO, URIRef


class BaseExtractClasses(TransformationStep):
    def transform(self, context):
        graph = context.graph
        bind_iso_prefixes(graph)
        package_identifiers = context.extraction_index.identifiers_for("mpkg")
        class_identifiers = context.extraction_index.identifiers_for("cls")

        for cls in context.tree.findall(".//UML:Class", namespaces=NS):
            if has_excluded_stereotype(cls):
                continue
            class_iri = class_identifiers[cls.get("xmi.id")]
            graph.add((class_iri, RDF.type, OWL.Class))
            graph.add((class_iri, SDO.identifier, Literal(cls.get("xmi.id"), datatype=HO.xmiId)))
            graph.add((class_iri, RDFS.isDefinedBy, context.source_iri))
            graph.add((class_iri, RDFS.label, Literal(element_name(cls, "cls"))))
            description = extract_description(cls)
            if description:
                graph.add((class_iri, SCHEMA.description, Literal(description)))
            for parent in cls.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
                namespaces=NS,
            ):
                graph.add((package_identifiers[parent], RDFS.member, class_iri))
            strategy = context.strategies.get("abstract_class")
            if strategy is not None:
                is_abstract = cls.get("isAbstract", "false").lower() == "true"
                children = [
                    class_identifiers[gen.get("subtype")]
                    for gen in context.tree.findall(".//UML:Generalization", namespaces=NS)
                    if gen.get("supertype") == cls.get("xmi.id") and gen.get("subtype") in class_identifiers
                ]
                strategy.apply(context, class_iri=class_iri, is_abstract=is_abstract, children=children)
        context.metadata["class_identifiers"] = class_identifiers
        return context


class BaseExtractSubclassRelations(TransformationStep):
    def transform(self, context):
        class_identifiers = context.extraction_index.identifiers_for("cls")
        relations = {}
        for gen in context.tree.findall(".//UML:Generalization", namespaces=NS):
            sub, sup = gen.get("subtype"), gen.get("supertype")
            if sub and sup and sub in class_identifiers and sup in class_identifiers:
                relations.setdefault(sub, []).append(class_identifiers[sup])
        strategy = context.strategies.get("inheritance")
        for sub, supers in relations.items():
            for superclass in supers:
                if strategy is None:
                    context.graph.add((class_identifiers[sub], RDFS.subClassOf, superclass))
                elif isinstance(strategy, IntersectionStrategy):
                    if superclass is supers[0]:
                        strategy.apply(context, subclass=class_identifiers[sub], superclass=superclass, superclasses=supers)
                else:
                    strategy.apply(context, subclass=class_identifiers[sub], superclass=superclass)
        return context
