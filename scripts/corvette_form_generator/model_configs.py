"""Model-specific generator configuration."""

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
    "delivery",
    "customer_info",
    "summary",
)

STEP_LABELS = {
    "body_style": "Body Style",
    "trim_level": "Trim Level",
    "paint": "Exterior Paint",
    "exterior_appearance": "Exterior Appearance",
    "wheels": "Wheels & Brake Calipers",
    "packages_performance": "Packages & Performance",
    "aero_exhaust_stripes_accessories": "Aero, Exhaust, Stripes & Accessories",
    "seat": "Seats",
    "base_interior": "Base Interior",
    "seat_belt": "Seat Belt",
    "interior_trim": "Interior Trim",
    "delivery": "Custom Delivery",
    "customer_info": "Customer Information",
    "summary": "Summary",
    "standard_equipment": "Standard Equipment",
}

CONTEXT_SECTIONS = (
    {
        "section_id": "sec_context_body_style",
        "section_name": "Body Style",
        "category_id": "cat_context_001",
        "category_name": "Vehicle Context",
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
        "category_id": "cat_context_001",
        "category_name": "Vehicle Context",
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
    "sec_onst_001": "interior_trim",
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

STINGRAY_MODEL = ModelConfig(
    model_key="stingray",
    model_label="Stingray",
    model_year="2027",
    dataset_name="2027 Corvette Stingray operational form",
    source_option_sheet="stingray_master",
    variant_ids=("1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"),
    expected_variant_count=6,
    root=ROOT,
    workbook_path=WORKBOOK_PATH,
    output_dir=OUTPUT_DIR,
    app_dir=APP_DIR,
    interior_reference_path=ROOT / "architectureAudit" / "stingray_interiors_refactor.csv",
    generated_sheets=GENERATED_SHEETS,
    step_order=STEP_ORDER,
    step_labels=STEP_LABELS,
    context_sections=CONTEXT_SECTIONS,
    body_style_display_order=BODY_STYLE_DISPLAY_ORDER,
    selection_mode_labels=SELECTION_MODE_LABELS,
    standard_sections=STANDARD_SECTIONS,
    section_step_overrides=SECTION_STEP_OVERRIDES,
)

GRAND_SPORT_MODEL = ModelConfig(
    model_key="grand_sport",
    model_label="Grand Sport",
    model_year="2027",
    dataset_name="2027 Corvette Grand Sport operational form",
    source_option_sheet="grandSport",
    variant_ids=("1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"),
    expected_variant_count=6,
    root=ROOT,
    workbook_path=WORKBOOK_PATH,
    output_dir=OUTPUT_DIR,
    app_dir=APP_DIR,
    interior_reference_path=ROOT / "architectureAudit" / "grand_sport_interiors_refactor.csv",
    generated_sheets=GENERATED_SHEETS,
    step_order=STEP_ORDER,
    step_labels=STEP_LABELS,
    context_sections=CONTEXT_SECTIONS,
    body_style_display_order=BODY_STYLE_DISPLAY_ORDER,
    selection_mode_labels=SELECTION_MODE_LABELS,
    standard_sections=STANDARD_SECTIONS,
    section_step_overrides=SECTION_STEP_OVERRIDES
    | {
        "sec_gsha_001": "exterior_appearance",
        "sec_spec_001": "packages_performance",
        "sec_colo_001": "interior_trim",
    },
    blank_section_overrides={
        "opt_pcq_001": "sec_lpoe_001",
        "opt_pdy_001": "sec_lpoi_001",
        "opt_pef_001": "sec_lpoi_001",
    },
    notes=(
        "Read-only inspection only: Grand Sport generation is not activated by the Stingray entrypoint.",
        "PCQ, PDY, and PEF blank-section normalization must remain explicit config or validation output.",
    ),
)
