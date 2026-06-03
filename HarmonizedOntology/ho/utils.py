import re
from pathlib import Path
from typing import Literal as TypingLiteral
from urllib.parse import quote

from lxml import etree
from lxml.etree import _ElementTree
from rdflib import URIRef, Graph, Namespace

XMI_FILES_ROOT = Path(__file__).resolve().parents[3] / "HMMG" / "XMI" / "ConceptualModels"
OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "outputs"

NS = {"UML": "omg.org/UML1.3"}
UML_PACKAGE = f"{{{NS['UML']}}}Package"
UML_CLASS = f"{{{NS['UML']}}}Class"
HO = Namespace("https://def.isotc211.org/def/ho/")

ISO_PREFIXES = {
    "cls": "https://def.isotc211.org/class/",
    "ho": "https://def.isotc211.org/def/ho/",
    "mpkg": "https://def.isotc211.org/package/",
    "pred": "https://def.isotc211.org/pred/",
    "std": "https://def.isotc211.org/standard/",
}


def bind_iso_prefixes(g: Graph):
    """Adds standard ISO prefixes to a graph"""
    for k, v in ISO_PREFIXES.items():
        g.bind(k, v)


def element_name(element: etree._Element, element_type: TypingLiteral["mpkg", "cls", "pred", "std"]) -> str:
    """Finds a string literal name for an element or from a string"""
    if isinstance(element, etree._Element):
        name = element.get("name", "(unnamed element)")
    else:
        name = element
    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)

    if element_type == "pred":
        name = name.lower()
    # elif element_type in ["mpkg", "cls", "std"]:
    else:
        name = name.title()

    return name


def standard_name(name: str) -> str:
    """Creates a name for a standard from the file name"""
    name = name.replace(" Edition 1", "")
    name = name.replace(".xml", "")
    return name


def make_iri(prefix: str, elem: etree._Element | Path | str) -> URIRef:
    """Makes standardized IRIs for Standards, Packages and Classes and Predicates"""
    # if prefix == "pred":
    #     names = element.xpath(
    #         "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='lt']/@value",
    #         namespaces=NS,
    #     )
    #     if len(names) > 0:
    #         name = names[0].strip("+")
    #     else:
    #         return None
    if isinstance(elem, etree._Element):
        name = elem.get("name")
        if name is None:
            return None
        parts = name.split(" ")
        name = parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
    elif isinstance(elem, Path):
        name = elem.name.replace(".xml", "")
        name = name.replace(" Edition 1", "")
        name = name.replace(" ", "")
    else:
        name = elem.replace(" ", "")

    return URIRef(ISO_PREFIXES[prefix] + quote(name, safe=""))


def batch_replace_in_file(file_path: Path, replacements: list[tuple[str, str]]):
    """Replaces all instances of the first string per pair in replacements with the second"""

    # 1. Read the original content
    content = file_path.read_text(encoding="utf-8")

    # 2. Escape keys to handle special regex characters, then join with '|'
    # Sort by length descending to prevent shorter substrings matching inside longer ones
    replacements_sorted = sorted(replacements, key=lambda x: len(x[0]), reverse=True)
    pattern = re.compile("|".join(re.escape(old) for old, _ in replacements_sorted))

    # 3. Create a lookup dictionary for fast replacement matching
    lookup = dict(replacements_sorted)

    # 4. Perform the single-pass replacement
    # pattern.sub loops through matches; lookup[m.group(0)] finds the new string
    new_content = pattern.sub(lambda match: lookup[match.group(0)], content)

    # 5. Write the updated content back to the file
    file_path.write_text(new_content, encoding="utf-8")


def replace_iris_in_graph(graph: Graph, replacements: list[tuple[str, str]]) -> Graph:
    """Replaces all IRIs - the first string per pair in replacements - with the second in a graph"""

    # 1. Convert the string tuples into a dictionary of URIRef objects for fast lookup
    iri_map = {URIRef(old): URIRef(new) for old, new in replacements}

    # 2. Track triples to remove and triples to add
    triples_to_remove = []
    triples_to_add = []

    # 3. Scan all triples in the graph
    for subj, pred, obj in graph:
        # Check if any part of the triple matches our old IRIs
        new_subj = iri_map.get(subj, subj)
        new_pred = iri_map.get(pred, pred)
        new_obj = iri_map.get(obj, obj)

        # If a change occurred, queue the old triple for removal and the new one for addition
        if (new_subj != subj) or (new_pred != pred) or (new_obj != obj):
            triples_to_remove.append((subj, pred, obj))
            triples_to_add.append((new_subj, new_pred, new_obj))

    # 4. Apply the mutations safely outside the loop
    for triple in triples_to_remove:
        graph.remove(triple)

    for triple in triples_to_add:
        graph.add(triple)

    return graph


def make_outputs_folder(s_iri):
    """Makes or returns and existing outputs folder per standard"""

    d = OUTPUT_ROOT / str(s_iri).replace(ISO_PREFIXES["std"], "")
    # if d.exists() and d.is_dir():
    #     shutil.rmtree(d)
    Path.mkdir(d, exist_ok=True, parents=True)

    return d


def make_identifiers_map(tree: _ElementTree, prefix: TypingLiteral["std", "mpkg", "cls", "pred"]):
    """Creates a map (dictionary) of identifiers for a type of object - Standard, Package, Class or Predicate - in an Element Tree

    The map maps internal XMI IDs (keys) to IRIs (values)
    """

    ids = {}

    xpaths = {
        "std": "",
        "mpkg": "Package",
        "cls": "Class",
        "pred": "Association",
    }

    for elem in tree.findall(f".//UML:{xpaths[prefix]}", namespaces=NS):
        ids[elem.get("xmi.id")] = make_iri(prefix, elem)

    if prefix == "pred":
        for elem in tree.findall(f".//UML:Attribute", namespaces=NS):
            if elem.get("name") is not None:
                iri = make_iri(prefix, elem)
                if iri is not None:
                    ids[elem.xpath("UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value",
                                   namespaces=NS)[0].strip("{}")] = iri

    return ids


# class types not for class processing
EXCLUDED_CLASS_STEREOTYPES = {"dataType", "codeList", "CodeList"}
