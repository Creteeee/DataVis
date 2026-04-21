# Campus Green Space Benchmark Findings

Generated from local files only: 04/20/2026 16:17:24

## Findings summary

- Shanghai campus plant subset: 1257 rows, 690 unique scientific names, 7 campus/locality names.
- Shanghai city workbook: 7008 district-record rows, 1238 unique scientific names.
- After simple binomial normalization, 205 campus names overlap with the city checklist. This covers 17.2% of city normalized species and matches 31.4% of campus normalized species.
- Campus unique-species nonnative share: 46.7%. City unique-species non-native share: 30.7%.
- The campus nonnative share is higher under the local labels, but a formal claim needs a curated label crosswalk.

## Missingness report

The inspected core CSV files show no missing cells in declared columns. The more important gaps are schema gaps: no campus invasive label, no shared canonical taxon key, no local XML files despite the prompt naming XML, and no explicit license file.

## Curator task list

- Add or remove the XML references in the benchmark manifest.
- Create a canonical taxon-name table for campus and city records.
- Harmonize Native/Nonnative with the city workbook's Shanghai native/non-native labels.
- Export city XLSX sheets to canonical CSV files.
- Add license and citation instructions.
- Document whether district gaps are ecological absences or sampling absences.

## Suggested benchmark tasks

- Schema matching between campus and city plant data.
- Taxon normalization from scientific names with and without authors.
- Campus vs city nativeness comparison with clear denominators.
- District coverage audit and bias statement.
- Student dashboard generation with evidence-linked charts.

## Suggested metrics and evaluation protocol

- Score schema matches with precision and recall against a curated crosswalk.
- Score taxon normalization by canonical-name accuracy and unresolved-review rate.
- Score quantitative answers by correct numerator, denominator, percentage, and caveat.
- Score visual outputs by evidence links, unit clarity, and correct treatment of missing coverage.
- Compare tools fairly using the same data slice, same prompt, same local-only rule, and same rubric.

## Output files

- CampusGreenSpace_Benchmark_CourseMaterial.html
- benchmark_profile.json
- benchmark_findings_summary.md
