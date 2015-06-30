# py-mapzen-gazetteer

```
Brett
what about the gazetteer? needs a name

Aaron
can we call it "knutzen" or would that be weird?

Brett
it does have zen in it
```
## Install

Depending on which version of rage-making Python or more likely the rage-making-er `setuptools` you may need to expicitly tell the install script to put the command line tools in `/usr/local/bin` like this:

```
sudo python ./setup.py install --install-scripts /usr/local/bin
```

## Usage

_Please write me_

## Command line tools

### mzg-placetype-to-csv

Dump all the records matching a specific placetype to a CSV file:

```
$> /usr/local/bin/mzg-placetype-to-csv --source /usr/local/mapzen/gazetteer --place-type country  --csv /usr/local/mapzen/mzg-country.csv
```

Which would produce something like this:

```
id,name,source,path
85632161,Macao S.A.R,quattroshapes,856/321/61/85632161.geojson
85632163,Guam,quattroshapes,856/321/63/85632163.geojson
85632167,Bahrain,quattroshapes,856/321/67/85632167.geojson
85632169,United States Virgin Islands,quattroshapes,856/321/69/85632169.geojson
85632171,Bhutan,quattroshapes,856/321/71/85632171.geojson
```

### mzg-csv-to-feature-collection

Combine all the records in a CSV file (produced by `mzg-placetype-to-csv`) in to a single GeoJSON feature collection:

```
$> /usr/local/bin/mzg-csv-to-feature-collection --source fs --prefix /usr/local/mapzen/gazetteer --csv /usr/local/mapzen/mzg-country.csv --out mzg-country.geojson
```

You can also fetch things stored on a (public) S3 bucket:

```
$> /usr/local/bin/mzg-csv-to-feature-collection --source s3 --prefix http://com.mapzen.gazetteer.s3.amazonaws.com --csv /usr/local/mapzen/mzg-country.csv --out mzg-country.geojson
```

Which you could then hand off to something like `ogr2ogr`:

```
$> ogr2ogr -F 'ESRI Shapefile' mzg-country.shp mzg-country.geojson
```

Which you could then load in to something like the [flickrgeocoder-java](https://github.com/thisisaaronland/flickrgeocoder-java) reverse-geocoder:

```
$> PORT=5000 java -Xmx384m -cp 'target/classes:target/dependency/*' com.hackdiary.geo.FlickrGeocodeServlet mzg-country.geojson
```

But really that's your business...

You can limit the number of records in a GeoJSON file by passing the `--max` flag. For example:

```
$> /usr/local/mapzen/py-mapzen-gazetteer/scripts/mzg-csv-to-feature-collection --source fs --prefix /usr/local/mapzen/gazetteer-local --csv /usr/local/mapzen/gazetteer-local/meta/mzg-locality-latest.csv --max 50000 --out /usr/local/mapzen/gazetteer-bundles/locality/locality.geojson --verbose
```

Which would produce something like this:

```
ll ../gazetteer-bundles/locality/*.geojson
-rw-r--r-- 1 ubuntu ubuntu 457624245 Jun 30 18:41 ../gazetteer-bundles/locality/locality-1.geojson
-rw-r--r-- 1 ubuntu ubuntu 183653688 Jun 30 18:41 ../gazetteer-bundles/locality/locality-2.geojson
-rw-r--r-- 1 ubuntu ubuntu 232375434 Jun 30 18:41 ../gazetteer-bundles/locality/locality-3.geojson
-rw-r--r-- 1 ubuntu ubuntu  44981632 Jun 30 18:41 ../gazetteer-bundles/locality/locality-4.geojson
```

### mzg-cvs-to-s3

Copy the files listed in an CSV file – produced by `mzg-placetype-to-csv` or similar – to an S3 bucket:

```
/usr/local/bin/mzg-csv-to-s3 --source /usr/local/mapzen/gazetteer --csv /usr/local/mapzen/mzg-region-20150625.csv --bucket com.mapzen.gazetteer --config aws.cfg --meta
```

Note the `--meta` flag. This will also copy the CSV file in question to a `meta` folder in the S3 bucket.

## For example

### bundle-placetype.sh

```
#!/bin/sh

TYPE=$1
YMD=`date "+%Y%m%d"`

SOURCE=/usr/local/mapzen/gazetteer-local
META=${SOURCE}/meta
BUNDLE=${SOURCE}/bundle

CSV_CURRENT=${META}/mzg-${TYPE}-${YMD}.csv
CSV_LATEST=${META}/mzg-${TYPE}-latest.csv

GEOJSON=/usr/local/mapzen/gazetteer-bundles/${TYPE}/${TYPE}.geojson
SHAPEFILE=/usr/local/mapzen/gazetteer-bundles/${TYPE}/${TYPE}.shp

ROOT=`dirname ${GEOJSON}`

if [ ! -d ${ROOT} ]
then
    mkdir ${ROOT}
fi

echo "generate CSV bundle for ${TYPE} - ${CSV_CURRENT}"
/usr/local/bin/mzg-placetype-to-csv --source ${SOURCE} --place-type ${TYPE} --csv ${CSV_CURRENT}
cp ${CSV_CURRENT} ${CSV_LATEST}

echo "remove old GeoJSON files for ${TYPE}"

for GEOJSON in `ls -a ${ROOT}/*.geojson`
do
    echo "remove ${GEOJSON}"
    rm ${GEOJSON}
done

echo "generate feature collection for ${TYPE} - ${GEOJSON}"
/usr/local/bin/mzg-csv-to-feature-collection --source fs --prefix ${SOURCE} --csv ${CSV_CURRENT} --out ${GEOJSON} --max 50000

echo "generate shapefiles for ${TYPE}"

for GEOJSON in `ls -a ${ROOT}/*.geojson`
do
    SHAPEFILE=`echo ${GEOJSON} | awk -F '.geojson' '{ print $1 }'`
    SHAPEFILE="${SHAPEFILE}.shp"

    echo "generate shapefile for ${TYPE} - ${SHAPEFILE}"
    ogr2ogr -overwrite -F 'ESRI Shapefile' ${SHAPEFILE} ${GEOJSON}
done

echo "all done"
exit 0;

```

## Known knowns

* The `mzg-csv-to-s3` tool does not overwrite files or offer any logic for comparing two files.

## See also

* [py-mapzen-gazetteer-export](https://github.com/mapzen/py-mapzen-gazetteer-export)
