"""Extracts ho:ModelPackage instances from UML:Package instances within an XMI file"""
import sys
from pathlib import Path

from lxml import etree
from lxml.etree import _ElementTree
from rdflib import Graph, Literal, URIRef, SDO, Namespace
from rdflib.namespace import OWL, RDF, RDFS

if __package__:
    from .utils import element_name, make_iri, bind_iso_prefixes, ISO_PREFIXES, replace_iris_in_graph, \
        NS, make_outputs_folder, HO, extract_description
else:
    from utils import element_name, make_iri, bind_iso_prefixes, ISO_PREFIXES, NS, make_outputs_folder, \
        replace_iris_in_graph, HO, extract_description

SCHEMA = Namespace(ISO_PREFIXES["schema"])


def print_package_hierarchy(tree: _ElementTree):
    """Prints the hierarchy of Packages as seen in an ElementTree"""
    packages = tree.xpath(
        "count(//UML:Package)",
        namespaces=NS,
    )

    print()
    print(f"Packages: {int(packages)}")
    print()

    print("Package Hierarchy")
    print("-------------------")

    package_elements = tree.findall(".//UML:Package", namespaces=NS)
    packages_by_id = {pkg.get("xmi.id"): pkg for pkg in package_elements}
    children_by_parent = {}

    for pkg in package_elements:
        parents = pkg.xpath(
            "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
            namespaces=NS,
        )
        if len(parents) > 0:
            children_by_parent.setdefault(parents[0], []).append(pkg)

    def print_package(pkg, depth=0):
        print(f"{'  ' * depth}{pkg.get('name')}")

        for child in sorted(children_by_parent.get(pkg.get("xmi.id"), []), key=lambda item: element_name(item[1], "mpkg")):
            print_package(child, depth + 1)

    for pkg in sorted(package_elements, key=lambda item: element_name(item[1], "mpkg")):
        parents = pkg.xpath(
            "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
            namespaces=NS,
        )
        if len(parents) == 0 or parents[0] not in packages_by_id:
            print_package(pkg)


def extract_packages(tree, s_iri, d) -> None:
    """Extracts objects of type UML:Package from an ElementTree and creates RDFS Property instances of ho:ModelPackage from them"""
    g = Graph()
    bind_iso_prefixes(g)
    
    # Declare schema:description as an annotation property
    g.add((SCHEMA.description, RDF.type, OWL.AnnotationProperty))

    package_iris = []

    for pkg in tree.findall(".//UML:Package", namespaces=NS):
        p_iri = URIRef("http://package/" + pkg.get("xmi.id"))
        p_name = element_name(pkg, "mpkg")

        g.add((p_iri, RDF.type, HO.ModelPackage))
        g.add((p_iri, SDO.identifier, Literal(pkg.get("xmi.id"), datatype=HO.xmiId)))
        g.add((p_iri, RDFS.isDefinedBy, s_iri))
        g.add((p_iri, RDFS.label, Literal(p_name)))
        
        # description from UML model
        description = extract_description(pkg)
        if description:
            g.add((p_iri, SCHEMA.description, Literal(description)))
        
        g.add((s_iri, RDFS.member, p_iri))

        parents = pkg.xpath(
            "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
            namespaces=NS)
        if len(parents) > 0:
            g.add((URIRef("http://package/" + parents[0]), RDFS.member, p_iri))

        package_iris.append((p_iri, make_iri("mpkg", p_name)))

    replace_iris_in_graph(g, package_iris)

    f = Path(d) / "packages.ttl"
    g.serialize(f, format="longturtle")


def main(xml_file_path) -> None:
    if not Path(xml_file_path).exists():
        raise SystemExit(f"XML file not found: {xml_file_path}")

    tree = etree.parse(str(xml_file_path))

    print_package_hierarchy(tree)

    s_iri = make_iri("std", xml_file_path)
    d = make_outputs_folder(s_iri)

    extract_packages(tree, s_iri, d)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python packages.py <path_to_xmi_file>")
    
    if not Path(sys.argv[1]).exists():
        raise SystemExit(f"XMI file not found: {sys.argv[1]}")

    print(f"Processing {sys.argv[1]}")
    main(sys.argv[1])
