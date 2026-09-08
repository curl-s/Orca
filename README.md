
<p align="center">
    <img width="25%" height="25%" alt="logo" src="src/image-removebg-preview.png" />
</p>

<h1 align="center">Orca</h1>

> **Explore how Orbis OS evolves.**

Orca is a firmware analysis and evolution platform designed for comparing, tracking, and understanding changes across **Orbis OS firmware versions**.

Rather than treating a firmware comparison as an isolated diff between two binaries, Orca aims to build a broader picture: **how code, functions, structures, and behaviour evolve across an entire firmware history.**

## Why Orca?

Traditional binary diffing tools are built around a simple question:

> *What changed between binary A and binary B?*

Orca expands that question:

> *When did this change first appear?*
> *Which firmware introduced it?*
> *Did it remain unchanged afterwards?*
> *Was it modified again?*
> *How does this component evolve across the entire firmware timeline?*

By analysing multiple firmware versions together, Orca is designed to turn individual firmware comparisons into a searchable history of software evolution.

## Features

### Multi-Firmware Analysis

Compare more than two firmware versions simultaneously.

Instead of manually performing:

```text
Firmware A → Firmware B
Firmware B → Firmware C
Firmware C → Firmware D
```

Orca can model changes across an entire firmware timeline.

```text
FW 1 ─────┐
FW 2 ─────┤
FW 3 ─────┼──► Evolution Analysis
FW 4 ─────┤
FW 5 ─────┘
```

### Firmware Evolution Tracking

Track functions and components across multiple firmware versions.

Identify:

* When a function first appears
* When it disappears
* When it changes
* How significantly it changed
* Whether changes persist across later versions
* Relationships between functions across firmware generations

### Change Classification

Orca aims to classify differences instead of simply reporting that two pieces of code are different.

Potential change categories include:

* Added
* Removed
* Modified
* Renamed
* Moved
* Split
* Merged
* Unchanged

### Orbis Metadata

Build structured metadata around analysed firmware components.

This can include information such as:

* Firmware version
* Binary/module
* Function identity
* Cross-firmware relationships
* Change history
* Analysis notes
* User annotations

### Searchable Analysis Database

Store analysis results in a structured database rather than keeping comparisons isolated inside individual projects.

This makes it possible to search across firmware versions and ask questions such as:

> Show every firmware where this function changed.

> Find functions introduced between two firmware generations.

> Show all components modified during a specific firmware update.

### Cross-Firmware Relationships

Orca is designed to maintain relationships between components across firmware versions.

```text
Function X
    │
    ├── FW 1.00
    │
    ├── FW 2.00 ── Modified
    │
    ├── FW 3.00 ── Modified
    │
    └── FW 4.00 ── Unchanged
```

This makes it easier to follow the evolution of a component instead of repeatedly rediscovering it during individual binary comparisons.

### Annotations

Attach notes and research context directly to analysed components.

Annotations can help document:

* Reverse engineering findings
* Function behaviour
* Interesting changes
* Research hypotheses
* Cross-references
* Known symbols

## Vision

Orca is not intended to be just another binary diffing interface.

The goal is to create a system that understands firmware as a **continuously evolving ecosystem**.

A normal diff shows you:

```text
A ≠ B
```

Orca aims to show you:

```text
A → B → C → D → E

What changed?
When did it change?
How did it evolve?
Did the change persist?
What else changed with it?
```

## Roadmap

### Phase 1: Two-Firmware Analysis

* Import firmware binaries
* Compare two firmware versions
* Function matching
* Basic change detection
* Function-level metadata

### Phase 2: Multi-Firmware Support

* Analyse multiple firmware versions together
* Build firmware evolution histories
* Track functions across versions
* Detect persistent and temporary changes

### Phase 3: Orbis Knowledge Layer

* Structured metadata
* Searchable analysis database
* Cross-firmware references
* Change classification
* Annotations

### Phase 4: Advanced Evolution Analysis

* Firmware evolution visualisation
* Change timelines
* Function history graphs
* Dependency tracking
* Large-scale firmware analysis

## Example

Instead of seeing several disconnected comparisons:

```text
FW 1.00 ↔ FW 2.00

FW 2.00 ↔ FW 3.00

FW 3.00 ↔ FW 4.00
```

Orca aims to produce a connected history:

```text
Function: example_function

FW 1.00  ████████████████  Introduced
FW 2.00  ████████████████  Unchanged
FW 3.00  ███████████████░  Modified
FW 4.00  ███████████████░  Unchanged
FW 5.00  █████████████████ New modification
```

## Status

**Early development / research**

Orca is currently an experimental project exploring new approaches to firmware comparison and long-term evolution analysis.

## Name

**Orca** draws inspiration from the Orbis ecosystem while representing something capable of navigating and analysing a large, complex environment.

The project focuses on looking beneath individual firmware versions and understanding the larger system that connects them.

---

> **Orca — Beyond binary diffing. Understand firmware evolution.**
