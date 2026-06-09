"""Shared PriceRef pricing helpers for Corvette form generation.

Single source of truth for seat/component price lookups and R6X price
arithmetic. OptionType normalization uses ``price_ref_component_type_key``
(strip non-alphanumerics, lowercase) so workbook formatting variants such as
``TwoTone`` / ``two_tone`` / ``Two Tone`` resolve to the same key.
"""

from __future__ import annotations

import re

from corvette_form_generator.workbook import clean, money


def price_ref_key(trim: str, code: str) -> tuple[str, str]:
    return (clean(trim).replace("_", " "), clean(code))


def price_ref_prices(rows: list[dict[str, str]]) -> dict[tuple[str, str], int]:
    prices: dict[tuple[str, str], int] = {}
    for row in rows:
        if clean(row.get("OptionType", "")).lower() != "seat":
            continue
        trim = clean(row.get("Trim", ""))
        code = clean(row.get("Code", ""))
        if trim and code:
            prices[price_ref_key(trim, code)] = money(row.get("Price"))
    return prices


def price_ref_component_type_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def price_ref_component_prices(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], int]:
    prices: dict[tuple[str, str, str], int] = {}
    for row in rows:
        option_type = price_ref_component_type_key(row.get("OptionType", ""))
        code = clean(row.get("Code", ""))
        if not option_type or not code:
            continue
        prices[(option_type, clean(row.get("Trim", "")).replace("_", " "), code)] = money(row.get("Price"))
    return prices


def price_ref_component_price(
    price_ref: dict[tuple[str, str, str], int],
    option_type: str,
    code: str,
    trim: str = "",
) -> int:
    normalized_type = price_ref_component_type_key(option_type)
    normalized_trim = clean(trim).replace("_", " ")
    normalized_code = clean(code)
    if (normalized_type, normalized_trim, normalized_code) in price_ref:
        return price_ref[(normalized_type, normalized_trim, normalized_code)]
    return price_ref.get((normalized_type, "", normalized_code), 0)


def r6x_price_component(row: dict[str, str], price_ref: dict[tuple[str, str], int]) -> int:
    trim = clean(row.get("Trim", ""))
    interior_id = clean(row.get("interior_id", "") or row.get("ID", ""))
    if "R6X" not in trim and "R6X" not in interior_id:
        return 0

    seat = clean(row.get("Seat", ""))
    r6x_trim = trim if "R6X" in trim else f"{trim}_R6X"
    base_trim = r6x_trim.replace("_R6X", "")
    r6x_price = price_ref.get(price_ref_key(r6x_trim, seat))
    if r6x_price is None:
        return 0
    return max(0, r6x_price - price_ref.get(price_ref_key(base_trim, seat), 0))


def generated_interior_price(row: dict[str, str], price_ref: dict[tuple[str, str], int]) -> int:
    return money(row.get("Price") or row.get("Cost")) + r6x_price_component(row, price_ref)
