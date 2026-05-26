from pathlib import Path

from lxml import etree
from lxml.etree import _ElementTree
from rdflib import Graph, Literal
from rdflib.namespace import OWL, RDF, RDFS, SDO

try:
    from .utils import element_name, make_iri, bind_iso_prefixes, ISO_PREFIXES, make_outputs_folder, HO, XMI_FILES_ROOT, \
        NS, \
        make_identifiers_map, EXCLUDED_CLASS_STEREOTYPES
except ImportError:
    from utils import element_name, make_iri, bind_iso_prefixes, ISO_PREFIXES, make_outputs_folder, HO, XMI_FILES_ROOT, \
        NS, make_identifiers_map

UML_CLASS = f"{{{NS['UML']}}}Class"


def child_classes(package: etree._Element) -> list[etree._Element]:
    owned_elements = package.find("UML:Namespace.ownedElement", namespaces=NS)
    if owned_elements is None:
        return []

    return [child for child in owned_elements if child.tag == UML_CLASS]


def has_excluded_stereotype(uml_class: etree._Element) -> bool:
    stereotypes = uml_class.findall("UML:ModelElement.stereotype/UML:Stereotype", namespaces=NS)
    return any(stereotype.get("name") in EXCLUDED_CLASS_STEREOTYPES for stereotype in stereotypes)


def print_class_list(tree: _ElementTree):
    packages = tree.xpath(
        "count(//UML:Package)",
        namespaces=NS,
    )

    classes = tree.xpath(
        "count(//UML:Class)",
        namespaces=NS,
    )
    print()
    print(f"Packages: {int(packages)}")
    print(f"Classes: {int(classes)}")
    print()

    package_elements = tree.findall(".//UML:Package", namespaces=NS)
    packages_by_id = {pkg.get("xmi.id"): pkg for pkg in package_elements}
    classes_by_package = {}

    for cls in tree.findall(".//UML:Class", namespaces=NS):
        if has_excluded_stereotype(cls):
            continue

        packages = cls.xpath(
            "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
            namespaces=NS,
        )
        if len(packages) > 0:
            classes_by_package.setdefault(packages[0], []).append(cls)

    for package_id, pkg in sorted(packages_by_id.items(), key=lambda item: element_name(item[1])):
        package_classes = classes_by_package.get(package_id, [])
        if len(package_classes) == 0:
            continue

        print(element_name(pkg))
        for cls in sorted(package_classes, key=element_name):
            print(f"  {element_name(cls)}")
        print()

    class_elements = tree.findall(".//UML:Class", namespaces=NS)
    classes_by_id = {cls.get("xmi.id"): cls for cls in class_elements}
    class_names = {element_name(cls) for cls in class_elements}
    children_by_parent = {}
    child_names = set()

    for gen in tree.findall(".//UML:Generalization", namespaces=NS):
        child_id = gen.get("subtype")
        parent_id = gen.get("supertype")
        if child_id in classes_by_id and parent_id in classes_by_id:
            child_name = element_name(classes_by_id[child_id])
            parent_name = element_name(classes_by_id[parent_id])
            if child_name != parent_name:
                children_by_parent.setdefault(parent_name, set()).add(child_name)
                child_names.add(child_name)

    def print_class_hierarchy(class_name, depth=0, ancestors=None):
        if ancestors is None:
            ancestors = set()

        print(f"{'  ' * depth}{class_name}")

        if class_name in ancestors:
            return

        for child_name in sorted(children_by_parent.get(class_name, [])):
            print_class_hierarchy(child_name, depth + 1, ancestors | {class_name})

    print("Class hierarchy")
    for class_name in sorted(class_names):
        if class_name not in child_names:
            print_class_hierarchy(class_name)


def extract_classes(tree, s_iri, d):
    g = Graph()
    bind_iso_prefixes(g)

    package_identifiers = make_identifiers_map(tree, "mpkg")
    class_identifiers = make_identifiers_map(tree, "cls")

    for cls in tree.findall(".//UML:Class", namespaces=NS):
        if has_excluded_stereotype(cls):
            continue

        c = class_identifiers[cls.get("xmi.id")]

        # primary details
        g.add((c, RDF.type, OWL.Class))
        g.add((c, SDO.identifier, Literal(cls.get("xmi.id"), datatype=HO.xmiId)))
        g.add((c, RDFS.isDefinedBy, s_iri))
        g.add((c, RDFS.label, Literal(element_name(cls))))

        # package
        parents = cls.xpath(
            "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
            namespaces=NS,
        )
        if len(parents) > 0:
            for parent in parents:
                g.add((package_identifiers[parent], RDFS.member, c))

    # for k, v in class_identifiers.items():
    #     print(k, v)

    # subclass of
    for gen in tree.findall(".//UML:Generalization", namespaces=NS):
        sub = gen.get("subtype")
        sup = gen.get("supertype")
        if sub and sup:
            if sub in class_identifiers.keys() and sup in class_identifiers.keys():
                g.add((class_identifiers[sub], RDFS.subClassOf, class_identifiers[sup]))

    g.serialize(Path(d) / "classes.ttl", format="longturtle")


def main(xml_file_path) -> None:
    if not xml_file_path.exists():
        raise SystemExit(f"XML file not found: {xml_file_path}")

    tree = etree.parse(str(xml_file_path))

    print_class_list(tree)

    s_iri = make_iri("std", xml_file_path)
    d = make_outputs_folder(s_iri)

    extract_classes(tree, s_iri, d)


if __name__ == "__main__":
    main(XMI_FILES_ROOT / "ISO 19160-1 Edition 1.xml")
    # main(XMI_FILES_ROOT / "ISO 19115-1 Edition 1.xml")
    # main(XMI_FILES_ROOT / "ISO 19157-1 Edition 1.xml")
