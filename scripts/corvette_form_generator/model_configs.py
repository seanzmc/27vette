"""Model configuration: shared constants plus workbook-first base configs.

The workbook owns model-specific metadata through ``model_master``,
``model_workbook_sources``, ``model_variants``, and
``model_registry_promotion``; resolve a base config against it with
``runtime_metadata.load_model_config_overrides``. Python keeps filesystem
paths, unpromoted-model compatibility defaults, and promoted-model
completeness expectations. Promoted runtime metadata such as steps, context
sections, and order-summary grouping must come from workbook rows.
"""

from __future__ import annotations

from pathlib import Path

from corvette_form_generator.model_config import ModelConfig


ROOT = Path(__file__).resolve().parents[2]
WORKBOOK_PATH = ROOT / "stingray_master.xlsx"
OUTPUT_DIR = ROOT / "form-output"
APP_DIR = ROOT / "form-app"

GENERATED_SHEETS = (
    "form_steps",
    "form_context_choices",
    "form_choices",
    "form_standard_equipment",
    "form_rule_groups",
    "form_exclusive_groups",
    "form_rules",
    "form_price_rules",
    "form_interiors",
    "form_color_overrides",
    "form_validation",
)

STEP_ORDER = (
    "body_style",
    "trim_level",
    "paint",
    "exterior_appearance",
    "wheels",
    "packages_performance",
    "aero_exhaust_stripes_accessories",
    "seat",
    "base_interior",
    "seat_belt",
    "interior_trim",
    "accessories",
    "delivery",
    "summary",
)

STEP_LABELS = {
    "body_style": "Body Style",
    "trim_level": "Trim Level",
    "paint": "Exterior Paint",
    "exterior_appearance": "Exterior Appearance",
    "wheels": "Wheels & Brake Calipers",
    "packages_performance": "Performance & Aero",
    "aero_exhaust_stripes_accessories": "Stripes",
    "seat": "Seats",
    "base_interior": "Interior Color",
    "seat_belt": "Seat Belt",
    "interior_trim": "Interior Trim",
    "accessories": "Accessories",
    "delivery": "Custom Delivery",
    "summary": "Summary",
    "standard_equipment": "Standard Equipment",
}

CONTEXT_SECTIONS = (
    {
        "section_id": "sec_context_body_style",
        "section_name": "Body Style",
        "selection_mode": "single_select_req",
        "selection_mode_label": "Required single choice",
        "choice_mode": "single",
        "is_required": "True",
        "standard_behavior": "user_selected",
        "section_display_order": 1,
        "step_key": "body_style",
        "step_label": "Body Style",
    },
    {
        "section_id": "sec_context_trim_level",
        "section_name": "Trim Level",
        "selection_mode": "single_select_req",
        "selection_mode_label": "Required single choice",
        "choice_mode": "single",
        "is_required": "True",
        "standard_behavior": "user_selected",
        "section_display_order": 2,
        "step_key": "trim_level",
        "step_label": "Trim Level",
    },
)

SECTION_STEP_OVERRIDES = {
    "sec_pain_001": "paint",
    "sec_whee_002": "wheels",
    "sec_cali_001": "wheels",
    "sec_roof_001": "exterior_appearance",
    "sec_exte_001": "exterior_appearance",
    "sec_badg_001": "exterior_appearance",
    "sec_engi_001": "exterior_appearance",
    "sec_perf_001": "packages_performance",
    "sec_susp_001": "packages_performance",
    "sec_seat_002": "seat",
    "sec_intc_001": "base_interior",
    "sec_intc_002": "base_interior",
    "sec_intc_003": "base_interior",
    "sec_seat_001": "seat_belt",
    "sec_inte_001": "interior_trim",
    "sec_lpoi_001": "interior_trim",
    "sec_whee_001": "wheels",
    "sec_gsce_001": "exterior_appearance",
    "sec_gsha_001": "exterior_appearance",
    "sec_colo_001": "interior_trim",
    "sec_onst_001": "interior_trim",
    "sec_cust_002": "interior_trim",
    "sec_spec_001": "packages_performance",
    "sec_cust_001": "delivery",
}

