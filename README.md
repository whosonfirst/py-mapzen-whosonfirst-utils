# py-mapzen-gazetteer

## Usage

Please write me

## Command line tools

### mzg-placetype-to-csv

Dump all the records matching a specific placetype to a CSV file:

```
$> /usr/local/bin/mzg-placetype-to-csv --source /usr/local/mapzen/gazetteer --place-type country  --csv /usr/local/mapzen/mzg-country.csv
```

Which would produce something like this:

```
85632161,Macao S.A.R,quattroshapes,856/321/61/85632161.geojson
85632163,Guam,quattroshapes,856/321/63/85632163.geojson
85632167,Bahrain,quattroshapes,856/321/67/85632167.geojson
85632169,United States Virgin Islands,quattroshapes,856/321/69/85632169.geojson
85632171,Bhutan,quattroshapes,856/321/71/85632171.geojson
```

### mzg-csv-to-feature-collection

Combine all the records in a CSV file (produced by `mzg-placetype-to-csv`) in to a single GeoJSON feature collection:

```
/usr/local/bin/mzg-csv-to-feature-collection --source /usr/local/mapzen/gazetteer --csv /usr/local/mapzen/mzg-country.csv --out mzg-country.geojson
```

Which you could then hand off to something like `ogr2ogr`:

```
or2ogr -F 'ESRI Shapefile' mzg-country.shp mzg-country.geojson
```

Which you could then load in to something like the [flickrgeocoder-java](https://github.com/thisisaaronland/flickrgeocoder-java) reverse-geocoder:

```
$> PORT=5000 java -Xmx384m -cp 'target/classes:target/dependency/*' com.hackdiary.geo.FlickrGeocodeServlet mzg-country.geojson
```

But really that's your business...

## Known knowns

* The `mzg-placetype-to-csv` tool does not produce (and the `mzg-csv-to-feature-collection` tool does not expect) CSV files with headers.

* The `mzg-csv-to-feature-collection` tools needs to be taught how to produce multiple GeoJSON files containing a maximum number of features.

## See also

* [py-mapzen-gazetteer-export](https://github.com/mapzen/py-mapzen-gazetteer-export)
