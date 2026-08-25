from ..context import HO, NS, SCHEMA, bind_iso_prefixes, extract_description, TransformationContext
from ..identifiers import element_name
from .base import TransformationStep
from rdflib import Literal, OWL, RDFS, RDF, SDO, URIRef


class ExtractPackages(TransformationStep):
    def transform(self, context: TransformationContext):
        graph = context.graph
        bind_iso_prefixes(graph)
        package_identifiers = context.iri_registry.identifiers_for("mpkg")

        for pkg in context.tree.findall(".//UML:Package", namespaces=NS):
            package_iri = package_identifiers[pkg.get("xmi.id")]
            package_name = element_name(pkg, "mpkg")
            graph.add((package_iri, RDF.type, HO.ModelPackage))
            graph.add((package_iri, RDF.type, OWL.Ontology))
            graph.add((package_iri, SDO.identifier, Literal(pkg.get("xmi.id"), datatype=HO.xmiId)))
            graph.add((package_iri, RDFS.isDefinedBy, context.source_iri))
            graph.add((package_iri, RDFS.label, Literal(package_name)))

            description = extract_description(pkg)
            if description:
                graph.add((package_iri, SCHEMA.description, Literal(description)))

            graph.add((context.source_iri, RDFS.member, package_iri))
            parents = pkg.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
                namespaces=NS,
            )
            if parents and parents[0] in package_identifiers:
                graph.add((package_identifiers[parents[0]], RDFS.member, package_iri))

        return context


class ExtractPackageHierarchy(TransformationStep):
    def transform(self, context: TransformationContext):
        children_by_parent = {}
        for pkg in context.tree.findall(".//UML:Package", namespaces=NS):
            parents = pkg.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
                namespaces=NS,
            )
            if parents:
                children_by_parent.setdefault(parents[0], []).append(pkg)
        context.metadata["package_hierarchy"] = children_by_parent
        return context
