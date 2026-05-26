from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import RDF, DCTERMS, SDO

try:
    from .utils import standard_name, make_iri, bind_iso_prefixes
except ImportError:
    from utils import standard_name, make_iri, bind_iso_prefixes

ROOT = Path(__file__).resolve().parents[1]
CONCEPTUAL_MODELS = ROOT / "XMI" / "ConceptualModels"
EXCLUDED_NAME_PARTS = ("Amendment", "Complete", "DIS", "AWI", "CD", "TS", "Edition 2")


def is_excluded(filename: str) -> bool:
    return any(part in filename for part in EXCLUDED_NAME_PARTS)


def main() -> None:
    g = Graph()
    bind_iso_prefixes(g)

    for xml_file in sorted(CONCEPTUAL_MODELS.glob("*.xml")):
        if "-1" in xml_file.name and not is_excluded(xml_file.name):
            sn = standard_name(xml_file.name)
            s_iri = make_iri("std", xml_file)
            g.add((s_iri, RDF.type, DCTERMS.Standard))
            g.add((s_iri, SDO.name, Literal(sn)))

    ttl = g.serialize(format="longturtle")

    with open(Path(__file__).parent / "standards.ttl", "w") as f:
        f.write(ttl)

    print(ttl)


if __name__ == "__main__":
    main()
