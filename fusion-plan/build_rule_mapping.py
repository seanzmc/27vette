#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path


SOURCE_CSV = Path("/Users/seandm/Downloads/27_vette_app - stingray_master (1).csv")
OUTPUTS = [
    Path("/Users/seandm/Projects/27vette/Rule_Mapping.csv"),
    Path("/Users/seandm/Projects/27vette/fusion-plan/Rule_Mapping.csv"),
]


CODE_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z0-9]{3})(?![A-Za-z0-9])")
PAREN_RE = re.compile(r"\(([^)]*)\)")

NOISE_CODES = {
    "ADD",
    "ALL",
    "AND",
    "ANY",
    "ARE",
    "BAC",
    "BFU",
    "COM",
    "END",
    "FBC",
    "FGO",
    "FNR",
    "FOR",
    "GPS",
    "GT2",
    "HOW",
    "INC",
    "ITS",
    "JET",
    "KIT",
    "LOW",
    "LPO",
    "LS6",
    "LUG",
    "MAY",
    "NON",
    "NOT",
    "ONE",
    "RED",
    "RPO",
    "SEE",
    "SKY",
    "SOLD",
    "SRE",
    "THE",
    "TRE",
    "VIN",
    "WHO",
    "YOU",
}

# phrase pattern, rule type, needs review, direction
TRIGGERS = [
    (re.compile(r"not\s+recommended\s+with", re.I), "excludes", True, "direct"),
    (re.compile(r"not\s+available\s+with", re.I), "excludes", False, "direct"),
    (re.compile(r"not\s+available\s+on", re.I), "excludes", True, "direct"),
    (re.compile(r"this\s+option\s+is\s+without", re.I), "excludes", False, "direct"),
    (re.compile(r"without", re.I), "excludes", True, "direct"),
    (re.compile(r"except\s+for\s+orders\s+with", re.I), "excludes", True, "direct"),
    (re.compile(r"required\s+and\s+only\s+available", re.I), "requires", True, "direct"),
    (re.compile(r"requires?", re.I), "requires", False, "direct"),
    (re.compile(r"included\s+and\s+only\s+available\s+with", re.I), "includes", True, "reverse"),
    (re.compile(r"included\s+with", re.I), "includes", False, "reverse"),
    (re.compile(r"also\s+includes?", re.I), "includes", False, "direct"),
    (re.compile(r"includes?", re.I), "includes", False, "direct"),
    (re.compile(r"comes\s+with", re.I), "includes", True, "direct"),
    (re.compile(r"recommended\s+with", re.I), "includes", True, "direct"),
    (re.compile(r"available\s+with", re.I), "requires", True, "direct"),
    (re.compile(r"will\s+delete", re.I), "excludes", True, "direct"),
    (re.compile(r"deletes?", re.I), "excludes", True, "direct"),
    (re.compile(r"removes?", re.I), "excludes", True, "direct"),
    (re.compile(r"when\s+ordered\s+with", re.I), "requires", True, "direct"),
    (re.compile(r"\bif\b", re.I), "requires", True, "direct"),
]


def load_source_rows() -> list[dict[str, str]]:
    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_rpo_index(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    rpo_to_option_ids: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        rpo = row.get("rpo", "").strip().upper()
        option_id = row.get("option_id", "").strip()
        if rpo and option_id and option_id not in rpo_to_option_ids[rpo]:
            rpo_to_option_ids[rpo].append(option_id)
    return rpo_to_option_ids


def parenthesized_codes(rows: list[dict[str, str]]) -> set[str]:
    codes: set[str] = set()
    for row in rows:
        detail_raw = row.get("detail_raw", "").upper()
        for group in PAREN_RE.findall(detail_raw):
            normalized = group.replace("/", ",").replace(";", ",")
            codes.update(code for code in CODE_RE.findall(normalized) if code not in NOISE_CODES)
    return codes


def clean_code(code: str, known_rpos: set[str], paren_codes: set[str]) -> str | None:
    code = code.strip().upper()
    if not CODE_RE.fullmatch(code) or code in NOISE_CODES:
        return None
    if code.isdigit() and code not in known_rpos and code not in paren_codes:
        return None
    return code


def extract_codes(text: str, known_rpos: set[str], paren_codes: set[str]) -> list[str]:
    text_u = text.upper()
    codes: list[str] = []

    for group in PAREN_RE.findall(text_u):
        normalized = group.replace("/", ",").replace(";", ",")
        for found in CODE_RE.findall(normalized):
            code = clean_code(found, known_rpos, paren_codes)
            if code:
                codes.append(code)

    for match in CODE_RE.finditer(text_u.replace("/", ",")):
        code = clean_code(match.group(1), known_rpos, paren_codes)
        if not code or code in codes:
            continue

        before = text_u[: match.start()]
        after = text_u[match.end() :]
        prev_char = before.rstrip()[-1:] if before.rstrip() else ""
        next_char = after.lstrip()[:1]
        prev_word = before.rstrip().split()[-1].strip("(:,;") if before.rstrip().split() else ""
        after_words = after.lstrip().split(None, 2)
        next_word = after_words[0].strip(".,;:)") if after_words else ""
        list_left = prev_char in {"", ",", "(", "/", ":"} or prev_word.lower() in {
            "and",
            "or",
            "require",
            "requires",
            "stripes",
            "with",
        }
        list_right = next_char in {"", ",", ")", "/", ".", ";", ":"} or next_word.lower() in {
            "and",
            "or",
        }
        if list_left and list_right and (code in known_rpos or code in paren_codes or any(ch.isdigit() for ch in code)):
            codes.append(code)

    return list(OrderedDict.fromkeys(codes))


def trigger_matches(text: str) -> list[tuple[int, int, str, str, bool, str]]:
    matches: list[tuple[int, int, str, str, bool, str]] = []
    for pattern, rule_type, review, direction in TRIGGERS:
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), match.group(0), rule_type, review, direction))

    matches.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    filtered: list[tuple[int, int, str, str, bool, str]] = []
    occupied_until = -1
    starts: set[int] = set()
    for match in matches:
        start, end = match[0], match[1]
        if start in starts or start < occupied_until:
            continue
        filtered.append(match)
        starts.add(start)
        occupied_until = end
    return filtered


