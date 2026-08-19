# ISO/TC-211 Harmonized Ontology

This directory contains the software and tools for generating OWL ontologies from the ISO/TC-211's Harmonized Model XMI files, with support for transformations and ablation studies.

## Overview

The Harmonized Ontology project transforms ISO/TC-211 conceptual models (represented as XMI files) into Semantic Web ontologies (OWL/RDF). The software is organized into a `transformations/` library containing the core transformation engine, rules, and tests.

## Quick Start

### Installation

Install dependencies from the root requirements.txt:

```bash
pip install -r requirements.txt
```

### Running Transformations

Use the root-level `main.py` as your entry point for all transformation and ablation work:

**Run full transformation:**
```bash
python main.py transform path/to/xmi/file.xml
```

**Run transformation with specific rules:**
```bash
python main.py transform path/to/xmi/file.xml --rules BaseExtractPackages BaseExtractClasses
```

**Run ablation study (remove specific rules to study their impact):**
```bash
python main.py ablate path/to/xmi/file.xml --ablate BaseExtractClasses
```

### Running Tests

Execute the test suite from the `HarmonizedOntology` directory:

```bash
pytest transformations/tests
```

## Directory Structure

```
HarmonizedOntology/
├── main.py                   # Entry point for transformations and ablations
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── transformations/          # Core transformation library
    ├── __init__.py
    ├── __main__.py           # Batch transformation runner
    ├── main.py               # Transformation execution engine
    ├── transformation_rule.py # Base transformation rule class
    ├── transformation_ruleset.py # Rule set management
    ├── transformations.py    # Core transformation logic
    └── tests/                # Test suite
        ├── __init__.py
        └── test_standards.py
```

## Transformations Library

The `transformations/` directory contains the core transformation engine for converting ISO/TC-211 XMI conceptual model files into OWL/RDF ontologies.

### Core Components

- **`main.py`** — The transformation execution engine. Loads XMI files and applies transformation rules.
- **`transformation_rule.py`** — Base class for all transformation rules.
- **`transformation_ruleset.py`** — Manages and executes an ordered sequence of transformation rules.
- **`transformations.py`** — Core transformation logic and utilities.
- **`__init__.py`** — Package initialization; exports public API.
- **`__main__.py`** — CLI entry point for batch transformations.

### Architecture

The transformation system is built on three core concepts:

1. **Transformation Context** — Holds the XMI tree, source IRI, and RDF graph during processing
2. **Transformation Rules** — Individual rules that extract specific model elements
3. **Rule Sets** — Ordered collections of rules applied sequentially to a context

This architecture allows for composable, testable, and reusable transformation logic.

## Entry Points

### Main CLI (`main.py`)

The root-level `main.py` provides a unified command-line interface for:

- **Transformations**: Convert XMI files to RDF/OWL ontologies
- **Ablations**: Study the impact of specific transformation rules by removing them

Supports multiple output formats and rule selection.

### Batch Transformation (`python -m transformations`)

For batch processing entire directories or files using the transformation engine, use:

```bash
python -m transformations {XMI_FILE_PATH}
```

This delegates to the transformation engine in `transformations/main.py`.

### Invoking from Python

You can also invoke transformations programmatically from Python:

```python
from transformations import transform_xmi

graph = transform_xmi("path/to/xmi/file.xml")
print(graph.serialize(format="turtle"))
```

Explicit paper profiles can select or override decision-point strategies. Omitted
choices use the profile baseline:

```python
from transformations import TransformationConfig, transform_xmi

config = TransformationConfig(
        paper="jetlund",
        strategies={"abstract_class": "annotation", "inheritance": "direct_subclass"},
)
graph = transform_xmi("path/to/xmi/file.xml", config=config)
```

The command-line entry point accepts the same explicit choices:

```bash
python main.py input.xml --paper jetlund \
    --strategy abstract_class=annotation \
    --strategy inheritance=direct_subclass
```

Available profiles and strategies are validated when the configuration is
created. The original invocation without `--paper` or `config` remains the
backward-compatible transformation.

## Status

As of May 2026, the transformation software is at an early stage of development, with an MVP version expected by August 2026.

## License & Rights

This software is licensed for reuse under the conditions of the [Creative Commons BY 4.0 License](https://creativecommons.org/licenses/by/4.0/), a copy of the deed of which is contained in this repository in the LICENSE file.

The software in this repository is copyright as follows:

&copy; International Organization for Standardization, 2026

## Contact

This software is managed by the TC-211's [Advisory Group 6 Group for Ontology Maintenance (GOM)](https://committee.iso.org/sites/tc211/home/about/advisory-groups.html). Please contact that group using the details at:

* <https://github.com/ISO-TC211/GOM#contact>
