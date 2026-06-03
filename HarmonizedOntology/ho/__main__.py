"""The entry point for this package: runs all the other executable modules (files)"""
import sys
from pathlib import Path

if __package__:
    from .standards import main as standards_main
    from .packages import main as packages_main
    from .classes import main as classes_main
    from .predicates import main as predicates_main
else:
    from standards import main as standards_main
    from packages import main as packages_main
    from classes import main as classes_main
    from predicates import main as predicates_main

if not Path(sys.argv[1]).is_dir():
    raise FileNotFoundError(f"{sys.argv[1]} is not a directory")
else:
    XMI_DIR = Path(sys.argv[1])

    standards_main(XMI_DIR)

    for f in XMI_DIR.glob("*.xml"):
        if "ISO " in f.name and "-1" in f.name:
            packages_main(f)
            classes_main(f)
            predicates_main(f)
