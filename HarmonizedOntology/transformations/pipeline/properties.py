from ..context import EXCLUDED_CLASS_STEREOTYPES, HO, NS, SCHEMA, bind_iso_prefixes, extract_description
from ..identifiers import element_name
from ..context import TransformationContext
from .base import TransformationStep
from rdflib import Literal, OWL, RDF, RDFS, SDO, URIRef


def class_iri_for_reference(context, reference, package_id=None, xmi_id=None):
    if xmi_id:
        return context.iri_registry.iri_for(xmi_id)
    return context.iri_registry.class_iri_for_reference(reference, package_id)


class AddSchemaDescriptionProperty(TransformationStep):
    def transform(self, context:TransformationContext):
        bind_iso_prefixes(context.graph)
        context.graph.add((SCHEMA.description, RDF.type, OWL.AnnotationProperty))
        return context


class ExtractAssociations(TransformationStep):
    def transform(self, context:TransformationContext):
        graph = context.graph
        predicate_identifiers = context.iri_registry.identifiers_for("pred")
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
            ends = pred.xpath(
                "UML:Association.connection/UML:AssociationEnd",
                namespaces=NS,
            )
            domain = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_sourceName']/@value", namespaces=NS)
            if domain:
                package = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value", namespaces=NS)
                source_id = ends[0].get("type") if ends else None
                graph.add((predicate_iri, RDFS.domain, class_iri_for_reference(context, str(domain[0]), package[0] if package else None, source_id)))
            range_name = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_targetName']/@value", namespaces=NS)
            if range_name:
                package = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value", namespaces=NS)
                target_id = ends[1].get("type") if len(ends) > 1 else None
                graph.add((predicate_iri, RDFS.range, class_iri_for_reference(context, str(range_name[0]), package[0] if package else None, target_id)))
        return context


class ExtractAttributes(TransformationStep):
    def transform(self, context:TransformationContext):
        graph = context.graph
        predicate_identifiers = context.iri_registry.identifiers_for("pred")
        for pred in context.tree.findall(".//UML:Attribute", namespaces=NS):
            owner_ids = pred.xpath(
                "ancestor::*[self::UML:Class or self::UML:Interface][1]/@xmi.id",
                namespaces=NS,
            )
            # XMI also contains attributes on UML:ClassifierRole and other
            # diagram/runtime elements. They are not ontology properties and
            # therefore are not registered by IRIService.
            if not owner_ids:
                continue
            class_stereotypes = pred.xpath(
                "ancestor::*[self::UML:Class or self::UML:Interface][1]/UML:ModelElement.stereotype/UML:Stereotype/@name",
                namespaces=NS,
            )
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
            domain = pred.xpath(
                "ancestor::*[self::UML:Class or self::UML:Interface][1]/@name",
                namespaces=NS,
            )
            if domain:
                owner = pred.xpath(
                    "ancestor::*[self::UML:Class or self::UML:Interface][1]/UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
                    namespaces=NS,
                )
                graph.add((predicate_iri, RDFS.domain, class_iri_for_reference(
                    context,
                    str(domain[0]),
                    owner[0] if owner else None,
                    owner_ids[0] if owner_ids else None,
                )))
            range_names = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value", namespaces=NS)
            if range_names:
                owner = pred.xpath(
                    "ancestor::*[self::UML:Class or self::UML:Interface][1]/UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
                    namespaces=NS,
                )
                type_ids = pred.xpath(
                    "UML:StructuralFeature.type/UML:Classifier/@xmi.idref",
                    namespaces=NS,
                )
                graph.add((predicate_iri, RDFS.range, class_iri_for_reference(
                    context,
                    str(range_names[0]),
                    owner[0] if owner else None,
                    type_ids[0] if type_ids else None,
                )))
        return context


class ExtractEnumerations(TransformationStep):
    def _is_self_describing_enumeration(self, values):
        """Return whether enumeration members are readable words rather than codes."""
        return bool(values) and all(
            value.replace(" ", "").replace("-", "").replace("_", "").isalpha()
            for value in values
    )

    def transform(self, context:TransformationContext):
        strategy = context.strategies.get("enumeration")
        if strategy is None:
            return context
        for cls in context.tree.findall(".//UML:Class", namespaces=NS):
            stereotypes = cls.findall("UML:ModelElement.stereotype/UML:Stereotype", namespaces=NS)
            if not any(st.get("name") == "enumeration" for st in stereotypes):
                continue
            values = [attr.get("name") for attr in cls.findall("UML:Attribute", namespaces=NS) if attr.get("name")]
            attributes = []
            predicate_identifiers = context.iri_registry.identifiers_for("pred")
            for attr in context.tree.findall(".//UML:Attribute", namespaces=NS):
                range_names = attr.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value", namespaces=NS)
                if cls.get("xmi.id") not in range_names and cls.get("name") not in range_names:
                    continue
                ids = attr.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value", namespaces=NS)
                if ids:
                    attributes.append(predicate_identifiers[ids[0].strip("{}")])
            class_identifiers = context.iri_registry.identifiers_for("cls")
            strategy.apply(context, class_iri=class_identifiers[cls.get("xmi.id")], values=values, self_describing=self._is_self_describing_enumeration(values), attributes=attributes)
        return context
