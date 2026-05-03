# Glossary — Mainframe Terms for Cloud-Native Readers

Most software industry judges have never touched z/OS. This glossary translates the mainframe vocabulary in Helios docs and demo into terms a cloud-native developer recognizes. Read top-to-bottom for orientation, or jump to a term.

A non-Z judge who reads this file before the demo will understand twice as much of what they see. That converts to scoring.

---

## The 30-second mental model

A z/OS mainframe is a single very large machine running thousands of jobs in parallel. The unit of work is a **job** described by **JCL** (a declarative manifest, like a Kubernetes Pod spec). Jobs invoke **programs** (mostly written in **COBOL**) which read and write to **datasets** (files on attached storage) and to **DB2** (the on-platform relational database). Programs share data structures via **copybooks** (header files) and call into shared subroutines via **PROCs** (think Helm chart partials). All of this runs inside a **region** — an environment, like dev/staging/prod, but with much more configuration drift between regions than a typical cloud setup.

If you understand that paragraph, you understand 80% of what Helios is automating.

---

## Term-by-term

### ABEND
*Abnormal END.* The mainframe word for a program crash. ABENDs come with a **completion code** (e.g., `S0C7`, `U4038`) that classifies the failure. Cloud equivalent: a process exit code combined with a stack trace.

### Bind / BIND
The act of compiling a SQL package against a specific DB2 catalog. Equivalent to running prepared statements once and storing the execution plan. Bind parameters (`ACTION`, `RETAIN`, `ISOLATION`, etc.) determine how the package behaves at runtime. Mismatched binds across regions are a top source of promotion failures.

### CEEDUMP
Diagnostic file produced by the COBOL runtime (Language Environment) when a program ABENDs. Contains the call stack, register state, and storage near the failure. Equivalent to a core dump.

### Copybook
A reusable file that defines a data structure, included by COBOL programs at compile time. Equivalent to a C/C++ header or a Python `dataclass` import. The same copybook can have multiple versions across the SYSLIB chain — that drift is one of the bugs JJSCAN+ catches.

### DB2
IBM's relational database that runs on z/OS. Roughly the mainframe analog of PostgreSQL, but tightly coupled to the operating system. Has subsystems (instances), plans, packages, and collections — all of which differ across regions.

### DB2 plan / package / collection
- **Plan** = the executable form of a SQL program, bound at deploy time.
- **Package** = a sub-unit of a plan; one package per program.
- **Collection** = a namespace grouping packages, scoped per region. `CUSTPKG.INT2` and `CUSTPKG.INT3` are the same package in two collections.

If a JCL references `CUSTPKG.INT2` but is being run in `int3`, you get `SQLCODE -805` ("DBRM not found"). One of JJSCAN+'s rules.

### DD (Data Definition statement)
A line in JCL that declares an input or output dataset for a program. Roughly: a Pod spec's `volumeMount` plus environment variable, combined.

### Endevor
A change-management product from Broadcom. Where most banks store their mainframe source code today. Equivalent to git + a merge-approval workflow + a deployment manifest, all coupled together. Helios coexists with Endevor; it does not replace it.

### GDG (Generation Data Group)
A naming convention for time-versioned datasets. `CUST.MASTER(0)` is "current," `CUST.MASTER(-1)` is "previous." Cloud equivalent: object versioning in S3 with semantic version aliases.

### Granite Code
IBM's family of code-specialized LLMs. Used by Helios for COBOL summarization and ABEND root-cause explanation. Runs on watsonx.ai.

### HLQ (High-Level Qualifier)
The first part of a dataset name, by convention the owning team or environment. `CUST.INT2.LOAD` has HLQ `CUST.INT2`. Region Atlas's main job is keeping HLQs straight across promotions.

### IDCAMS
The mainframe utility for dataset management — define, delete, copy, rename, REPRO (replicate). Used by Helios's backup generator for VSAM cluster backups.

### IEC141I, IEF272I, IEC031I, etc.
System message codes that appear in SYSLOG when something goes wrong with allocation, I/O, or termination. Each prefix maps to a subsystem; ABEND Archaeologist's pattern library knows them all.

### IMAGE COPY
A DB2 backup operation that snapshots a tablespace to a dataset. The Helios backup generator pairs an UNLOAD with an IMAGE COPY whenever a JCL touches a protected DB2 table.

### ISPF
The standard z/OS terminal UI. Where mainframe developers spend most of their day. Equivalent to a TUI shell that has eaten 50 years of features. Helios runs alongside ISPF, not inside it.

### JCL (Job Control Language)
The declarative manifest that tells z/OS what to run, with what inputs, with what resources. The closest cloud analog is a Kubernetes manifest combined with a shell script. JCL is **the** thing Helios primarily operates on.

### JES2 / JES3
The job entry subsystem — the scheduler that turns JCL into running jobs. Equivalent to the Kubernetes scheduler. The SMF feed (see below) is JES's event stream.

### JJSCAN
A real IBM utility (full name: jobsCAN) that statically analyzes a JCL deck and reports what it calls, what datasets it touches, etc. Helios's **JJSCAN+** is a deeper analyzer that also detects logical defects (missing members, version drift, plan mismatches).

### Job / Step
A **job** is one execution unit, declared by one JCL deck. A job has one or more **steps**, each invoking one program. Equivalent to a Pod with multiple containers run sequentially.

### LPAR (Logical Partition)
A virtualized slice of a mainframe. Equivalent to a VM. A z/OS shop typically runs 4–8 LPARs hosting their dev, int, prod regions.

### Plan / Package
See *DB2 plan / package / collection*.

### PROC (Procedure)
A reusable JCL fragment, like a Helm partial or an Ansible role. Invoked from a job with parameter substitution. PROCs themselves can override the calling JCL's DDs, which is where `proc_override_conflict` defects come from.

