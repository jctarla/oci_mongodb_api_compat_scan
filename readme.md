# Oracle Database API for MongoDB compatibiliy scanner

`mongo_oci_compat_scan.py` scans source code for MongoDB features that are not compatible with **Oracle Database API for MongoDB on OCI**.

The scanner uses an embedded `oci_incompatible_list` built from items marked as `Support = No` in the [Oracle Database API for MongoDB compatibility reference](https://docs.oracle.com/en/database/oracle/mongodb-api/mgapi/support-mongodb-apis-operations-and-data-types-reference.html#GUID-0CEEF19F-8E07-4441-88D2-86351D884492]). It does not require internet access at runtime. It can print a terminal report and optionally save JSON, Markdown, or PDF outputs.

The scan is read-only for the target directory. The script reads source files from the directory you pass as `target_dir`, but it does not modify, delete, move, or rewrite any information inside that target directory. It only writes report files when you explicitly provide output options such as `--output-json`, `--output-markdown`, or `--output-pdf`.

## What It Detects

The script scans for unsupported MongoDB items in these categories:

- query operators
- aggregation stages
- aggregation expressions
- system variables
- MongoDB commands
- BSON types
- index types and index options

It also detects MongoDB driver references and classifies them as:

- `supported`: official MongoDB drivers
- `review`: wrappers, ODMs, or framework integrations that need compatibility review
- `incompatible`: packages that are not suitable as production MongoDB access drivers

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

Install dependencies with:

```bash
pip install -r requirements.txt
```

The current dependency is `markdown-pdf`, which is only required when using `--output-pdf`. The scanner's core terminal, JSON, and Markdown reports use Python standard library modules.

## Usage

Scan a target directory and print a terminal report:

```bash
./mongo_oci_compat_scan.py /path/to/source
```

Save a JSON report:

```bash
./mongo_oci_compat_scan.py /path/to/source --output-json report.json
```

Save a Markdown report:

```bash
./mongo_oci_compat_scan.py /path/to/source --output-markdown report.md
```

Save a PDF report:

```bash
./mongo_oci_compat_scan.py /path/to/source --output-pdf report.pdf
```

Scan the included sample application:

```bash
./mongo_oci_compat_scan.py sample_app --output-json sample_app/report.json
```

## Options

- `--output-json PATH`: write the full report as JSON
- `--output-markdown PATH`: write the full report as Markdown
- `--output-pdf PATH`: write the full report as PDF
- `--include-all-text-files`: scan any text-like file, not only known source extensions
- `--extra-extension EXT`: include an additional file extension, repeatable
- `--exclude-dir NAME`: exclude an additional directory name, repeatable

## Default Scan Behavior

By default, the scanner:

- recursively scans the target directory
- includes common source, config, and documentation extensions
- skips directories such as `.git`, `node_modules`, `vendor`, `dist`, `build`, `target`, virtual environments, and cache folders
- counts every textual occurrence of each unsupported item
- keeps the target directory read-only during scanning

Because detection is regex-based, findings should be reviewed before remediation. Comments, documentation, generated reports, and the scanner source itself can produce matches if they are inside the scanned target directory.

## Output Formats

The terminal, Markdown, and PDF reports include:

- summary counts
- incompatibilities grouped by file
- category totals
- MongoDB driver validation
- driver totals by status and package signature

The JSON report is intended for automation and includes structured `findings` and `driver_findings` arrays.

## Sample Application

The `sample_app` directory contains an Express application with intentional incompatible MongoDB usage. It is useful for validating scanner behavior and output generation.

See `sample_app/README.md` for details.


## Author

Joao Tarla

## Disclaimer

This script is provided as-is, without any warranty or guarantee. Use it at your own risk. The author is not responsible for any issues, losses, or damages that may result from using this script.

## License

This project is licensed under the Universal Permissive License (UPL), Version 1.0. See [LICENSE](LICENSE) for details.
