# Campus Green Space Dataset Notes

This README records project instructions, assistant answers, and formal notes about the CSV files in this directory.

## Current User Instructions

- Explain the CSV files in this directory simply.
- Build a README to record user instructions and assistant answers, including formal answers.
- Build an HTML visualization page using simple charts for the bird, plant, and location CSVs, excluding the source-list CSV.
- Add switching between birds, plants, and locations.
- Add switching between English and Simplified Chinese.
- Write the latest instructions and answers into `README.md`.
- Split each top bird locality bar into migratory and resident bird segments.

## Directory Contents

This directory contains four CSV files related to campus green-space biodiversity:


| File                                  | Simple meaning                                | Rows   |
| ------------------------------------- | --------------------------------------------- | ------ |
| `ERDP-2021-02.2.1-Bird_List.csv`      | Bird species recorded at university campuses  | 6,423  |
| `ERDP-2021-02.3.1-Locality_Infor.csv` | Campus/location information                   | 404    |
| `ERDP-2021-02.4.1-Plant_List.csv`     | Plant species recorded at university campuses | 46,558 |
| `ERDP-2021-02.5.1-Source_List.csv`    | Bibliographic sources for the records         | 272    |


## Visualization Page

The file `index.html` is a standalone bilingual dashboard for the dataset. It visualizes the bird list, plant list, and locality information CSVs with simple bar charts and pie charts. The source-list CSV is not charted.

To use it, open `index.html` in a web browser. The page includes:

- Dataset tabs for birds, plants, and locations.
- Language switching between English and Simplified Chinese.
- Summary cards for total records, species/locality counts, average area, and average elevation.
- Bar charts and pie charts based on precomputed summaries from the CSV files.

## Simple Explanation

These CSVs form a campus biodiversity dataset. They describe university campuses, the bird species found there, the plant species found there, and the references or sources where those records came from.

The most important linking fields are:

- `LocationID`: connects bird and plant records to a campus in the locality table.
- `SourceID`: connects bird and plant records to a reference in the source table.

### `ERDP-2021-02.3.1-Locality_Infor.csv`

This is the place table. Each row represents one campus or locality.

Important columns include:

- `LocationID`: unique ID for the campus/locality.
- `Region`, `Province`, `City`: where the campus is located.
- `Locality`: campus or locality name.
- `Locality_Type`: type of locality, such as campus.
- `Elevation (m)`: elevation in meters.
- `decimalLatitude`, `decimalLongitude`: geographic coordinates.
- `MAT (deg C)`: mean annual temperature.
- `MAP (mm)`: mean annual precipitation.
- `Area (ha)`: campus/locality area in hectares.
- `EstablishedYear`: year the campus or institution was established.

### `ERDP-2021-02.2.1-Bird_List.csv`

This is the bird record table. Each row records one bird taxon observed or reported at one campus.

Important columns include:

- `LocationID`: connects the bird record to a campus.
- `Locality`: campus name.
- `ScientificName`: scientific bird name.
- `Family`, `Genus`, `SpecificEpithet`: taxonomic information.
- `TaxonRank`: taxonomic rank, usually species.
- `Bird_MigrantStatus`: migration status, such as resident or migratory.
- `Bird_SurveyTime`: survey period.
- `SourceID`: connects the record to a source.

### `ERDP-2021-02.4.1-Plant_List.csv`

This is the plant record table. Each row records one plant taxon observed or reported at one campus.

Important columns include:

- `LocationID`: connects the plant record to a campus.
- `Locality`: campus name.
- `ScientificName`: scientific plant name.
- `Family`, `Genus`, `SpecificEpithet`: taxonomic information.
- `TaxonRank`: taxonomic rank, usually species.
- `GrowthForm`: plant type, such as tree, herb, shrub, or vine.
- `Plant_NativenessStatus`: whether the plant is native or nonnative.
- `SourceID`: connects the record to a source.

### `ERDP-2021-02.5.1-Source_List.csv`

This is the source table. Each row describes one reference used for bird or plant records.

Important columns include:

- `SourceID`: unique source ID.
- `Source`: source citation in English or romanized form.
- `SourceType`: source category, such as paper or book.
- `Source_CN`: Chinese source citation.

## Formal Dataset Description

This dataset documents biodiversity records associated with campus green spaces. It is organized as a relational set of CSV tables. The locality table provides geographic, climatic, spatial, and institutional attributes for each campus or locality. The bird and plant tables provide taxonomic occurrence records linked to localities through `LocationID`. The source table provides bibliographic metadata linked to species records through `SourceID`.

The dataset can support analyses of campus biodiversity patterns, including species richness, taxonomic composition, plant nativeness, bird migration status, geographic distribution, and relationships between biodiversity and campus attributes such as area, climate, elevation, region, or establishment year.

## Previous Assistant Answer