### PROCLIB
The dataset (directory) where PROCs live. Each region has its own. JJSCAN+ resolves PROC references through the region's PROCLIB concatenation.

### RACF (Resource Access Control Facility)
The IBM-native auth system for z/OS. Groups, profiles, permissions on every resource. Equivalent to IAM. Region profiles track which RACF groups own which resources.

### Region
The mainframe word for environment. `int1`, `int2`, `int3`, `prod` are regions. Unlike cloud environments, regions tend to drift considerably — different DB2 subsystems, different RACF groups, different schedulers, different naming conventions. This drift is the central thing Helios's Region Atlas captures.

### Restart
A JCL feature that lets a job resume from a particular step on rerun. Useful but error-prone — restarting after a step that already wrote a permanent dataset will conflict with that dataset's `DISP=NEW`. JJSCAN+ has a rule for this (`restart_step_incompatibility`, parked for Phase 2).

### REXX
A scripting language often used on z/OS for ops automation. Like the mainframe's bash + Python. Helios doesn't generate REXX but reads it for context.

### SMF (System Management Facilities)
The mainframe's metric and event stream. Records every job step start, end, ABEND, dataset open, etc. Helios's Learning Loop subscribes to SMF (or a synthetic stand-in) to detect when promotions actually succeed or fail in production. Equivalent to OpenTelemetry traces + audit log combined.

### SQLCODE
The DB2 error code returned to a program after a failed SQL operation. Negative codes are errors (`-805`, `-811`, `-904`, `-922` are the ones ABEND Archaeologist's pattern library handles). Positive codes are warnings.

### STEPLIB / JOBLIB
A DD statement that prepends directories to the program-resolution search path for a single step or for the whole job. Equivalent to setting `LD_LIBRARY_PATH` in the cloud world. Region Atlas substitutes STEPLIB DSNs during promotion because each region has its own load library HLQ.

### S0C4, S0C7, S322, S806, S813, U4038
The most common ABEND codes:
- **S0C4** — protection exception (bad pointer / out-of-bounds memory access)
- **S0C7** — data exception (numeric op on non-numeric data, the canonical COBOL bug)
- **S322** — CPU time limit exceeded
- **S806** — module not found in load library chain
- **S813** — wrong volume mounted (rare in modern shops)
- **U4038** — Language Environment user ABEND (the COBOL runtime gave up; usually wraps something else)

ABEND Archaeologist's pattern library has runbook entries for all of these.

### SYSLOG
The mainframe's master event log. Where every job's lifecycle messages appear. Equivalent to systemd journal scaled to thousands of jobs. ABEND Archaeologist parses SYSLOG paste-ins.

### SYSLIB
The DD that points at the include search path for copybooks at compile time. Concatenation order matters — the same copybook name can resolve to different physical members depending on which dataset comes first. Hence "copybook drift."

### Subsystem
A persistent service running on z/OS. DB2 is a subsystem. CICS is a subsystem. MQ is a subsystem. Each has an ID (`DBI1`, `DBI2`, ...) that JCL must reference. Region differences in subsystem IDs are the most common cause of promotion failures.

### UNLOAD
A DB2 utility that exports a tablespace to a flat file. Helios's backup generator pairs an UNLOAD with an IMAGE COPY for every protected DB2 resource touched by a promoted JCL.

### VSAM (Virtual Storage Access Method)
The non-relational structured-file system on z/OS. Similar to indexed files. Many older COBOL programs use VSAM datasets; Helios's backup generator uses `IDCAMS REPRO` to back these up.

### VOLSER (Volume Serial)
A 6-character identifier for a DASD or tape volume. Region profiles track VOLSER conventions because some shops segregate environments by volume.

### watsonx.ai
IBM's hosted inference platform. Helios calls it for Granite Code 8B (COBOL summarization) and Granite-3-8B-Instruct (general chat). Equivalent to a managed LLM endpoint.

### watsonx Orchestrate
IBM's multi-agent runtime. Helios uses it to coordinate the four agents that map to its four feature modules. Equivalent to a workflow orchestrator with LLM-in-the-loop steps.

### Zowe
An open-source CLI / SDK for talking to z/OS from outside it. The bridge between modern dev tools and the mainframe. Helios's backend uses Zowe's APIs (where available) for read-only operations on the synthetic shop's emulated datasets.

---

## Cloud→mainframe translation table

| Cloud term | Mainframe term |
|---|---|
| Pod manifest / Helm chart | JCL |
| Helm partial / Ansible role | PROC |
| Header file / dataclass | Copybook |
| Environment variable | Symbolic parameter |
| Environment (dev/prod) | Region |
| Container image / load library | Load module |
| Namespace | Region + RACF group |
| IAM | RACF |
| systemd journal | SYSLOG |
| OpenTelemetry traces | SMF |
| Process exit code | ABEND completion code |
| Core dump | CEEDUMP / SVC dump |
| `LD_LIBRARY_PATH` | STEPLIB / JOBLIB |
| Object versioning | GDG |
| Prepared statement cache | DB2 plan/package |
| S3 bucket | DASD volume |
| Job scheduler / cron | JES2 / JES3 |
| Database snapshot | IMAGE COPY |
| File replication | IDCAMS REPRO |
| Audit log | SMF + (today: nothing structured) |
| Compliance evidence bundle | (today: a mess of grep output) |

---

## Why this glossary belongs in the repo

1. **For judges.** Most reviewers will be cloud-native. This file is the on-ramp.
2. **For onboarding.** When a new contributor joins post-hackathon, this is the file we hand them first.
3. **For the README.** A single link from the README ("New to mainframes? Read this first.") demonstrates that Helios is built for both audiences.

If a judge clicks one link from the README, this should be one of the top three candidates.
