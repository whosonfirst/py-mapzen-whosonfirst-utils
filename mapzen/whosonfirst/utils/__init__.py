# https://pythonhosted.org/setuptools/setuptools.html#namespace-packages
__import__('pkg_resources').declare_namespace(__name__)

import shapely.geometry
import requests
import geojson
import json
import os
import os.path
import logging
import re
import time
import shutil

import sys 
import signal
import multiprocessing
import hashlib

import mapzen.whosonfirst.placetypes
import mapzen.whosonfirst.meta

# used by the update concordances stuff so it will probably
# be moved in to its own package shortly

import atomicwrites
import csv

# used in parse_filename
pat_wof = re.compile(r"^(\d+)(?:-([a-z0-9\-]+))?$")

def hash_geom(f):

    geom = f['geometry']
    geom = json.dumps(geom)
    
    hash = hashlib.md5()
    hash.update(geom)
    return hash.hexdigest()

def is_valid_latitude(lat):
    lat = float(lat)

    if lat < -90.0:
        return False

    if lat > 90.0:
        return False

    return True

def is_valid_longitude(lon):
    lon = float(lon)

    if lon < -180.0:
        return False

    if lon > 180.0:
        return False

    return True

# these names are kind of stupid...
# (20150720/thisisaaronland)

def load(root, id, **kwargs):

    path = id2abspath(root, id, **kwargs)

    if not os.path.exists(path):
        raise Exception, "%s does not exist" % path

    return load_file(path)

def load_file(path):
    fh = open(path, 'r')
    return geojson.load(fh)

def id2fqpath(root, id, **kwargs):
    logging.warning("deprecated use of id2fqpath, please use id2abspath")
    return id2abspath(root, id, **kwargs)

def id2abspath(root, id, **kwargs):

    rel = id2relpath(id, **kwargs)

    path = os.path.join(root, rel)
    return path

def id2relpath(id, **kwargs):

    fname = id2fname(id, **kwargs)
    parent = id2path(id)

    path = os.path.join(parent, fname)
    return path

def id2fname(id, **kwargs):

    # See this. It doesn't really allow for new "alternate" names
    # to be added. For example a bespoke reverse geocoding polygon.
    # That's not ideal but it's also by design to force us to
    # actually think about what/how we want to do that...
    # (20151217/thisisaaronland)

    alt = kwargs.get('alt', None)
    display = kwargs.get('display', None)

    if alt:
        return "%s-alt-%s.geojson" % (id, alt)
    elif display:
        return "%s-display-%s.geojson" % (id, display)
    else:
        return "%s.geojson" % id

def id2path(id):

    tmp = str(id)
    parts = []
    
    while len(tmp) > 3:
        parts.append(tmp[0:3])
        tmp = tmp[3:]

    if len(tmp):
        parts.append(tmp)

    return "/".join(parts)

def generate_id():

    url = 'http://api.brooklynintegers.com/rest/'
    params = {'method':'brooklyn.integers.create'}

    try :
        rsp = requests.post(url, params=params)    
        data = rsp.content
    except Exception, e:
        logging.error(e)
        return 0
    
    try:
        data = json.loads(data)
    except Exception, e:
        logging.error(e)
        return 0
    
    return data.get('integer', 0)

def ensure_bbox(f):

    if not f.get('bbox', False):
        geom = f['geometry']
        shp = shapely.geometry.asShape(geom)
        f['bbox'] = list(shp.bounds)

def crawl_with_callback(source, callback, **kwargs):

    iter = crawl(source, **kwargs)

    if kwargs.get('multiprocessing', False):

        processes = multiprocessing.cpu_count() * 2
        pool = multiprocessing.Pool(processes=processes)

        def sigint_handler(signum, frame):
            logging.warning("Received interupt handler (in crawl_with_callback scope) so exiting")
            pool.terminate()
            sys.exit()

        signal.signal(signal.SIGINT, sigint_handler)

        batch = []
        batch_size = kwargs.get('multiprocessing_batch_size', 1000)

        for rsp in iter:

            batch.append((callback, rsp))

            if len(batch) >= batch_size:

                pool.map(_callback_wrapper, batch)
                batch = []

        if len(batch):
            pool.map(_callback_wrapper, batch)

    else:

        for rsp in iter:
            callback(rsp)

