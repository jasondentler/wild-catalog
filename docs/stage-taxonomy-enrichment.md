# Taxonomy Enrichment and Language Service

The Taxonomy Service enriches classifier predictions with canonical scientific
taxonomy and localized common names.

It uses the iNaturalist Taxonomy DarwinCore Archive, [ `taxonomy.dwca.zip` ](https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip), as the local source of truth for taxon records, parent-child relationships, taxonomic ranks, scientific names, and common names.

The service does **not** make live iNaturalist API calls during image
identification. The DarwinCore Archive is downloaded, parsed, and compiled into
local lookup tables ahead of request time so `/identify` responses remain fast, 
predictable, and available offline.

## Source Dataset

The service uses the [iNaturalist Taxonomy DarwinCore Archive](https://www.inaturalist.org/taxa/inaturalist-taxonomy.dwca.zip).

This archive provides the taxonomic tree and common-name data used
to enrich model predictions. 

[DarwinCore](https://dwc.tdwg.org/) is a zip file containing:
1. `meta.xml` identifying the core file, extension files, and column meaning.
2. `taxa.csv` containing the core taxonomic data
3. Language-specific extension files such as `VernacularNames-english.csv`
4. `eml.xml` containing background info not used by this application
5. Additional extension files not used by this application

## Why This Service Exists

Classifier models return machine-oriented class identifiers or logits. They do
not, by themselves, provide the full API response contract required by Wild
Catalog.

The API response requires each prediction to include:

* `confidence`
* `is_present`
* `taxonomy`
* `taxonomy_common_names`

The classifier is responsible for visual prediction. The Taxonomy Service is
responsible for turning classifier class IDs into user-facing taxonomic data.

Keeping this logic separate makes classifier models pluggable. A future
classifier can use a different class index as long as Wild Catalog can map that
classifier's class IDs to iNaturalist taxon IDs or another supported taxonomy
mapping.

## Example Data

> ***Important:*** Taxonomic lineages are not fixed to the classic seven
> ranks. The service returns every real ancestor present in the iNaturalist
> taxonomy tree, ordered from highest ancestor to predicted taxon.

**Example**: Chapman's Zebra ***(Equus quagga ssp. chapmani)***

| Index | Rank        | Taxon_id | Taxonomy value | Common (en-US)                     | Common (es-MX)                   | Common (zh-CN) |
|-------|-------------|----------|----------------|------------------------------------|----------------------------------|----------------|
| 0     | kingdom     | 1        | Animalia       | Animals                            | Animales                         | 动物界         |
| 1     | phylum      | 2        | Chordata       | Chordates                          | Cordados                         | 脊索动物门     |
| 2     | subphylum   | 355675   | Vertebrata     | Vertebrates                        | Vertebrados                      | 脊椎动物亚门   |
| 3     | class       | 40151    | Mammalia       | Mammals                            | Mamíferos                        | 哺乳纲         |
| 4     | subclass    | 848317   | Theria         | Therians                           | Marsupiales y placentarios       | 兽亚纲         |
| 5     | infraclass  | 848320   | Placentalia    | Placental Mammals                  | Placentarios                     | 胎盘动物       |
| 6     | superorder  | 848324   | Laurasiatheria | Ungulates, Carnivorans, and Allies | Venados, felinos y parientes     | 劳亚兽总目     |
| 7     | order       | 43327    | Perissodactyla | Odd-toed Ungulates                 | Caballos, tapires y rinocerontes | 奇蹄目         |
| 8     | family      | 43328    | Equidae        | Equids                             | Caballos, asnos y cebras         | 马科           |
| 9     | genus       | 43329    | Equus          | Horses, Asses, and Zebras          | Caballos, asnos y cebras         | 马属           |
| 10    | species     | 43335    | quagga         | Plains Zebra                       | Cebra de Sabana                  | 平原斑马       |
| 11    | subspecies  | 418151   | chapmani       | Chapman's Zebra                    | Cebra de Chapman                 | 查普曼斑马     |

---

`Accept-Language: en-US`
```json
{
    "taxonomy": [
        "Animalia",
        "Chordata",
        "Vertebrata",
        "Mammalia",
        "Theria",
        "Placentalia",
        "Laurasiatheria",
        "Perissodactyla",
        "Equidae",
        "Equus",
        "quagga",
        "chapmani"
    ],
    "taxonomy_rank_names": [
        "kingdom",
        "phylum",
        "subphylum",
        "class",
        "subclass",
        "infraclass",
        "superorder",
        "order",
        "family",
        "genus",
        "species",
        "subspecies"
    ],
    "taxonomy_common_names": [
        "Animals",
        "Chordates",
        "Vertebrates",
        "Mammals",
        "Therians",
        "Placental Mammals",
        "Ungulates, Carnivorans, and Allies",
        "Odd-toed Ungulates",
        "Equids",
        "Horses, Asses, and Zebras",
        "Plains Zebra",
        "Chapman's Zebra"
    ]
}
```

---

`Accept-Language: es-MX`
```json
{
    "taxonomy": [
        "Animalia",
        "Chordata",
        "Vertebrata",
        "Mammalia",
        "Theria",
        "Placentalia",
        "Laurasiatheria",
        "Perissodactyla",
        "Equidae",
        "Equus",
        "quagga",
        "chapmani"
    ],
    "taxonomy_rank_names": [
        "kingdom",
        "phylum",
        "subphylum",
        "class",
        "subclass",
        "infraclass",
        "superorder",
        "order",
        "family",
        "genus",
        "species",
        "subspecies"
    ],
    "taxonomy_common_names": [
        "Animales",
        "Cordados",
        "Vertebrados",
        "Mamíferos",
        "Marsupiales y placentarios",
        "Placentarios",
        "Venados, felinos y parientes",
        "Caballos, tapires y rinocerontes",
        "Caballos, asnos y cebras",
        "Caballos, asnos y cebras",
        "Cebra de Sabana",
        "Cebra de Chapman"
    ]
}
```

---

`Accept-Language: zh-CN`
```json
{
    "taxonomy": [
        "Animalia",
        "Chordata",
        "Vertebrata",
        "Mammalia",
        "Theria",
        "Placentalia",
        "Laurasiatheria",
        "Perissodactyla",
        "Equidae",
        "Equus",
        "quagga",
        "chapmani"
    ],
    "taxonomy_rank_names": [
        "kingdom",
        "phylum",
        "subphylum",
        "class",
        "subclass",
        "infraclass",
        "superorder",
        "order",
        "family",
        "genus",
        "species",
        "subspecies"
    ],
    "taxonomy_common_names": [
        "动物界",
        "脊索动物门",
        "脊椎动物亚门",
        "哺乳纲",
        "兽亚纲",
        "胎盘动物",
        "劳亚兽总目",
        "奇蹄目",
        "马科",
        "马属",
        "平原斑马",
        "查普曼斑马"
    ]
}
```

---

## Responsibilities

The Taxonomy Service is responsible for:

1. Loading `taxonomy.dwca.zip` data into a SQLite database.
2. Resolving the scientific lineage for each predicted taxon.
3. Resolving localized common names for each taxonomic rank.
4. When localized common names are unavailable, falling back gracefully to english, then scientific name.
5. Returning enriched prediction payloads for the API response.

## Architecture

### Taxonomy Importer

The `TaxonomyImporter` is responsible for downloading the archive, extracting the data, and loading it into a local SQLite database.

```sql
-- Table Schema TBD
```

By default only en-US common names will be imported. The `WILD_CATALOG_LANGUAGES` environment variable is a comma-separated list of ISO-639 language codes (just like an `Accept-Language` header). Refer to [vernacular_language_code_to_csv.py](../src/wild_catalog/taxonomy/vernacular_language_code_to_csv.py) for supported languages.

### Taxonomy Service

The `TaxonomyService` is the final processing step in the detection pipeline responsible for looking up the scientific name and a localized common name.
