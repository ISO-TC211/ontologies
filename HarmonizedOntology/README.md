# ISO/TC-211 Harmonized Ontology

This directory contains the software for generating OWL/RDF ontologies from ISO/TC-211 Harmonized Model XMI files. Transformations are implemented as ordered rules, with optional paper or implementation profiles for decisions such as abstract classes, inheritance, and enumerations.

## Overview

The Harmonized Ontology project transforms ISO/TC-211 conceptual models (represented as XMI files) into Semantic Web ontologies (OWL/RDF). The software is organized into a `transformations/` library containing the core transformation engine, rules, and tests.

The project parses an XMI document into a transformation context and applies a ruleset to build and serialize an `rdflib.Graph`. The repository-level `main.py` is a compatibility wrapper around the package CLI, intended to connect with future ontology quality metrics.

The transformation has four related concepts:

- A **transformation step** performs one focused extraction or graph update, such as extracting UML classes or associations.
- A **transformation pipeline** is an ordered collection of steps. It controls which rules run and the order in which they update the transformation context and RDF graph.
- A **rule strategy** implements one modeling choice within a step, such as representing inheritance with direct `rdfs:subClassOf` statements or an OWL intersection.
- A **modeling profile** groups the strategies and alternatives associated with an implementation approach or publication. The default strategy is currently arbitrarily chosen. A profile is selected through `TransformationConfig` and individual strategy choices can be overridden.

## Quick Start

### Installation

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

### CLI

Both entrypoints accept the same arguments. The XMI path is positional and the serialized graph is written to standard output.

Run the repository entrypoint:
```bash
python main.py path/to/xmi/file.xml > output.ttl
```

The package entrypoint is currently equivalent:
```bash
python -m transformations path/to/xmi/file.xml > output.ttl
```

Select an RDF serialization format with `--format`:
```bash
python main.py path/to/xmi/file.xml --format json-ld > output.json
```

Run only selected rules with `--rules`:
```bash
python main.py path/to/xmi/file.xml \
    --rules BaseExtractPackages BaseExtractClasses
```

`--rules` is also the mechanism for ablation-style experiments: provide the rules to retain in the run. A list of rules and strategies are provided below. 

Select a profile and override one or more decision points with repeatable `--strategy` options:
```bash
python main.py path/to/xmi/file.xml \
    --paper jetlund \
    --strategy abstract_class=annotation \
    --strategy inheritance=direct_subclass
```

The available options are:

| Option | Meaning |
| --- | --- |
| `xmi_path` | Input XMI/XML file. The command fails if it does not exist. |
| `--rules RULE ...` | Optional names of rules to run. Without it, all default rules run. |
| `--format FORMAT` | RDFLib serialization format; defaults to `turtle`. |
| `--paper PROFILE` | Profile identifier, such as `iso` or `inspire`. |
| `--strategy DECISION_POINT=STRATEGY` | Override a profile default. May be supplied more than once. |

### Running Tests

Execute the test suite from the `HarmonizedOntology` directory:

```bash
pytest transformations/tests
```

## File Structure

```
HarmonizedOntology/
├── main.py                         # Repository CLI wrapper
├── requirements.txt                # Runtime and test dependencies
├── README.md                       # This documentation
├── tests/
│   └── test_transformations.py     # Unit, integration, and CLI smoke tests
└── transformations/
    ├── __init__.py                 # Public package exports
    ├── __main__.py                 # Package CLI and transform_xmi/load_xmi
    ├── config.py                   # Immutable profile configuration and validation
    ├── factory.py                  # ProfileAwareRulesetFactory and make_ruleset
    ├── profiles.py                 # ModelingProfile definitions and default strategies
    ├── rule.py                     # TransformationStep abstract class
    ├── ruleset.py                  # TransformationPipeline class
    ├── implementations/
    │   └── BaseTransformation.py   # DefaultTransformationPipeline
    └── strategies/
        ├── base.py                 # RuleStrategy interface
        ├── abstract_class.py
        ├── inheritance.py
        └── enumeration.py
```

## Transformation Model

### Context

`load_xmi()` returns a context containing the parsed XML tree, the source IRI, an RDFLib graph, and transformation metadata. Rules read and update this context. `transform_xmi()` creates the context, constructs `DefaultTransformationPipeline`, applies it, and returns the resulting `Graph`.