These CSVs are a campus green-space biodiversity dataset. They describe Chinese university campuses, the bird species recorded there, the plant species recorded there, and the sources those records came from.

- `ERDP-2021-02.3.1-Locality_Infor.csv`: the campus/place table. One row per locality, with `LocationID`, region, province, city, campus name, elevation, latitude/longitude, climate values, area, and established year. It has `404` locations.
- `ERDP-2021-02.2.1-Bird_List.csv`: bird records by campus. Each row says a bird species was recorded at a particular `LocationID`. It includes scientific name, family, genus, migrant/resident status, survey time, and `SourceID`. It has `6,423` rows across `171` locations.
- `ERDP-2021-02.4.1-Plant_List.csv`: plant records by campus. Each row says a plant species was recorded at a particular `LocationID`. It includes scientific name, family, genus, growth form like herb/tree, native/non-native status, and `SourceID`. It has `46,558` rows across `254` locations.
- `ERDP-2021-02.5.1-Source_List.csv`: bibliography/source table. `SourceID` links bird and plant records back to papers, books, theses, or other sources. It has `272` sources.

The key links are simple: `LocationID` connects bird/plant records to campus details, and `SourceID` connects bird/plant records to the reference source.



### 2026-04-15: Explain The CSV Files

**User instruction or question**

Please explain the CSVs simply in this directory.

**Assistant answer**

The directory contains four related CSV files forming a campus green-space biodiversity dataset:

- `ERDP-2021-02.3.1-Locality_Infor.csv`: campus and location information, including region, province, city, coordinates, climate, area, elevation, and established year.
- `ERDP-2021-02.2.1-Bird_List.csv`: bird records by location, including scientific name, taxonomy, migrant/resident status, survey time, and source ID.
- `ERDP-2021-02.4.1-Plant_List.csv`: plant records by location, including scientific name, taxonomy, growth form, native/nonnative status, and source ID.
- `ERDP-2021-02.5.1-Source_List.csv`: bibliography and source metadata linked to bird and plant records by `SourceID`.

The main linking fields are `LocationID`, which connects bird and plant records to campus/locality details, and `SourceID`, which connects records to references.

**Files or outputs affected**

No files were changed for this instruction.



### 2026-04-15: Create README

**User instruction or question**

Could you help me build up a README for recording my instructions and your answers, including the formal ones?

**Assistant answer**

A new `README.md` was created to record project instructions, assistant answers, formal dataset notes, CSV explanations, and future Q&A entries. It includes sections for current user instructions, directory contents, simple explanation, formal dataset description, previous assistant answer, and a reusable future entry template.

**Files or outputs affected**

- `README.md`





### 2026-04-15: Create HTML Visualization Dashboard

**User instruction or question**

Can you help me build up an HTML page using simple charts to visualize these CSVs except the source-list CSV? Use bar charts, pie charts, etc. The page should switch between birds, plants, and locations, and also switch between English and Simplified Chinese.

**Assistant answer**

A standalone bilingual dashboard was created in `index.html`. It visualizes the bird list, plant list, and locality information CSVs using simple bar charts and pie charts. The source-list CSV is excluded from the charts.

The page includes:

- Tabs for `Birds`, `Plants`, and `Locations`.
- Language switching between English and Simplified Chinese.
- Summary cards for record counts, species counts, locality counts, average area, and average elevation.
- Bird charts for migration status, top bird families, and top bird localities.
- Plant charts for nativeness, growth forms, and top plant families.
- Location charts for region distribution, location type, and top provinces.

The dashboard is self-contained and does not require internet access, Chart.js, or external packages.

**Files or outputs affected**

- `index.html`
- `README.md`



### 2026-04-15: Record Latest Instructions And Answers

**User instruction or question**

Can you write the instructions and the answers to the `README.md`?

**Assistant answer**

The README was updated with a chronological Q&A log that records the earlier CSV explanation request, the README creation request, the HTML visualization dashboard request, and this documentation update request.

**Files or outputs affected**

- `README.md`

### 2026-04-15: Split Top Bird Locality Bars By Migration Status

**User instruction or question**

For Top bird localities, can you split each bar into 2 colors, one color for Migratory birds and another for Resident? Do not forget to add this question and your answer into `README.md`.

**Assistant answer**

The `Top bird localities` chart in `index.html` was changed from a single-color bar chart into a stacked bar chart. Each locality bar now has two colored segments:

- Migratory birds are shown in blue-green.
- Resident birds are shown in yellow.

The chart keeps the same top ten localities and total record counts, but now also shows the composition of migratory and resident bird records within each locality. A compact legend was added, and the note is translated in both English and Simplified Chinese.

**Files or outputs affected**

- `index.html`
- `README.md`





### Entry Template

**User instruction or question**

Write the user request here.

**Assistant answer**

Write the answer or summary here.

**Files or outputs affected**

List related files, charts, notebooks, scripts, or results here.