def split_trigger_clauses(text: str) -> list[dict[str, str | bool]]:
    matches = trigger_matches(text)
    clauses: list[dict[str, str | bool]] = []
    for index, (start, _end, trigger, rule_type, review, direction) in enumerate(matches):
        next_start = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        clauses.append(
            {
                "text": text[start:next_start].strip(),
                "rule_type": rule_type,
                "review": review,
                "direction": direction,
                "trigger": trigger,
            }
        )
    if not clauses:
        clauses.append({"text": text.strip(), "rule_type": "", "review": True, "direction": "direct", "trigger": ""})
    return clauses


def emit_row(
    output_rows: list[dict[str, str]],
    seen_rows: set[tuple[str, str, str]],
    option_id: str,
    target_id: str,
    rule_type: str,
    detail_raw: str,
    review: bool,
) -> None:
    key = (option_id, target_id, rule_type)
    if not option_id or not target_id or key in seen_rows:
        return
    seen_rows.add(key)
    output_rows.append(
        {
            "option_id": option_id,
            "target_id": target_id,
            "rule_type": rule_type,
            "original_detail_raw": detail_raw,
            "review_flag": "TRUE" if review or not rule_type else "FALSE",
        }
    )


def build_rows(source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rpo_to_option_ids = build_rpo_index(source_rows)
    known_rpos = set(rpo_to_option_ids)
    paren_codes = parenthesized_codes(source_rows)
    output_rows: list[dict[str, str]] = []
    seen_rows: set[tuple[str, str, str]] = set()

    for row in source_rows:
        current_option_id = row.get("option_id", "").strip()
        current_rpo = row.get("rpo", "").strip().upper()
        detail_raw = row.get("detail_raw", "").strip()
        selectable = row.get("selectable", "").strip().upper()
        if not current_option_id or not current_rpo or not detail_raw or selectable != "TRUE":
            continue

        for clause in split_trigger_clauses(detail_raw):
            codes = extract_codes(str(clause["text"]), known_rpos, paren_codes)
            if not codes:
                continue
            review = bool(clause["review"]) or bool(re.search(r"\b(if|when|except)\b", str(clause["text"]), re.I))
            rule_type = str(clause["rule_type"])

            if clause["direction"] == "reverse" and rule_type == "includes":
                for source_rpo in codes:
                    source_option_ids = rpo_to_option_ids.get(source_rpo, [])
                    for source_option_id in source_option_ids:
                        emit_row(output_rows, seen_rows, source_option_id, current_rpo, rule_type, detail_raw, review)
                    if not source_option_ids:
                        emit_row(output_rows, seen_rows, source_rpo, current_rpo, rule_type, detail_raw, True)
            else:
                for target_id in codes:
                    emit_row(output_rows, seen_rows, current_option_id, target_id, rule_type, detail_raw, review)

    return output_rows


def write_rows(rows: list[dict[str, str]]) -> None:
    for output in OUTPUTS:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["option_id", "target_id", "rule_type", "original_detail_raw", "review_flag"],
            )
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    rows = build_rows(load_source_rows())
    write_rows(rows)
    print(f"wrote {len(rows)} rows")
    print(Counter(row["rule_type"] or "(blank)" for row in rows))
    print(f"review_flag=TRUE: {sum(row['review_flag'] == 'TRUE' for row in rows)}")


if __name__ == "__main__":
    main()
