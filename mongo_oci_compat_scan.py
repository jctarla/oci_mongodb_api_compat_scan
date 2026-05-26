#!/usr/bin/env python3
"""
Scan source code for MongoDB features that are incompatible with OCI Oracle Database API for MongoDB.

This script uses a hardcoded list of unsupported items (no internet access required).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from typing import Dict, List, Sequence, Set, Tuple

# Hardcoded list built from Oracle compatibility references.
FALLBACK_UNSUPPORTED_ITEMS: Dict[str, List[str]] = {
    "query_operators": [
        "$box",
        "$center",
        "$centerSphere",
        "$expr",
        "$jsonSchema",
        "$meta",
        "$polygon",
        "$slice",
        "$uniqueDocs",
        "$where",
    ],
    "aggregation_stages": [
        "$bucketAuto",
        "$currentOp",
        "$geoNear",
        "$graphLookup",
        "$listLocalSessions",
        "$listSessions",
        "$planCacheStats",
        "$redact",
        "$setWindowFields",
    ],
    "aggregation_expressions": [
        "$accumulator",
        "$anyElementFalse",
        "$bottomN",
        "$dateAdd",
        "$dateDiff",
        "$dateSubtract",
        "$dateTrunc",
        "$firstN",
        "$function",
        "$getField",
        "$indexOfBytes",
        "$lastN",
        "$maxN",
        "$meta",
        "$regexFind",
        "$regexFindAll",
        "$regexMatch",
        "$replaceAll",
        "$sampleRate",
        "$setEquals",
        "$setIsSubset",
        "$strLenBytes",
        "$substrBytes",
        "$toDecimal",
        "$topN",
    ],
    "system_variables": [
        "$$DESCEND",
        "$$KEEP",
        "$$PRUNE",
        "$$REMOVE",
    ],
    "commands": [
        "abortReshardCollection",
        "addShard",
        "addShardZone",
        "balancerCollectionStatus",
        "balancerStart",
        "balancerStatus",
        "balancerStop",
        "checkShardingIndex",
        "clearJumboFlag",
        "cleanupOrphaned",
        "cleanupReshardCollection",
        "cloneCollectionAsCapped",
        "commitReshardCollection",
        "connPoolStats",
        "convertToCapped",
        "createRole",
        "createUser",
        "currentOp",
        "dbHash",
        "dropAllRolesFromDatabase",
        "dropAllUsersFromDatabase",
        "dropRole",
        "dropUser",
        "enableSharding",
        "features",
        "filemd5",
        "flushRouterConfig",
        "getShardMap",
        "getShardVersion",
        "getPrevError",
        "grantRolesToRole",
        "grantRolesToUser",
        "isdbGrid",
        "killOp",
        "listShards",
        "mapReduce",
        "medianKey",
        "mergeChunks",
        "moveChunk",
        "movePrimary",
        "parallelCollectionScan",
        "profiler",
        "refineCollectionShardKey",
        "removeShard",
        "removeShardFromZone",
        "reshardCollection",
        "revokePrivilegesFromRole",
        "revokeRolesFromUser",
        "rolesInfo",
        "setAllowMigrations",
        "setShardVersion",
        "shardCollection",
        "shardingState",
        "split",
        "splitVector",
        "top",
        "unsetSharding",
        "updateRole",
        "updateUser",
        "updateZoneKeyRange",
        "userInfo",
    ],
    "bson_types": [
        "dbPointer",
        "javascript",
        "javascriptWithScope",
        "maxKey",
        "minKey",
        "regex",
        "symbol",
        "timestamp",
        "undefined",
    ],
    "index_types": [
        "2d",
        "2dsphere",
        "hashed",
    ],
    "index_options": [
        "collation",
        "hidden",
        "partialFilterExpression",
        "storageEngine",
    ],
}

DEFAULT_INCLUDE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".scala",
    ".rs",
    ".swift",
    ".m",
    ".mm",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".xml",
    ".properties",
    ".env",
    ".txt",
    ".md",
    ".sh",
    ".zsh",
}

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "coverage",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    ".DS_Store",
}


@dataclass(frozen=True)
class UnsupportedItem:
    category: str
    value: str


@dataclass(frozen=True)
class DriverSignature:
    name: str
    status: str
    notes: str
    regex: str


# status meanings:
# - supported: official MongoDB driver package
# - review: wrapper/ODM/framework that still depends on a driver and needs compatibility review
# - incompatible: not suitable as production MongoDB access driver
DRIVER_SIGNATURES: List[DriverSignature] = [
    DriverSignature("node_mongodb", "supported", "Node.js official MongoDB driver", r'["\']mongodb["\']'),
    DriverSignature("python_pymongo", "supported", "Python official MongoDB driver", r"(?im)^\s*pymongo([<>=!~].*)?$"),
    DriverSignature("go_mongo_driver", "supported", "Go official MongoDB driver", r"go\.mongodb\.org/mongo-driver"),
    DriverSignature("java_mongodb_driver", "supported", "Java official MongoDB driver", r"org\.mongodb:mongodb-driver"),
    DriverSignature("dotnet_mongodb_driver", "supported", ".NET official MongoDB driver", r"MongoDB\.Driver"),
    DriverSignature("php_mongodb", "supported", "PHP MongoDB driver/library", r"mongodb/mongodb"),
    DriverSignature("ruby_mongo", "supported", "Ruby official MongoDB driver", r"(?im)^\s*gem\s+['\"]mongo['\"]"),
    DriverSignature("rust_mongodb", "supported", "Rust MongoDB driver crate", r'(?im)^\s*mongodb\s*=\s*["\']'),
    DriverSignature("python_motor", "review", "Async wrapper over PyMongo", r"(?im)^\s*motor([<>=!~].*)?$"),
    DriverSignature("node_mongoose", "review", "ODM on top of MongoDB driver", r'["\']mongoose["\']'),
    DriverSignature("python_mongoengine", "review", "ODM wrapper on top of PyMongo", r"(?im)^\s*mongoengine([<>=!~].*)?$"),
    DriverSignature("java_spring_data_mongodb", "review", "Framework abstraction for MongoDB", r"spring-boot-starter-data-mongodb"),
    DriverSignature("ruby_mongoid", "review", "ODM on top of Ruby Mongo driver", r"(?im)^\s*gem\s+['\"]mongoid['\"]"),
    DriverSignature("python_mongomock", "incompatible", "Mock driver (testing only)", r"(?im)^\s*mongomock([<>=!~].*)?$"),
]


def load_unsupported_items() -> Tuple[List[UnsupportedItem], str]:
    out: List[UnsupportedItem] = []
    for category, values in FALLBACK_UNSUPPORTED_ITEMS.items():
        for value in values:
            out.append(UnsupportedItem(category=category, value=value))
    return sorted(out, key=lambda x: (x.category, x.value.lower())), "oci_incompatible_list"


def should_scan_file(path: str, include_extensions: Set[str], include_all_text_files: bool) -> bool:
    name = os.path.basename(path)
    _, ext = os.path.splitext(name)
    if ext.lower() in include_extensions:
        return True

    if include_all_text_files:
        try:
            with open(path, "rb") as fh:
                chunk = fh.read(4096)
            if b"\x00" in chunk:
                return False
            return True
        except OSError:
            return False

    return False


def iter_source_files(root_dir: str, exclude_dirs: Set[str], include_extensions: Set[str], include_all_text_files: bool):
    for current_root, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for filename in filenames:
            path = os.path.join(current_root, filename)
            if should_scan_file(path, include_extensions, include_all_text_files):
                yield path


def report_path(path: str, root_dir: str) -> str:
    relative_path = os.path.relpath(path, root_dir)
    return relative_path.replace(os.sep, "/")


def build_bson_type_pattern(value: str) -> re.Pattern[str]:
    escaped_value = re.escape(value)
    enum_name = re.sub(r"(?<!^)(?=[A-Z])", "_", value).upper()
    enum_aliases = {enum_name}
    if value == "regex":
        enum_aliases.add("REGULAR_EXPRESSION")
    enum_pattern = "|".join(sorted(re.escape(alias) for alias in enum_aliases))

    return re.compile(
        rf"""
        (?:
            (?:["']?(?:\$type|bsonType)["']?\s*[:=]\s*["']{escaped_value}["'])
            |
            (?:\bBsonType\.({enum_pattern})\b)
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )


def build_command_pattern(value: str) -> re.Pattern[str]:
    escaped_value = re.escape(value)
    return re.compile(
        rf"""
        (?:
            \b(?:db\.)?(?:command|runCommand|adminCommand)\s*\(\s*\{{\s*["']?{escaped_value}["']?\s*:
            |
            \{{\s*["']?{escaped_value}["']?\s*:\s*[^}}\n]+}}
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )


def build_patterns(items: Sequence[UnsupportedItem]) -> Dict[UnsupportedItem, re.Pattern[str]]:
    patterns: Dict[UnsupportedItem, re.Pattern[str]] = {}
    for item in items:
        if item.category == "bson_types":
            patterns[item] = build_bson_type_pattern(item.value)
            continue

        if item.category == "commands":
            patterns[item] = build_command_pattern(item.value)
            continue

        escaped = re.escape(item.value)
        if item.value.startswith("$"):
            pattern = re.compile(rf"(?<!\w){escaped}(?!\w)")
        else:
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])")
        patterns[item] = pattern
    return patterns


def build_driver_patterns(signatures: Sequence[DriverSignature]) -> Dict[DriverSignature, re.Pattern[str]]:
    patterns: Dict[DriverSignature, re.Pattern[str]] = {}
    for signature in signatures:
        patterns[signature] = re.compile(signature.regex)
    return patterns


def scan_codebase(
    root_dir: str,
    unsupported_items: Sequence[UnsupportedItem],
    exclude_dirs: Set[str],
    include_extensions: Set[str],
    include_all_text_files: bool,
) -> Tuple[Dict[str, Dict[UnsupportedItem, int]], Dict[str, Dict[DriverSignature, int]], int]:
    patterns = build_patterns(unsupported_items)
    driver_patterns = build_driver_patterns(DRIVER_SIGNATURES)
    findings: Dict[str, Dict[UnsupportedItem, int]] = {}
    driver_findings: Dict[str, Dict[DriverSignature, int]] = {}
    files_scanned = 0

    for path in iter_source_files(root_dir, exclude_dirs, include_extensions, include_all_text_files):
        files_scanned += 1
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except OSError:
            continue

        file_hits: Dict[UnsupportedItem, int] = {}
        for item, pattern in patterns.items():
            count = len(pattern.findall(content))
            if count > 0:
                file_hits[item] = count

        if file_hits:
            findings[report_path(path, root_dir)] = file_hits

        file_driver_hits: Dict[DriverSignature, int] = {}
        for signature, pattern in driver_patterns.items():
            count = len(pattern.findall(content))
            if count > 0:
                file_driver_hits[signature] = count
        if file_driver_hits:
            driver_findings[report_path(path, root_dir)] = file_driver_hits

    return findings, driver_findings, files_scanned


def print_human_report(
    findings: Dict[str, Dict[UnsupportedItem, int]],
    driver_findings: Dict[str, Dict[DriverSignature, int]],
    files_scanned: int,
    total_items_considered: int,
    source_label: str,
):
    print("=== OCI Mongo API Compatibility Scan Report ===")
    print(f"Unsupported item source: {source_label}")
    print(f"Files scanned: {files_scanned}")
    print(f"Unsupported items considered: {total_items_considered}")
    print(f"Files with incompatibilities: {len(findings)}")
    print()

    if not findings:
        print("No incompatible usage found.")
        return

    total_hits = 0
    category_totals: Dict[str, int] = {}

    for path in sorted(findings.keys()):
        hits = findings[path]
        file_total = sum(hits.values())
        total_hits += file_total
        print(f"- File: {path}")
        print(f"  Total incompatibilities in file: {file_total}")
        for item in sorted(hits.keys(), key=lambda x: (x.category, x.value.lower())):
            count = hits[item]
            category_totals[item.category] = category_totals.get(item.category, 0) + count
            print(f"  - [{item.category}] {item.value}: {count}")
        print()

    print(f"Total incompatibility hits: {total_hits}")
    print("Category totals:")
    for category in sorted(category_totals.keys()):
        print(f"- {category}: {category_totals[category]}")

    print()
    print("=== Driver Validation ===")
    print(f"Files with MongoDB driver references: {len(driver_findings)}")
    if not driver_findings:
        print("No MongoDB driver references found.")
        return

    status_totals: Dict[str, int] = {}
    driver_totals: Dict[str, int] = {}
    for path in sorted(driver_findings.keys()):
        hits = driver_findings[path]
        file_total = sum(hits.values())
        print(f"- File: {path}")
        print(f"  Total driver references in file: {file_total}")
        for signature in sorted(hits.keys(), key=lambda x: (x.status, x.name)):
            count = hits[signature]
            status_totals[signature.status] = status_totals.get(signature.status, 0) + count
            driver_totals[signature.name] = driver_totals.get(signature.name, 0) + count
            print(f"  - [{signature.status}] {signature.name}: {count} ({signature.notes})")
        print()

    print("Driver status totals:")
    for status in sorted(status_totals.keys()):
        print(f"- {status}: {status_totals[status]}")

    print("Driver totals:")
    for driver in sorted(driver_totals.keys()):
        print(f"- {driver}: {driver_totals[driver]}")


def save_json_report(
    output_json: str,
    findings: Dict[str, Dict[UnsupportedItem, int]],
    driver_findings: Dict[str, Dict[DriverSignature, int]],
    files_scanned: int,
    total_items_considered: int,
    source_label: str,
):
    payload = {
        "source": source_label,
        "files_scanned": files_scanned,
        "unsupported_items_considered": total_items_considered,
        "files_with_incompatibilities": len(findings),
        "files_with_driver_references": len(driver_findings),
        "findings": [],
        "driver_findings": [],
    }

    for path in sorted(findings.keys()):
        hits = findings[path]
        payload["findings"].append(
            {
                "file": path,
                "total_hits": sum(hits.values()),
                "items": [
                    {"category": item.category, "item": item.value, "count": count}
                    for item, count in sorted(hits.items(), key=lambda x: (x[0].category, x[0].value.lower()))
                ],
            }
        )

    for path in sorted(driver_findings.keys()):
        hits = driver_findings[path]
        payload["driver_findings"].append(
            {
                "file": path,
                "total_hits": sum(hits.values()),
                "drivers": [
                    {
                        "name": signature.name,
                        "status": signature.status,
                        "notes": signature.notes,
                        "count": count,
                    }
                    for signature, count in sorted(hits.items(), key=lambda x: (x[0].status, x[0].name))
                ],
            }
        )

    with open(output_json, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def build_markdown_report_lines(
    findings: Dict[str, Dict[UnsupportedItem, int]],
    driver_findings: Dict[str, Dict[DriverSignature, int]],
    files_scanned: int,
    total_items_considered: int,
    source_label: str,
) -> List[str]:
    total_hits = 0
    category_totals: Dict[str, int] = {}
    for hits in findings.values():
        for item, count in hits.items():
            total_hits += count
            category_totals[item.category] = category_totals.get(item.category, 0) + count

    driver_status_totals: Dict[str, int] = {}
    driver_totals: Dict[str, int] = {}
    for hits in driver_findings.values():
        for signature, count in hits.items():
            driver_status_totals[signature.status] = driver_status_totals.get(signature.status, 0) + count
            driver_totals[signature.name] = driver_totals.get(signature.name, 0) + count

    lines: List[str] = []
    lines.append("# OCI Mongo API Compatibility Scan Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Unsupported item source: `{source_label}`")
    lines.append(f"- Files scanned: `{files_scanned}`")
    lines.append(f"- Unsupported items considered: `{total_items_considered}`")
    lines.append(f"- Files with incompatibilities: `{len(findings)}`")
    lines.append(f"- Total incompatibility hits: `{total_hits}`")
    lines.append(f"- Files with MongoDB driver references: `{len(driver_findings)}`")
    lines.append("")

    lines.append("## Incompatibilities by File")
    lines.append("")
    if not findings:
        lines.append("No incompatible usage found.")
        lines.append("")
    else:
        for path in sorted(findings.keys()):
            hits = findings[path]
            lines.append(f"### {path}")
            lines.append("")
            lines.append(f"- Total incompatibilities in file: `{sum(hits.values())}`")
            lines.append("")
            lines.append("| Category | Item | Count |")
            lines.append("|---|---|---:|")
            for item in sorted(hits.keys(), key=lambda x: (x.category, x.value.lower())):
                lines.append(f"| `{item.category}` | `{item.value}` | {hits[item]} |")
            lines.append("")

    lines.append("## Incompatibility Category Totals")
    lines.append("")
    if not category_totals:
        lines.append("No category totals to report.")
        lines.append("")
    else:
        lines.append("| Category | Count |")
        lines.append("|---|---:|")
        for category in sorted(category_totals.keys()):
            lines.append(f"| `{category}` | {category_totals[category]} |")
        lines.append("")

    lines.append("## Driver Validation")
    lines.append("")
    if not driver_findings:
        lines.append("No MongoDB driver references found.")
        lines.append("")
    else:
        for path in sorted(driver_findings.keys()):
            hits = driver_findings[path]
            lines.append(f"### {path}")
            lines.append("")
            lines.append(f"- Total driver references in file: `{sum(hits.values())}`")
            lines.append("")
            lines.append("| Status | Driver | Notes | Count |")
            lines.append("|---|---|---|---:|")
            for signature in sorted(hits.keys(), key=lambda x: (x.status, x.name)):
                lines.append(
                    f"| `{signature.status}` | `{signature.name}` | {signature.notes} | {hits[signature]} |"
                )
            lines.append("")

    lines.append("## Driver Totals")
    lines.append("")
    if not driver_totals:
        lines.append("No driver totals to report.")
        lines.append("")
    else:
        lines.append("| Driver | Count |")
        lines.append("|---|---:|")
        for driver in sorted(driver_totals.keys()):
            lines.append(f"| `{driver}` | {driver_totals[driver]} |")
        lines.append("")

    lines.append("## Driver Status Totals")
    lines.append("")
    if not driver_status_totals:
        lines.append("No driver status totals to report.")
        lines.append("")
    else:
        lines.append("| Status | Count |")
        lines.append("|---|---:|")
        for status in sorted(driver_status_totals.keys()):
            lines.append(f"| `{status}` | {driver_status_totals[status]} |")
        lines.append("")

    return lines


def save_markdown_report(
    output_markdown: str,
    findings: Dict[str, Dict[UnsupportedItem, int]],
    driver_findings: Dict[str, Dict[DriverSignature, int]],
    files_scanned: int,
    total_items_considered: int,
    source_label: str,
):
    lines = build_markdown_report_lines(
        findings=findings,
        driver_findings=driver_findings,
        files_scanned=files_scanned,
        total_items_considered=total_items_considered,
        source_label=source_label,
    )

    with open(output_markdown, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def save_pdf_report(
    output_pdf: str,
    findings: Dict[str, Dict[UnsupportedItem, int]],
    driver_findings: Dict[str, Dict[DriverSignature, int]],
    files_scanned: int,
    total_items_considered: int,
    source_label: str,
):
    try:
        from markdown_pdf import MarkdownPdf, Section
    except ImportError as exc:
        raise RuntimeError(
            "markdown-pdf is not installed. Install with: pip install markdown-pdf"
        ) from exc

    markdown_content = "\n".join(
        build_markdown_report_lines(
            findings=findings,
            driver_findings=driver_findings,
            files_scanned=files_scanned,
            total_items_considered=total_items_considered,
            source_label=source_label,
        )
    )

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as tmp:
        tmp.write(markdown_content)
        tmp_markdown_path = tmp.name

    try:
        pdf = MarkdownPdf()
        pdf.add_section(Section(markdown_content, root=os.path.dirname(tmp_markdown_path)))
        pdf.save(output_pdf)
    finally:
        try:
            os.unlink(tmp_markdown_path)
        except OSError:
            pass


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan source files for MongoDB features unsupported by OCI Oracle Database API for MongoDB."
        )
    )
    parser.add_argument(
        "target_dir",
        help="Directory containing source code to scan.",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Optional path to save full scan report as JSON.",
    )
    parser.add_argument(
        "--output-markdown",
        default=None,
        help="Optional path to save full scan report as Markdown.",
    )
    parser.add_argument(
        "--output-pdf",
        default=None,
        help="Optional path to save full scan report as PDF (requires markdown-pdf).",
    )
    parser.add_argument(
        "--include-all-text-files",
        action="store_true",
        help="Scan all text-like files instead of only known source extensions.",
    )
    parser.add_argument(
        "--extra-extension",
        action="append",
        default=[],
        help="Additional extension to include (repeatable), e.g. --extra-extension .vue",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Additional directory names to exclude from recursive scan.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)

    target_dir = os.path.abspath(args.target_dir)
    if not os.path.isdir(target_dir):
        print(f"ERROR: target_dir does not exist or is not a directory: {target_dir}", file=sys.stderr)
        return 2

    include_extensions = set(DEFAULT_INCLUDE_EXTENSIONS)
    for ext in args.extra_extension:
        normalized = ext if ext.startswith(".") else f".{ext}"
        include_extensions.add(normalized.lower())

    exclude_dirs = set(DEFAULT_EXCLUDED_DIRS)
    exclude_dirs.update(args.exclude_dir)

    unsupported_items, source_label = load_unsupported_items()

    findings, driver_findings, files_scanned = scan_codebase(
        root_dir=target_dir,
        unsupported_items=unsupported_items,
        exclude_dirs=exclude_dirs,
        include_extensions=include_extensions,
        include_all_text_files=args.include_all_text_files,
    )

    print_human_report(
        findings=findings,
        driver_findings=driver_findings,
        files_scanned=files_scanned,
        total_items_considered=len(unsupported_items),
        source_label=source_label,
    )

    if args.output_json:
        output_json = os.path.abspath(args.output_json)
        save_json_report(
            output_json=output_json,
            findings=findings,
            driver_findings=driver_findings,
            files_scanned=files_scanned,
            total_items_considered=len(unsupported_items),
            source_label=source_label,
        )
        print()
        print(f"JSON report saved at: {output_json}")

    if args.output_markdown:
        output_markdown = os.path.abspath(args.output_markdown)
        save_markdown_report(
            output_markdown=output_markdown,
            findings=findings,
            driver_findings=driver_findings,
            files_scanned=files_scanned,
            total_items_considered=len(unsupported_items),
            source_label=source_label,
        )
        print()
        print(f"Markdown report saved at: {output_markdown}")

    if args.output_pdf:
        output_pdf = os.path.abspath(args.output_pdf)
        save_pdf_report(
            output_pdf=output_pdf,
            findings=findings,
            driver_findings=driver_findings,
            files_scanned=files_scanned,
            total_items_considered=len(unsupported_items),
            source_label=source_label,
        )
        print()
        print(f"PDF report saved at: {output_pdf}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
