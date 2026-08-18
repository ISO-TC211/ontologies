from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Literal as TypingLiteral
from urllib.parse import quote

from lxml import etree
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SDO

from ..rule import TransformationRule
from ..ruleset import TransformationRuleset

NS = {"UML": "omg.org/UML1.3"}
HO = Namespace("https://def.isotc211.org/def/ho/")

ISO_PREFIXES = {
    "cls": "https://def.isotc211.org/class/",
    "ho": "https://def.isotc211.org/def/ho/",
    "mpkg": "https://def.isotc211.org/package/",
    "pred": "https://def.isotc211.org/pred/",
    "std": "https://def.isotc211.org/standard/",
    "schema": "http://schema.org/",
}
SCHEMA = Namespace(ISO_PREFIXES["schema"])
EXCLUDED_CLASS_STEREOTYPES = {"dataType", "codeList", "CodeList"}


def bind_iso_prefixes(g: Graph):
    for k, v in ISO_PREFIXES.items():
        g.bind(k, v)


def extract_description(uml_element: etree._Element) -> str | None:
    descriptions = uml_element.xpath(
        "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='documentation']/@value",
        namespaces=NS,
    )
    if not descriptions:
        return None
    description = descriptions[0]
    description = html.unescape(description)
    description = re.sub(r"<[^>]+>", "", description)
    description = " ".join(description.split())
    return description if description else None


def element_name(element: etree._Element | str, element_type: TypingLiteral["mpkg", "cls", "pred", "std"]) -> str:
    if isinstance(element, etree._Element):
        name = element.get("name", "(unnamed element)")
    else:
        name = element

    name = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)

    if element_type == "pred":
        name = name.lower()
    else:
        name = name.title()

    return name


def make_iri(prefix: str, elem: etree._Element | Path | str) -> URIRef:
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


def replace_iris_in_graph(graph: Graph, replacements: list[tuple[str, str]]) -> Graph:
    iri_map = {URIRef(old): URIRef(new) for old, new in replacements}
    triples_to_remove = []
    triples_to_add = []
    for subj, pred, obj in graph:
        new_subj = iri_map.get(subj, subj)
        new_pred = iri_map.get(pred, pred)
        new_obj = iri_map.get(obj, obj)
        if (new_subj != subj) or (new_pred != pred) or (new_obj != obj):
            triples_to_remove.append((subj, pred, obj))
            triples_to_add.append((new_subj, new_pred, new_obj))
    for triple in triples_to_remove:
        graph.remove(triple)
    for triple in triples_to_add:
        graph.add(triple)
    return graph


def has_excluded_stereotype(uml_class: etree._Element) -> bool:
    stereotypes = uml_class.findall("UML:ModelElement.stereotype/UML:Stereotype", namespaces=NS)
    return any(stereotype.get("name") in EXCLUDED_CLASS_STEREOTYPES for stereotype in stereotypes)


def make_identifiers_map(tree, prefix: TypingLiteral["std", "mpkg", "cls", "pred"]):
    ids = {}
    xpaths = {"std": "", "mpkg": "Package", "cls": "Class", "pred": "Association"}

    for elem in tree.findall(f".//UML:{xpaths[prefix]}", namespaces=NS):
        ids[elem.get("xmi.id")] = make_iri(prefix, elem)

    if prefix == "pred":
        for elem in tree.findall(".//UML:Attribute", namespaces=NS):
            if elem.get("name") is not None:
                iri = make_iri(prefix, elem)
                if iri is not None:
                    ids[elem.xpath(
                        "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value",
                        namespaces=NS,
                    )[0].strip("{}")] = iri
    return ids


class BaseAddSchemaDescriptionProperty(TransformationRule):
    def transform(self, context):
        bind_iso_prefixes(context.graph)
        context.graph.add((SCHEMA.description, RDF.type, OWL.AnnotationProperty)) # seems off to me. Why not "add annotation property"?
        return context


class BaseExtractPackages(TransformationRule):
    def transform(self, context):
        graph = context.graph
        bind_iso_prefixes(graph)
        package_iris = []

        for pkg in context.tree.findall(".//UML:Package", namespaces=NS):
            p_iri = URIRef("http://package/" + pkg.get("xmi.id"))
            p_name = element_name(pkg, "mpkg")
            graph.add((p_iri, RDF.type, HO.ModelPackage))
            graph.add((p_iri, SDO.identifier, Literal(pkg.get("xmi.id"), datatype=HO.xmiId)))
            graph.add((p_iri, RDFS.isDefinedBy, context.source_iri))
            graph.add((p_iri, RDFS.label, Literal(p_name)))

            description = extract_description(pkg)
            if description:
                graph.add((p_iri, SCHEMA.description, Literal(description)))

            graph.add((context.source_iri, RDFS.member, p_iri))

            parents = pkg.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
                namespaces=NS,
            )
            if len(parents) > 0:
                graph.add((URIRef("http://package/" + parents[0]), RDFS.member, p_iri))

            package_iris.append((p_iri, make_iri("mpkg", p_name)))

        replace_iris_in_graph(graph, package_iris)
        return context


class BaseExtractPackageHierarchy(TransformationRule):
    def transform(self, context):
        package_elements = context.tree.findall(".//UML:Package", namespaces=NS)
        children_by_parent = {}
        for pkg in package_elements:
            parents = pkg.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='parent']/@value",
                namespaces=NS,
            )
            if len(parents) > 0:
                children_by_parent.setdefault(parents[0], []).append(pkg)
        context.metadata["package_hierarchy"] = children_by_parent
        return context