BODY_STYLE_DISPLAY_ORDER = {
    "coupe": 1,
    "convertible": 2,
}

SELECTION_MODE_LABELS = {
    "single_select_req": "Required single choice",
    "single_select_opt": "Optional single choice",
    "multi_select_opt": "Optional multiple choice",
    "display_only": "Display only",
}

STANDARD_SECTIONS = frozenset(
    {
        "sec_1lte_001",
        "sec_2lte_001",
        "sec_3lte_001",
        "sec_incl_001",
        "sec_stan_001",
        "sec_stan_002",
        "sec_safe_001",
        "sec_tech_001",
    }
)

DEFAULT_TEXT_CLEANUP = {
    "enabled": True,
    "normalize_new_prefix": True,
    "collapse_whitespace": True,
    "collapse_repeated_punctuation": True,
    "remove_adjacent_duplicate_phrases": True,
}

GRAND_SPORT_SECTION_LABEL_OVERRIDES = {
    "sec_gsce_001": "Grand Sport Center Stripes",
    "sec_gsha_001": "Grand Sport Heritage Hash Marks",
    "sec_spec_001": "Special Edition",
    "sec_colo_001": "Color Combination Override",
}

_SECTION_LABEL_OVERRIDES_BY_MODEL = {
    "grand_sport": GRAND_SPORT_SECTION_LABEL_OVERRIDES,
}

_MODEL_NOTES = {
    "grand_sport": (
        "Read-only inspection only: Grand Sport generation is not activated by the Stingray entrypoint.",
        "Grand Sport option rows are read from the normalized grandSport_options sheet.",
    ),
    "z06": (
        "Z06 is eligible for runtime promotion through workbook-owned model_registry_promotion rows.",
        "Z06 option rows are read from normalized z06_options source rows.",
    ),
}


def base_model_config(model_key: str) -> ModelConfig:
    """Build the Python-side base config for any model key.

    Every workbook-expressible field (label, year, dataset name, sheet roles,
    variants) carries only a conventional default here; the workbook metadata
    sheets are authoritative once the config is resolved through
    ``load_model_config_overrides``.
    """

    label = model_key.replace("_", " ").title()
    slug = model_key.replace("_", "-")
    return ModelConfig(
        model_key=model_key,
        model_label=label,
        model_year="2027",
        dataset_name=f"2027 Corvette {label} operational form",
        source_option_sheet=f"{model_key}_options",
        status_sheet=f"{model_key}_ovs",
        variant_ids=(),
        expected_variant_count=0,
        root=ROOT,
        workbook_path=WORKBOOK_PATH,
        output_dir=OUTPUT_DIR,
        app_dir=APP_DIR,
        generated_sheets=GENERATED_SHEETS,
        step_order=STEP_ORDER,
        step_labels=STEP_LABELS,
        context_sections=CONTEXT_SECTIONS,
        body_style_display_order=BODY_STYLE_DISPLAY_ORDER,
        selection_mode_labels=SELECTION_MODE_LABELS,
        standard_sections=STANDARD_SECTIONS,
        section_step_overrides=SECTION_STEP_OVERRIDES,
        section_label_overrides=_SECTION_LABEL_OVERRIDES_BY_MODEL.get(model_key, {}),
        preview_artifact_prefix=f"{slug}-contract-preview",
        draft_artifact_prefix=f"{slug}-form-data-draft",
        text_cleanup=dict(DEFAULT_TEXT_CLEANUP),
        notes=_MODEL_NOTES.get(model_key, ()),
    )


STINGRAY_MODEL = base_model_config("stingray")
GRAND_SPORT_MODEL = base_model_config("grand_sport")
Z06_MODEL = base_model_config("z06")
