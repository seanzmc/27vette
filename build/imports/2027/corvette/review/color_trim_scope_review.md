# Color/Trim Scope Review

Do not edit this generated review packet as source of truth. Transfer approved decisions into data/import_maps/corvette_2027/*.csv.

This review packet is generated evidence only. It does not update staging CSVs, import maps, or canonical CSVs.

## Readiness Snapshot

- primary_variant_matrix_ready: `true`
- color_trim_ready: `false`
- pricing_ready: `true`
- equipment_groups_ready: `true`
- rpo_role_overlaps_ready: `false`
- canonical_proposal_ready: `false`
- color_trim_review_status_counts: `{"needs_review": 6}`
- resolved_overlap_count: `0`
- mapped_overlap_count: `10`
- observed_overlap_count: `10`

## Decision Options

- `approved`: eligible for later canonical proposal work.
- `accepted_review_only`: intentionally retained as evidence, not canonical import-ready.
- `deferred`: known not ready yet.
- `needs_review`: unresolved.

## Review Rows

| source_sheet | section_role | section_index | start_row | end_row | row_count | sample_interior_rpos | sample_exterior_colors | current_review_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Color and Trim 1 | color_trim_interior_matrix | 1 | 3 | 14 | 40 | HTA \| HUP \| HUQ \| HTJ \| H1Y \| HUN \| HUR \| HUV | Sebring Orange Tintcoat \| Sebring Orange Tintcoat9 \| Roswell Green Metallic \| Roswell Green Metallic10 \| Arctic White \| Black \| Competition Yellow Tintcoat Metallic \| Competition Yellow Tintcoat Metallic9 | accepted_review_only |
| Color and Trim 1 | color_trim_compatibility_matrix | 2 | 14 | 26 | 130 | HTA \| HUP \| HUQ \| HTJ \| H1Y \| HUN \| HUR \| HUV | Sebring Orange Tintcoat \| Sebring Orange Tintcoat9 \| Roswell Green Metallic \| Roswell Green Metallic10 \| Arctic White \| Black \| Competition Yellow Tintcoat Metallic \| Competition Yellow Tintcoat Metallic9 | accepted_review_only |
| Color and Trim 1 | color_trim_disclosure | 3 | 27 | 27 | 2 | HTA \| HUP \| HUQ \| HTJ \| H1Y \| HUN \| HUR \| HUV | Sebring Orange Tintcoat \| Sebring Orange Tintcoat9 \| Roswell Green Metallic \| Roswell Green Metallic10 \| Arctic White \| Black \| Competition Yellow Tintcoat Metallic \| Competition Yellow Tintcoat Metallic9 | accepted_review_only |
| Color and Trim 2 | color_trim_interior_matrix | 1 | 3 | 9 | 9 | HZB \| HVV \| HUU \| HU0 \| HVT \| HMO \| HZP \| HXO | Sebring Orange Tintcoat \| Sebring Orange Tintcoat4 \| Roswell Green Metallic \| Roswell Green Metallic5 \| Arctic White \| Black \| Competition Yellow Tintcoat Metallic \| Competition Yellow Tintcoat Metallic4 | accepted_review_only |
| Color and Trim 2 | color_trim_compatibility_matrix | 2 | 9 | 21 | 40 | HZB \| HVV \| HUU \| HU0 \| HVT \| HMO \| HZP \| HXO | Sebring Orange Tintcoat \| Sebring Orange Tintcoat4 \| Roswell Green Metallic \| Roswell Green Metallic5 \| Arctic White \| Black \| Competition Yellow Tintcoat Metallic \| Competition Yellow Tintcoat Metallic4 | accepted_review_only |
| Color and Trim 2 | color_trim_disclosure | 3 | 22 | 22 | 1 | HZB \| HVV \| HUU \| HU0 \| HVT \| HMO \| HZP \| HXO | Sebring Orange Tintcoat \| Sebring Orange Tintcoat4 \| Roswell Green Metallic \| Roswell Green Metallic5 \| Arctic White \| Black \| Competition Yellow Tintcoat Metallic \| Competition Yellow Tintcoat Metallic4 | accepted_review_only |

The CSV is the complete review surface.