class BaseExtractClasses(TransformationRule):
    def transform(self, context):
        graph = context.graph
        bind_iso_prefixes(graph)
        package_identifiers = make_identifiers_map(context.tree, "mpkg")
        class_identifiers = make_identifiers_map(context.tree, "cls")

        for cls in context.tree.findall(".//UML:Class", namespaces=NS):
            if has_excluded_stereotype(cls):
                continue

            c = class_identifiers[cls.get("xmi.id")]
            graph.add((c, RDF.type, OWL.Class))
            graph.add((c, SDO.identifier, Literal(cls.get("xmi.id"), datatype=HO.xmiId)))
            graph.add((c, RDFS.isDefinedBy, context.source_iri))
            graph.add((c, RDFS.label, Literal(element_name(cls, "cls"))))

            description = extract_description(cls)
            if description:
                graph.add((c, SCHEMA.description, Literal(description)))

            parents = cls.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='package']/@value",
                namespaces=NS,
            )
            if len(parents) > 0:
                for parent in parents:
                    graph.add((package_identifiers[parent], RDFS.member, c))

        context.metadata["class_identifiers"] = class_identifiers
        return context


class BaseExtractSubclassRelations(TransformationRule):
    def transform(self, context):
        class_identifiers = make_identifiers_map(context.tree, "cls")
        for gen in context.tree.findall(".//UML:Generalization", namespaces=NS):
            sub = gen.get("subtype")
            sup = gen.get("supertype")
            if sub and sup:
                if sub in class_identifiers and sup in class_identifiers:
                    context.graph.add((class_identifiers[sub], RDFS.subClassOf, class_identifiers[sup]))
        return context


class BaseExtractAssociations(TransformationRule):
    def transform(self, context):
        graph = context.graph
        predicate_identifiers = make_identifiers_map(context.tree, "pred")
        for pred in context.tree.findall(".//UML:Association", namespaces=NS):
            if pred.get("name") is not None:
                p = predicate_identifiers[pred.get("xmi.id")]
                graph.add((p, RDF.type, RDF.Property))
                graph.add((p, SDO.identifier, Literal(pred.get("xmi.id"), datatype=HO.xmiId)))
                graph.add((p, RDFS.isDefinedBy, context.source_iri))
                graph.add((p, RDFS.label, Literal(element_name(pred, "pred"))))

                description = extract_description(pred)
                if description:
                    graph.add((p, SCHEMA.description, Literal(description)))

                domain = pred.xpath(
                    "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_sourceName']/@value",
                    namespaces=NS,
                )
                if len(domain) > 0:
                    graph.add((p, RDFS.domain, make_iri("cls", str(domain[0]))))

                range_name = pred.xpath(
                    "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_targetName']/@value",
                    namespaces=NS,
                )
                if len(range_name) > 0:
                    graph.add((p, RDFS.range, make_iri("cls", str(range_name[0]))))
        return context


class BaseExtractAttributes(TransformationRule):
    def transform(self, context):
        graph = context.graph
        predicate_identifiers = make_identifiers_map(context.tree, "pred")
        for pred in context.tree.findall(".//UML:Attribute", namespaces=NS):
            cl = pred.xpath("ancestor::UML:Class[1]/UML:ModelElement.stereotype/UML:Stereotype/@name", namespaces=NS)
            if len(cl) > 0 and cl[0] in EXCLUDED_CLASS_STEREOTYPES:
                continue

            ids = pred.xpath(
                "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='ea_guid']/@value",
                namespaces=NS,
            )
            if len(ids) > 0:
                attribute_id = ids[0].strip("{}")
                p = predicate_identifiers[attribute_id]
                graph.add((p, RDF.type, RDF.Property))
                graph.add((p, SDO.identifier, Literal(attribute_id, datatype=HO.xmiId)))
                graph.add((p, RDFS.isDefinedBy, context.source_iri))
                graph.add((p, RDFS.label, Literal(element_name(pred, "pred"))))

                description = extract_description(pred)
                if description:
                    graph.add((p, SCHEMA.description, Literal(description)))

                domain = pred.xpath("ancestor::UML:Class[1]/@name", namespaces=NS)
                if len(domain) > 0:
                    graph.add((p, RDFS.domain, make_iri("cls", str(domain[0]))))

                range_names = pred.xpath(
                    "UML:ModelElement.taggedValue/UML:TaggedValue[@tag='type']/@value",
                    namespaces=NS,
                )
                if len(range_names) > 0:
                    graph.add((p, RDFS.range, make_iri("cls", str(range_names[0]))))
        return context

class BaseRuleSet(TransformationRuleset):
    """Default XMI-to-RDF transformation ruleset for ho extraction."""

    def __init__(self, rule_names=None):
        rules = [
            BaseAddSchemaDescriptionProperty(),
            BaseExtractPackages(),
            BaseExtractPackageHierarchy(),
            BaseExtractClasses(),
            BaseExtractSubclassRelations(),
            BaseExtractAssociations(),
            BaseExtractAttributes(),
        ]
        if rule_names is not None:
            if isinstance(rule_names, str):
                rule_names = [rule_names]
            rules = [rule for rule in rules if rule.name in rule_names]
        super().__init__(rules)
