# Harmonised Ontology Software

The software in this directory is a Python application that reads XMI files of the TC-211's Conceptual Models stored in 
the [HMG Repository](https://github.com/ISO-TC211/HMMG/tree/master/XMI/ConceptualModels) and produces a series of OWL
ontology files.

## Status

Currently - May 2026 - this software is at an early stage of development. An MVP version is expected in about August 2026.

## Installation

To use this software them, you just need a Python environment with `lxml` and `rdflib` installed.

They have minimal dependencies, other than Python standard library packages, because they just read XML files using `lxml` and produce RDF data using `rdflib`.

## Use

### Run one

The `packages.py`, `classes.py` and `predicates.py` modules (files) of this package can be run 
independently using Python on the command line from within the `HarmonizedOntology` folder like this:

```
python ho/classes.py {XMI_FILE_PATH}
```

Where `{XMI_FILE_PATH}` is the path to a Harmonized Model XMI file.

`standards.py` can by run like this:

```
python ho/standards.py {XMI_FOLDER_PATH}
```

Where `{XMI_FOLDER_PATH}` is the path to the folder containing XMI files.

### Run all

All modules can be run together like this from within the `HarmonizedOntology` folder:

```
python ho {XMI_FOLDER_PATH}
```

Where `{XMI_FOLDER_PATH}` is the path to the folder containing XMI files.

This command will run the `standards.py`, `packages.py`, `classes.py` and `predicates.py` modules.

## Tests

Tests for all functionality are being added to the `tests` folder. They use the `pytest` package and can be run on the
command line from within the `HarmonizedOntology` folder like this:

```
pytest test
```

## License & Rights

This software is licensed for reuse under the conditions of the [Creative Commons BY 4.0 License](https://creativecommons.org/licenses/by/4.0/), a copy of the deed of which is contained in this repository in the LICENSE file.

The software in this repository is copyright as follows:

&copy; International Organization for Standardization, 2026

## Contact

This software is managed by the TC-211's [Advisory Group 6 Group for Ontology Maintenance (GOM)](https://committee.iso.org/sites/tc211/home/about/advisory-groups.html). Please contact that group using the details at:

* <https://github.com/ISO-TC211/GOM#contact>