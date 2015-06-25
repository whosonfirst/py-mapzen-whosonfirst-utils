# py-mapzen-gazetteer

## Usage

Please write me

## Command line tools

### mzg-placetype-to-csv

Dump all the records matching a specific placetype to a CSV file.

```
$> /usr/local/bin/mzg-placetype-to-csv --source /usr/local/mapzen/gazetteer --place-type country  --csv /usr/local/mapzen/mzg-country.csv
```

### mzg-csv-to-feature-collection

Combine all the records in a CSV file (produced by `mzg-placetype-to-csv`) in to a single GeoJSON feature collection.

```
/usr/local/bin/mzg-csv-to-feature-collection --source /usr/local/mapzen/gazetteer --csv /usr/local/mapzen/mzg-country.csv --out mzg-country.geojson
```

Which you could then hand off to something like `ogr2ogr`.

```
or2ogr -F 'ESRI Shapefile' mzg-country.shp mzg-country.geojson
```

Which you could then load in to something like the [flickrgeocoder-java](https://github.com/thisisaaronland/flickrgeocoder-java) reverse-geocoder.

```
$> PORT=5000 java -Xmx384m -cp 'target/classes:target/dependency/*' com.hackdiary.geo.FlickrGeocodeServlet mzg-country.geojson
```

But really that's your business...
