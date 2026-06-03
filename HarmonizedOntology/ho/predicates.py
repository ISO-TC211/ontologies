"""Extracts rdf:Property instances from various classes of object within an XMI file"""
import sys
from pathlib import Path

from lxml import etree
from lxml.etree import _ElementTree
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SDO

if __package__:
    from .utils import element_name, make_iri, bind_iso_prefixes, ISO_PREFIXES, make_outputs_folder, HO, \
        NS, make_identifiers_map, EXCLUDED_CLASS_STEREOTYPES
else:
    from utils import element_name, make_iri, bind_iso_prefixes, ISO_PREFIXES, make_outputs_folder, HO, \
        NS, make_identifiers_map, EXCLUDED_CLASS_STEREOTYPES


def print_predicate_list(tree: _ElementTree):
    """Prints the list of Predicates as seen in an ElementTree"""
    packages = tree.xpath(
        "count(//UML:Package)",
        namespaces=NS,
    )

    classes = tree.xpath(
        "count(//UML:Association)",
        namespaces=NS,
    )
    print()
    print(f"Packages: {int(packages)}")
    print(f"Association: {int(classes)}")
    print()

    print("Predicates")
    print("-------------------")

    # Associations
    print("Associations")
    print("-------------------")
    print()
    for pred in tree.findall(".//UML:Association", namespaces=NS):
        if pred.get("name") is not None:
            # print(pred.get("xmi.id"))
            print(pred.get("name"))

            domain = pred.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_sourceName']/@value",
                namespaces=NS,
            )
            if len(domain) > 0:
                print(f"\tdomain: {domain[0]}")

            range = pred.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_targetName']/@value",
                namespaces=NS,
            )
            if len(range) > 0:
                print(f"\trange: {range[0]}")
            print()

    print()
    print()

    # Attributes
    print("Attributes")
    print("-------------------")
    for pred in tree.findall(".//UML:Attribute", namespaces=NS):
        # exclude CodeLists
        cl = pred.xpath("ancestor::UML:Class[1]/UML:ModelElement.stereotype/UML:Stereotype/@name", namespaces=NS)
        if len(cl) > 0:
            if cl[0] in EXCLUDED_CLASS_STEREOTYPES:
                continue

        print(pred.get("name"))

        domain = pred.xpath("ancestor::UML:Class[1]/@name", namespaces=NS)
        if len(domain) > 0:
            print(f"\tdomain: {domain[0]}")

        range = pred.xpath(
            "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value",
            namespaces=NS,
        )
        if len(range) > 0:
            print(f"\trange: {range[0]}")
        print()


def extract_predicates(tree, s_iri, d):
    """Extracts objects of type UML:Association and UML:Attribute from an ElementTree and creates RDFS Property instances from them"""
    g = Graph()
    bind_iso_prefixes(g)

    package_identifiers = make_identifiers_map(tree, "mpkg")
    class_identifiers = make_identifiers_map(tree, "cls")
    predicate_identifiers = make_identifiers_map(tree, "pred")

    # import pprint
    # pprint.pprint(class_identifiers)
    # exit()

    # Associations
    for pred in tree.findall(".//UML:Association", namespaces=NS):
        if pred.get("name") is not None:
            p = predicate_identifiers[pred.get("xmi.id")]
            g.add((p, RDF.type, RDF.Property))
            g.add((p, SDO.identifier, Literal(pred.get("xmi.id"), datatype=HO.xmiId)))
            g.add((p, RDFS.isDefinedBy, s_iri))
            g.add((p, RDFS.label, Literal(element_name(pred, "pred"))))

            domain = pred.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_sourceName']/@value",
                namespaces=NS,
            )
            if len(domain) > 0:
                class_iri = make_iri("cls", str(domain[0]))
                g.add((p, RDFS.domain, class_iri))

            range = pred.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_targetName']/@value",
                namespaces=NS,
            )
            if len(range) > 0:
                class_iri = make_iri("cls", str(range[0]))
                g.add((p, RDFS.range, class_iri))

    # Attributes
    for pred in tree.findall(".//UML:Attribute", namespaces=NS):
        # exclude CodeLists
        cl = pred.xpath("ancestor::UML:Class[1]/UML:ModelElement.stereotype/UML:Stereotype/@name", namespaces=NS)
        if len(cl) > 0:
            if cl[0] in EXCLUDED_CLASS_STEREOTYPES:
                continue

        ids = pred.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value", namespaces=NS)
        if len(ids) > 0:
            id = ids[0].strip("{}")
            p = predicate_identifiers[id]

            g.add((p, RDF.type, RDF.Property))
            g.add((p, SDO.identifier, Literal(id, datatype=HO.xmiId)))
            g.add((p, RDFS.isDefinedBy, s_iri))
            g.add((p, RDFS.label, Literal(element_name(pred, "pred"))))

            domain = pred.xpath("ancestor::UML:Class[1]/@name", namespaces=NS)
            if len(domain) > 0:
                class_iri = make_iri("cls", str(domain[0]))
                g.add((p, RDFS.domain, class_iri))

            range = pred.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value",
                namespaces=NS,
            )
            if len(range) > 0:
                class_iri = make_iri("cls", str(range[0]))
                g.add((p, RDFS.range, class_iri))

    g.serialize(Path(d) / "predicates.ttl", format="longturtle")


def main(xml_file_path) -> None:
    if not xml_file_path.exists():
        raise SystemExit(f"XML file not found: {xml_file_path}")

    tree = etree.parse(str(xml_file_path))

    print_predicate_list(tree)

    s_iri = make_iri("std", xml_file_path)
    d = make_outputs_folder(s_iri)

    extract_predicates(tree, s_iri, d)


if __name__ == "__main__":
    if not Path.exists(sys.argv[1]):
        raise SystemExit(f"XMI file not found: {sys.argv[1]}")

    print(f"Processing {sys.argv[1]}")
    main(sys.argv[1])
