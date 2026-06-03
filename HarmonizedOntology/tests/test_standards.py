from pathlib import Path
from ho.standards import main
from ho.utils import OUTPUT_ROOT


def test_standards_main():
    XMI_DIR = Path("/Users/nick/work/iso/HMMG/XMI/ConceptualModels")
    OUTPUT_FILE = OUTPUT_ROOT / "standards.ttl"

    # check a standards.ttl file has been made
    Path.unlink(OUTPUT_FILE, missing_ok=True)
    main(XMI_DIR)
    assert Path.exists(OUTPUT_FILE)

    # check a particular file has been produced by looking for its name in the RDF
    target = None
    for f in XMI_DIR.glob("*.xml"):
        if "ISO " in f.name and "-1" in f.name:
            target = f
            break

    name = target.name.replace(" Edition 1", "")
    name = name.replace(".xml", "")
    assert f'"{name}"' in OUTPUT_FILE.read_text()
