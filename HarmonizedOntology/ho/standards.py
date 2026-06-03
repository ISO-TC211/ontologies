"""
Creates a standards.ttl file containing a list of the standards in RDF, as seen in the target XMI directory
"""

import sys
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import RDF, DCTERMS, SDO

if __package__:
    from .utils import standard_name, make_iri, bind_iso_prefixes, OUTPUT_ROOT
else:
    from utils import standard_name, make_iri, bind_iso_prefixes, OUTPUT_ROOT

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_NAME_PARTS = ("Amendment", "Complete", "DIS", "AWI", "CD", "TS", "Edition 2")


def is_excluded(filename: str) -> bool:
    return any(part in filename for part in EXCLUDED_NAME_PARTS)


def main(xmi_files_root: Path) -> None:
    g = Graph()
    bind_iso_prefixes(g)

    for xml_file in sorted(xmi_files_root.glob("*.xml")):
        if "-1" in xml_file.name and not is_excluded(xml_file.name):
            sn = standard_name(xml_file.name)
            s_iri = make_iri("std", xml_file)
            g.add((s_iri, RDF.type, DCTERMS.Standard))
            g.add((s_iri, SDO.name, Literal(sn)))

    ttl = g.serialize(format="longturtle")

    with open(OUTPUT_ROOT / "standards.ttl", "w") as f:
        f.write(ttl)

    print(ttl)


if __name__ == "__main__":
    if not Path.exists(sys.argv[1]):
        raise SystemExit(f"XMI directory not found: {sys.argv[1]}")

    print(f"Processing {sys.argv[1]}")
    main(Path(sys.argv[1]))
