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

GRAND_SPORT_SECTION_CATEGORY_OVERRIDES = {
    "sec_lpoe_001": "cat_exte_001",
    "sec_whee_001": "cat_exte_001",
    "sec_spoi_001": "cat_exte_001",
    "sec_perf_001": "cat_mech_001",
    "sec_incl_001": "cat_stan_001",
    "sec_cali_001": "cat_exte_001",
    "sec_onst_001": "cat_stan_001",
    "sec_spec_001": "cat_mech_001",
}

GRAND_SPORT_OPTION_CATEGORY_OVERRIDES = {
    "opt_bv4_001": "cat_inte_001",
    "opt_pin_001": "cat_exte_001",
    "opt_r8c_001": "cat_exte_001",
}

GRAND_SPORT_SOURCE_CATEGORY_OVERRIDES = {
    "opt_cfl_001": "cat_exte_001",
    "opt_cfv_001": "cat_exte_001",
    "opt_cfx_001": "cat_inte_001",
    "opt_cfz_001": "cat_exte_001",
    "opt_drg_001": "cat_exte_001",
    "opt_e60_001": "cat_exte_001",
    "opt_j56_001": "cat_mech_001",
    "opt_j6a_001": "cat_mech_001",
    "opt_j6b_001": "cat_mech_001",
    "opt_j6d_001": "cat_mech_001",
    "opt_j6e_001": "cat_mech_001",
    "opt_j6f_001": "cat_mech_001",
    "opt_j6l_001": "cat_mech_001",
    "opt_j6n_001": "cat_mech_001",
    "opt_t0e_002": "cat_exte_001",
    "opt_t0f_001": "cat_exte_001",
    "opt_tr7_001": "cat_exte_001",
    "opt_xfr_001": "cat_exte_001",
    "opt_xfs_001": "cat_exte_001",
    "opt_z25_001": "cat_exte_001",
}

GRAND_SPORT_SECTION_LABEL_OVERRIDES = {
    "sec_gsce_001": "Grand Sport Center Stripes",
    "sec_gsha_001": "Grand Sport Heritage Hash Marks",
    "sec_spec_001": "Special Edition",
    "sec_colo_001": "Color Combination Override",
}

STINGRAY_MODEL = ModelConfig(
    model_key="stingray",
    model_label="Stingray",
    model_year="2027",
    dataset_name="2027 Corvette Stingray operational form",
    source_option_sheet="stingray_options",
    status_sheet="stingray_ovs",
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
    source_option_sheet="grandSport_options",
    status_sheet="grandSport_ovs",
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
    section_category_overrides=GRAND_SPORT_SECTION_CATEGORY_OVERRIDES,
    option_category_overrides=GRAND_SPORT_OPTION_CATEGORY_OVERRIDES,
    source_category_overrides=GRAND_SPORT_SOURCE_CATEGORY_OVERRIDES,
    section_label_overrides=GRAND_SPORT_SECTION_LABEL_OVERRIDES,
    preview_artifact_prefix="grand-sport-contract-preview",
    draft_artifact_prefix="grand-sport-form-data-draft",
    rule_mapping_sheet="grandSport_rule_mapping",
    rule_groups_sheet="grandSport_rule_groups",
    rule_group_members_sheet="grandSport_rule_group_members",
    exclusive_groups_sheet="grandSport_exclusive_groups",
    exclusive_group_members_sheet="grandSport_exclusive_members",
    text_cleanup={
        "enabled": True,
        "normalize_new_prefix": True,
        "collapse_whitespace": True,
        "collapse_repeated_punctuation": True,
        "remove_adjacent_duplicate_phrases": True,
    },
    special_rule_review_rpos=("EL9", "Z25", "FEY", "Z15"),
    notes=(
        "Read-only inspection only: Grand Sport generation is not activated by the Stingray entrypoint.",
        "Grand Sport option rows are read from the normalized grandSport_options sheet.",
    ),
)