# Dunno - python seems all sad and whingey if this gets defined in
# the (crawl_with_callback) scope above so whatever...
# (20150902/thisisaaronland)

def _callback_wrapper(args):

    callback, feature = args

    try:
        callback(feature)
    except KeyboardInterrupt:
        logging.warning("Received interupt handler (in callback wrapper scope) so exiting")
    except Exception, e:
        logging.error("Failed to process feature because %s" % e)
        raise Exception, e
    
def crawl(source, **kwargs):

    validate = kwargs.get('validate', False)
    inflate = kwargs.get('inflate', False)

    ensure = kwargs.get('ensure_placetype', [])
    skip = kwargs.get('skip_placetype', [])

    is_wof = re.compile(r"^(\d+)(?:-([a-z0-9\-]+))?$")

    for (root, dirs, files) in os.walk(source):

        for f in files:

            path = os.path.join(root, f)
            path = os.path.abspath(path)

            ret = path

            parsed = parse_filename(path)

            if not parsed:
                continue
                           
            id, suffix = parsed

            # Hey look we're dealing with an alt file of some kind!

            if suffix != None:

                if not kwargs.get('include_alt', False) and not kwargs.get('require_alt', False):
                    continue

                # TO DO - filter on specific suffixes...
                # (20151216/thisisaaronland)

            else:

                if kwargs.get('require_alt', False):
                    continue

            # OKAY... let's maybe do something?

            if validate or inflate or len(skip) or len(ensure):

                try:
                    fh = open(path, 'r')
                    data = geojson.load(fh)

                except Exception, e:
                    logging.error("failed to load %s, because %s" % (path, e))
                    continue

                if len(ensure):

                    props = data['properties']
                    pt = props.get('wof:placetype', None)

                    if not pt in ensure:
                        logging.debug("skipping %s because it is a %s" % (path, pt))
                        continue

                elif len(skip):

                    props = data['properties']
                    pt = props.get('wof:placetype', None)

                    if pt in skip:
                        logging.debug("skipping %s because it is a %s" % (path, pt))
                        continue

                    if not pt:
                        logging.error("can not determine placetype for %s" % path)

                if not inflate:
                    ret = path
                else:
                    ret = data

            yield ret

def update_concordances_metafile(meta, to_process, **kwargs):

    # raise Exception, "Y U WHAT????"

    modified = []
    created = []

    now = time.gmtime()
    ymd = time.strftime("%Y%m%d", now)

    fname_ymd = "wof-concordances-%s.csv" % ymd
    fname_latest = "wof-concordances-latest.csv"

    path_ymd = os.path.join(meta, fname_ymd)
    path_latest = os.path.join(meta, fname_latest)

    source_meta = path_latest		# what we're reading from (looking for changes)
    dest_meta = path_ymd		# what we're writing to

    if os.path.exists(path_ymd):
        source_meta = path_ymd
        modified.append(path_ymd)
    else:
        created.append(path_ymd)

    if os.path.exists(path_latest):
        modified.append(path_latest)
    else:
        created.append(path_latest)

    if not os.path.exists(source_meta):

        # See this - we are leaving it to the caller to figure out what
        # to do in this instance. That is maybe not the correct approach
        # but it will do for now.

        modified = None
        created = None

        # In order to generate concordances from scratch this is what we
        # used to (can still) do:
        #
        # /usr/local/bin/wof-dump-concordances -v -e 'sg:id' -c /usr/local/mapzen/whosonfirst.cfg -o /usr/local/mapzen/whosonfirst-data/meta -l

        # And this is the new new because it's about a billion times faster.
        # Note that YMD is a placeholder for `date +"%Y%m%d"`
        #
        # /usr/local/mapzen/go-wof-concordances/bin/wof-concordances-write -processes 200 -source /usr/local/mapzen/whosonfirst-data/data > /usr/local/mapzen/whosonfirst-data/meta/wof-concordances-YMD.csv
        # cp /usr/local/mapzen/whosonfirst-data/meta/wof-concordances-YMD.csv /usr/local/mapzen/whosonfirst-data/meta/wof-concordances-latest.csv

        logging.error("Unable to find source file for concordances, expected %s BUT IT'S NOT THERE" % source_meta)

    else:

        __update_concordances(source_meta, dest_meta, to_process, **kwargs)

        logging.info("copy %s to %s" % (path_ymd, path_latest))
        shutil.copy(path_ymd, path_latest)

    return (modified, created)