### Rules

A rule is a class derived from `TransformationStep`. It has a `transform(context)` method and may optionally implement `fit()` or `inverse_transform()`. Rules are stateless by default, and their name is the class name. The default rules, applied in this order, are:

1. `BaseAddSchemaDescriptionProperty` — registers `schema:description` as an OWL annotation property.
2. `BaseExtractPackages` — extracts model packages and their metadata.
3. `BaseExtractPackageHierarchy` — records package-parent relationships in context metadata.
4. `BaseExtractClasses` — extracts UML classes, labels, descriptions, and package membership.
5. `BaseExtractSubclassRelations` — converts UML generalizations to subclass relations using the configured inheritance strategy.
6. `BaseExtractAssociations` — extracts UML associations as RDF properties with domain and range.
7. `BaseExtractAttributes` — extracts UML attributes as RDF properties with domain and range.
8. `BaseExtractEnumerations` — applies the configured enumeration strategy to enumeration classes.

### Rulesets

`TransformationPipeline` is an ordered collection of `TransformationStep` instances. It supports `add_rule()`, `fit()`, `transform()`, `fit_transform()`, iteration, indexing, `len()`, and `select(names)`. `DefaultTransformationPipeline` is the default implementation and can be created with `rule_names` and an optional `TransformationConfig`.

Selecting a subset from Python:

```python
from transformations import DefaultTransformationPipeline

ruleset = DefaultTransformationPipeline().select([
    "BaseExtractPackages",
    "BaseExtractClasses",
])
```

### Strategies

A strategy is a `RuleStrategy` implementation that encodes one modeling choice. A `TransformationConfig` validates the selected profile and fills omitted decision points with that profile's default. 

| Decision point | Strategies | Effect |
| --- | --- | --- |
| `abstract_class` | `annotation`, `disjoint_union` | Mark abstract classes with `iso19150:isAbstract`, or encode their children with `owl:disjointUnionOf`. |
| `inheritance` | `direct_subclass`, `intersection` | Emit direct `rdfs:subClassOf` triples, or use an OWL class intersection for multiple superclasses. |
| `enumeration` | `iso`, `inspire` | Encode values as an OWL datatype range, or use INSPIRE SKOS concepts for non-self-describing values. |

Supported profiles and their default strategies:

| Profile | Defaults |
| --- | --- |
| `jetlund` | `abstract_class=annotation`, `inheritance=direct_subclass`, `enumeration=iso` |
| `zedlitz_luttenberger_2012` | `abstract_class=disjoint_union` |
| `hajjamy_2016` | `inheritance=intersection` |
| `iso` | `abstract_class=annotation`, `inheritance=direct_subclass`, `enumeration=iso` |
| `inspire` | `inheritance=direct_subclass`, `enumeration=inspire` |

Configuration is immutable and exposes a deterministic `configuration_id`:

```python
from transformations import TransformationConfig

config = TransformationConfig(
    "inspire",
    {"enumeration": "inspire"},
)
```

Invalid profile, decision-point, or strategy names raise `ConfigurationError`.

## Entry Points

### `python main.py`

Compatibility wrapper that imports and calls `transformations.__main__.main()`. Made for future integration with a quality metrics package.

### `python -m transformations`

Canonical package entrypoint. It parses CLI arguments, creates an optional `TransformationConfig`, runs `transform_xmi()`, and prints the serialized graph.

## Tests

Run the test suite from this directory:

```bash
pytest
```

The tests cover rule and ruleset composition, repository XMI transformation, CLI and package import smoke tests, configuration validation, and profile-specific RDF output.

## Status

As of May 2026, the transformation software is at an early stage of development, with an MVP version expected by August 2026.

## License & Rights

This software is licensed for reuse under the conditions of the [Creative Commons BY 4.0 License](https://creativecommons.org/licenses/by/4.0/), a copy of the deed of which is contained in this repository in the LICENSE file.

The software in this repository is copyright as follows:

&copy; International Organization for Standardization, 2026

## Contact

This software is managed by the TC-211's [Advisory Group 6 Group for Ontology Maintenance (GOM)](https://committee.iso.org/sites/tc211/home/about/advisory-groups.html). Please contact that group using the details at:

* <https://github.com/ISO-TC211/GOM#contact>
