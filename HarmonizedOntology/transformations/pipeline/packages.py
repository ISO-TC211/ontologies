from ..context import HO, NS, SCHEMA, bind_iso_prefixes, extract_description
from ..identifiers import element_name, make_iri, replace_iris_in_graph
from .base import TransformationStep
from rdflib import Literal, RDFS, RDF, SDO, URIRef


class BaseExtractPackages(TransformationStep):
    def transform(self, context):
        graph = context.graph
        bind_iso_prefixes(graph)
        package_iris = []

        for pkg in context.tree.findall(".//UML:Package", namespaces=NS):
            package_iri = URIRef("http://package/" + pkg.get("xmi.id"))
            package_name = element_name(pkg, "mpkg")
            graph.add((package_iri, RDF.type, HO.ModelPackage))
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
            if parents:
                graph.add((URIRef("http://package/" + parents[0]), RDFS.member, package_iri))
            package_iris.append((package_iri, make_iri("mpkg", package_name)))

        replace_iris_in_graph(graph, package_iris)
        return context


class BaseExtractPackageHierarchy(TransformationStep):
    def transform(self, context):
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