# stub while I decideif this should live in py-mz-wof-concordances

def __update_concordances(source, dest, to_process, **kwargs):
    
    to_update = {}

    source_fh = open(source, 'r')
    reader = csv.reader(source_fh)

    # First figure out the columns we've got

    cols = reader.next()

    # Next check to see if there are any new ones

    # Note that this does NOT attempt to check and see whether the files
    # in to_process actually have modified concordances. That is still not
    # a solved problem but beyond that it is a problem to solve elsewhere
    # in the stack. This assumes that by the time you pass a list of files
    # you've satisfied yourself that it's worth the processing time (not to
    # mention memory) to fill up `to_update` for all the files listed in
    # to_update. (20160107/thisisaaronland)

    for path in to_process:

        path = os.path.abspath(path)
        feature = mapzen.whosonfirst.utils.load_file(path)

        props = feature['properties']
        wofid = props['wof:id']

        concordances = props['wof:concordances']
        to_update[ wofid ] = concordances

        for src in concordances.keys():

            if not src in cols:
                cols.append(src)

    cols.sort()

    # Rewind the source concordances file so that we can create a dict reader

    source_fh.seek(0)
    reader = csv.DictReader(source_fh)

    writer = None

    with atomicwrites.atomic_write(dest, mode='wb', overwrite=True) as dest_fh:

        for row in reader:

            if not writer:
                writer = csv.DictWriter(dest_fh, fieldnames=cols)
                writer.writeheader()

            # See what we're doing here? If this is a record that's been
            # updated (see above for the nuts and bolts about how/where
            # we determine this) then we reassign it to `row`.

            wofid = row.get('wof:id')
            wofid = int(wofid)

            if to_update.get(wofid, False):
                row = to_update[wofid]
                row['wof:id'] = wofid

            out = {}

            # Esnure we have a value or "" for every src in cols

            for src in cols:
                out[ src ] = row.get(src, "")

            writer.writerow(out)

# so that it can be invoked from both a CLI tool and from a git pre-commit hook
# (20151111/thisisaaronland)

def update_placetype_metafiles(meta, updated, **kwargs):

    modified = []
    created = []

    now = time.gmtime()
    ymd = time.strftime("%Y%m%d", now)
    
    to_rebuild = {}

    # first plow through the available updates and sort them
    # by placetype

    for path in updated:

        path = os.path.abspath(path)

        feature = load_file(path)
        props = feature['properties']

        placetype = props['wof:placetype']
        
        to_process = to_rebuild.get(placetype, [])
        to_process.append(path)

        to_rebuild[placetype] = to_process

    # now update each placetype meta file one at a time first checking to
    # see if there is an existing (YMD) meta file or if we should just start
    # with the "latest" version

    for placetype, to_process in to_rebuild.items():

        count = len(to_process)

        if count == 1:
            logging.info("rebuild meta file for placetype %s with one update" % placetype)
        else:
            logging.info("rebuild meta file for placetype %s with %s updates" % (placetype, count))

        fname_ymd = "wof-%s-%s.csv" % (placetype, ymd)
        fname_latest = "wof-%s-latest.csv" % placetype

        path_ymd = os.path.join(meta, fname_ymd)
        path_latest = os.path.join(meta, fname_latest)

        source_meta = path_latest
        dest_meta = path_ymd

        if os.path.exists(path_ymd):
            source_meta = path_ymd
            modified.append(path_ymd)
        else:
            created.append(path_ymd)

        if os.path.exists(path_latest):
            modified.append(path_latest)
        else:
            created.append(path_latest)

        if not os.path.exists(source_meta):
            logging.error("Unable to find source file for %s, expected %s BUT IT'S NOT THERE" % (placetype, source_meta))
            continue

        mapzen.whosonfirst.meta.update_metafile(source_meta, dest_meta, to_process, **kwargs)

        logging.info("copy %s to %s" % (path_ymd, path_latest))
        shutil.copy(path_ymd, path_latest)

    return (modified, created)

def parse_filename(path):

    fname = os.path.basename(path)
    fname, ext = os.path.splitext(fname)

    if ext != ".geojson":
        return None

    m = re.match(pat_wof, fname)

    if not m:
        return None
              
    id, suffix = m.groups()

    return (id, suffix)
