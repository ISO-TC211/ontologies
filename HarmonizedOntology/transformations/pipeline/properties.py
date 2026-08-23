from ..context import EXCLUDED_CLASS_STEREOTYPES, HO, NS, SCHEMA, bind_iso_prefixes, extract_description, is_self_describing_enumeration
from ..identifiers import element_name, make_iri
from .base import TransformationStep
from rdflib import Literal, OWL, RDF, RDFS, SDO, URIRef


class BaseAddSchemaDescriptionProperty(TransformationStep):
    def transform(self, context):
        bind_iso_prefixes(context.graph)
        context.graph.add((SCHEMA.description, RDF.type, OWL.AnnotationProperty))
        return context


class BaseExtractAssociations(TransformationStep):
    def transform(self, context):
        graph = context.graph
        predicate_identifiers = context.extraction_index.identifiers_for("pred")
        for pred in context.tree.findall(".//UML:Association", namespaces=NS):
            if pred.get("name") is None:
                continue
            predicate_iri = predicate_identifiers[pred.get("xmi.id")]
            graph.add((predicate_iri, RDF.type, RDF.Property))
            graph.add((predicate_iri, SDO.identifier, Literal(pred.get("xmi.id"), datatype=HO.xmiId)))
            graph.add((predicate_iri, RDFS.isDefinedBy, context.source_iri))
            graph.add((predicate_iri, RDFS.label, Literal(element_name(pred, "pred"))))
            description = extract_description(pred)
            if description:
                graph.add((predicate_iri, SCHEMA.description, Literal(description)))
            domain = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_sourceName']/@value", namespaces=NS)
            if domain:
                graph.add((predicate_iri, RDFS.domain, make_iri("cls", str(domain[0]))))
            range_name = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_targetName']/@value", namespaces=NS)
            if range_name:
                graph.add((predicate_iri, RDFS.range, make_iri("cls", str(range_name[0]))))
        return context


class BaseExtractAttributes(TransformationStep):
    def transform(self, context):
        graph = context.graph
        predicate_identifiers = context.extraction_index.identifiers_for("pred")
        for pred in context.tree.findall(".//UML:Attribute", namespaces=NS):
            class_stereotypes = pred.xpath("ancestor::UML:Class[1]/UML:ModelElement.stereotype/UML:Stereotype/@name", namespaces=NS)
            if class_stereotypes and class_stereotypes[0] in EXCLUDED_CLASS_STEREOTYPES:
                continue
            ids = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value", namespaces=NS)
            if not ids:
                continue
            attribute_id = ids[0].strip("{}")
            predicate_iri = predicate_identifiers[attribute_id]
            graph.add((predicate_iri, RDF.type, RDF.Property))
            graph.add((predicate_iri, SDO.identifier, Literal(attribute_id, datatype=HO.xmiId)))
            graph.add((predicate_iri, RDFS.isDefinedBy, context.source_iri))
            graph.add((predicate_iri, RDFS.label, Literal(element_name(pred, "pred"))))
            description = extract_description(pred)
            if description:
                graph.add((predicate_iri, SCHEMA.description, Literal(description)))
            domain = pred.xpath("ancestor::UML:Class[1]/@name", namespaces=NS)
            if domain:
                graph.add((predicate_iri, RDFS.domain, make_iri("cls", str(domain[0]))))
            range_names = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value", namespaces=NS)
            if range_names:
                graph.add((predicate_iri, RDFS.range, make_iri("cls", str(range_names[0]))))
        return context


class BaseExtractEnumerations(TransformationStep):
    def transform(self, context):
        strategy = context.strategies.get("enumeration")
        if strategy is None:
            return context
        for cls in context.tree.findall(".//UML:Class", namespaces=NS):
            stereotypes = cls.findall("UML:ModelElement.stereotype/UML:Stereotype", namespaces=NS)
            if not any(st.get("name") == "enumeration" for st in stereotypes):
                continue
            values = [attr.get("name") for attr in cls.findall("UML:Attribute", namespaces=NS) if attr.get("name")]
            attributes = []
            for attr in context.tree.findall(".//UML:Attribute", namespaces=NS):
                range_names = attr.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value", namespaces=NS)
                if cls.get("xmi.id") not in range_names and cls.get("name") not in range_names:
                    continue
                ids = attr.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value", namespaces=NS)
                if ids:
                    attributes.append(make_iri("pred", ids[0].strip("{}")))
            strategy.apply(context, class_iri=make_iri("cls", cls), values=values, self_describing=is_self_describing_enumeration(values), attributes=attributes)
        return context
