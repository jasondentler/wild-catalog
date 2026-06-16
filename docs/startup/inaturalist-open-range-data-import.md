# iNaturalist Open Range Data Import

The process imports [iNaturalist Open Range Map datasets](https://www.inaturalist.org/pages/range_maps) into a local SQLite database.

## Technical Specification

The process is initiated on application startup.

The entire dataset is split across several Geopackage (.gpkg) files and referenced by the [metadata.json](https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest/metadata.json).

### Calculating Geopackage Urls

A snippet of **metadata.json:**

```json
{
  "version": "2.31",
  "ranges": 118632,
  "collections": {
    "OtherAnimalia": {
      "ranges": 4462,
      "archives": 1
    },
    "Aves": {
      "ranges": 6822,
      "archives": 2
    },
    "Amphibia": {
      "ranges": 1599,
      "archives": 1
    },
    ...
  }
}
```

Resulting Geopackage files:

**OtherAnimalia** (Other Animals)

* [iNaturalist_geomodel_OtherAnimalia.gpkg](https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest/iNaturalist_geomodel_OtherAnimalia.gpkg)

**Aves** (Birds)

* [iNaturalist_geomodel_Aves_1.gpkg](https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest/iNaturalist_geomodel_Aves_1.gpkg)
* [iNaturalist_geomodel_Aves_2.gpkg](https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest/iNaturalist_geomodel_Aves_2.gpkg)

**Amphibia** (Amphibians)

* [iNaturalist_geomodel_Amphibia.gpkg](https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest/iNaturalist_geomodel_Amphibia.gpkg)

etc.

Here's the logic to build the urls:

```javascript
export async function calculate_geopackage_urls() {
    const baseUrl = "https://inaturalist-open-data.s3.us-east-1.amazonaws.com/geomodel/geopackages/latest"
    const metadataUrl = `${baseUrl}/metadata.json`

    $.getJSON(metadataUrl, function(json) {
        Object.keys(json.collections).forEach(key => {
            const collection = json.collections[key];
            const baseUrl = ``;
            
            for (let i = 0; i < collection.archives; i++) {
                const suffix = collection.archives > 1 ? `_${i + 1}` : "";
                const url = `${baseUrl}/iNaturalist_geomodel_${key}${suffix}.gpkg`;
                
                console.log(url);
            }
        });
    });
}
```

### Database Schema

The SQLite database schema is as follows:

```sql
CREATE TABLE range_geometries (
    id INTEGER PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    min_lon REAL NOT NULL,
    min_lat REAL NOT NULL,
    max_lon REAL NOT NULL,
    max_lat REAL NOT NULL,
    geometry_wkb BLOB NOT NULL
);

CREATE VIRTUAL TABLE range_geometries_rtree USING rtree(
    id,
    min_lon,
    max_lon,
    min_lat,
    max_lat
);

CREATE INDEX idx_range_geometries_taxon_id
ON range_geometries (taxon_id);

CREATE TABLE range_store_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### Import Processing

Loop through all the `.gpkg` files from [Calculating Geopackage Urls](#calculating-geopackage-urls) above.

Attach the `.gpkg` file, which is actually a SQLite database using an `ATTACH DATABASE` command. You will 
also need to replace `iNaturalist_geomodel_Amphibia` and `rtree_iNaturalist_geomodel_Amphibia_geom` table 
names dynamically, depending on which gpkg file you are processing. 

```sql
PRAGMA journal_mode = WAL; -- Write-Ahead Log for faster insertions
PRAGMA synchronous = NORMAL; -- Offloads sync checks safely
PRAGMA cache_size = -100000; -- Allocates ~100MB RAM for database cache lookup

-- 1. Attach your GeoPackage file to the current session
ATTACH DATABASE 'iNaturalist_geomodel_Amphibia.gpkg' AS gpkg_db;

-- 2. Migrate the main data table and parse the binary geometry
INSERT INTO range_geometries (
    taxon_id,
    min_lon,
    min_lat,
    max_lon,
    max_lat,
    geometry_wkb
)
SELECT 
    CAST(d.taxon_id AS INTEGER),
    r.minx,
    r.miny,
    r.maxx,
    r.maxy,
    -- Trims the GeoPackage header to yield pure standard WKB
    CASE 
        WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 0 THEN SUBSTR(d.geom, 9)
        WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 2 THEN SUBSTR(d.geom, 41)
        WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 4 THEN SUBSTR(d.geom, 57)
        WHEN (unicode(substr(d.geom, 4, 1)) & 14) = 6 THEN SUBSTR(d.geom, 57)
        ELSE SUBSTR(d.geom, 73)
    END
FROM gpkg_db.iNaturalist_geomodel_Amphibia d
JOIN gpkg_db.rtree_iNaturalist_geomodel_Amphibia_geom r ON d.fid = r.id;

-- 3. Populate your target virtual R-Tree index
INSERT INTO range_geometries_rtree (id, min_lon, max_lon, min_lat, max_lat)
SELECT id, min_lon, max_lon, min_lat, max_lat 
FROM range_geometries;

-- 4. Clean up connection
DETACH DATABASE gpkg_db;
```