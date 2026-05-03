# NOTICE

Helios bundles its own first-party code under the LICENSE at the repo root.
This document acknowledges the third-party datasets the demo's seed pipeline
reads at runtime. **None of these datasets is committed to the repository.**
They live under the gitignored `test dataset/` tree on a developer's local
machine and the seed loader reads them in place.

The artifacts persisted into Cloudant by `backend/migrations/seed_demo.py`
are derivative metadata (parsed AST excerpts, structured findings, schema
diffs, hand-crafted ABEND dump fragments) rather than verbatim source
copies. Where a dataset's license requires attribution, this file provides
it. Where a license restricts redistribution, the seed pipeline avoids
producing derivative artifacts that would carry the source verbatim.

---

## 1. Rocket Software BankDemo

**Path in dataset tree:** `test dataset/helios_sample_dataset/01_BankDemo/`

**License:** Proprietary — Rocket Software EULA. The bundled `LICENSE.txt`
states the software may be used, modified, and distributed "solely for
internal demonstration purposes with other Rocket® products, and is
otherwise subject to the EULA at
https://www.rocketsoftware.com/company/trust/agreements".

**Attribution:** Copyright 2010 – 2025 Rocket Software, Inc. or its
affiliates. Originally Micro Focus BankDemo; transferred with the
acquisition.

**Helios usage:** Helios reads BankDemo COBOL/PL-I/JCL/copybook/DDL sources
at seed time, parses them with first-party parsers under
`backend/app/services/mainframe_parser/`, and persists structured AST
metadata into Cloudant. The seed pipeline never copies BankDemo source
files into the repository or into any artifact that would be committed.
Region YAMLs, schema diffs, and hand-crafted ABEND dump fragments under
`shared/sample-corpus/` are derivatives written by Helios authors after
inspection of the dataset; their content is not verbatim BankDemo source.

**Restriction:** Do not commit BankDemo source files, do not redistribute
them outside an authenticated Rocket licensee context, and do not use them
in production inference workloads. The dataset is for hackathon
demonstration only.

---

## 2. Open Mainframe Project — COBOL Programming Course

**Path in dataset tree:**
`test dataset/helios_sample_dataset/02_OMP_COBOL_Course/`

**License:** Creative Commons Attribution 4.0 International (CC-BY-4.0)
per the bundled `LICENSE` file. The upstream project (github.com/
openmainframeproject/cobol-programming-course) is documented as a mix of
CC-BY-4.0 for course materials and Apache 2.0 for code samples; the
snapshot in this dataset carries only the CC-BY-4.0 license file, so this
project treats the entire snapshot as CC-BY-4.0 for the conservative
case.

**Attribution:** © Open Mainframe Project / The Linux Foundation.
Course-material reuse requires the attribution above. Helios's seed
pipeline derives parser AST metadata from the lab JCL and COBOL files;
those artifacts in Cloudant carry an `attribution` field referencing the
Open Mainframe Project source.

**Helios usage:** The intermediate-level labs (`labs_intermediate/`) and
advanced labs (`labs_advanced/`) seed the `training_int` region's job
catalog and provide the standard `IGYWC` / `IGYWCL` / `IGYWCLG` cataloged
procedures. The `challenges_advanced/Debugging/` tree provides
`CBL0106J.jcl` and `CBL0106.cbl` — used as the "deliberately broken"
program for the ABEND Archaeologist demo's S0C7 ground-truth fixture.

---

## 3. cobol-check sample programs

**Path in dataset tree:**
`test dataset/helios_sample_dataset/03_cobol-check_samples/`

**License:** Apache License 2.0 per the bundled `LICENSE` file.

**Attribution:** © cobol-check contributors (github.com/openmainframeproject/cobol-check).

**Helios usage:** The parallel-variant copybooks under
`cobol/copy/Outrec/` (e.g., `COPY001.CBL` vs `COPY001-padded.CBL`,
`mixed003.CBL` vs `mixed003-padded.CBL`) are an intentional drift testbed.
Helios seeds these into `helios_copybook_artifacts` with explicit version
tags so the JJ-COPYBOOK-DRIFT-001 rule has positive fixtures grounded in
real (rather than fabricated) drift. Apache 2.0 obligations: this NOTICE
file carries the attribution; downstream redistribution would require the
LICENSE file alongside.

---

## License compatibility note

Helios's first-party code is licensed under the LICENSE at the repo root.
The three datasets above are read at runtime — not vendored. The Cloudant
artifacts produced by seeding are first-party derivatives whose
copyrightable expression is the parser's structured output (field names,
relationships) rather than verbatim text from the sources. Hand-crafted
ABEND dump fragments under `shared/sample-corpus/abend_examples/` are
authored by Helios contributors based on plausible failure modes of named
programs; they are not transcripts of dumps produced by running BankDemo.

If any of these datasets is replaced with a more permissively licensed
substitute later, this file is the single place to update.
