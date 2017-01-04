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
import types

import datetime
import copy

import inspect
import sys 
import signal
import multiprocessing
import hashlib

import mapzen.whosonfirst.placetypes
import mapzen.whosonfirst.meta
import mapzen.whosonfirst.uri

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

def hash_file(path):

    try:
        fh = open(path, "r")
    except Exception, e:
        logging.error("failed to open %s for hashing, because %s" % (path, e))
        return None

    hash = hashlib.md5()
    hash.update(fh.read())
    
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

    if type(root) in (types.ListType, types.TupleType) :

        path = None

        for r in root:

            p = mapzen.whosonfirst.uri.id2abspath(r, id, **kwargs)

            if not os.path.exists(p):
                logging.debug("%s does not exist" % p)
                continue

            path = p
            break

    else:

        stack = inspect.stack()[1]
        file = stack[1]
        line = stack[2]
        func = stack[3]

        caller = "caller %s (%s at ln%s)" % (func, file, line)
        logging.debug("%s is invoking 'mapzen.whosonfirst.utils.load' in not-a-list context"% caller)

        path = mapzen.whosonfirst.uri.id2abspath(root, id, **kwargs)

    if not path or not os.path.exists(path):
        logging.error("unable to locate path for %s (%s)" % (id, root))
        raise Exception, "unable to locate path for %s (%s)" % (id, root)

    return load_file(path)

def load_file(path):
    fh = open(path, 'r')
    return geojson.load(fh)

# DEPRECATED

def id2fqpath(root, id, **kwargs):
    logging.warning("deprecated use of id2fqpath, please use id2abspath")

    return mapzen.whosonfirst.uri.id2abspath(root, id, **kwargs)

# DEPRECATED

def id2abspath(root, id, **kwargs):

    return mapzen.whosonfirst.uri.id2abspath(root, id, **kwargs)

# DEPRECATED

def id2relpath(id, **kwargs):

    return mapzen.whosonfirst.uri.id2relpath(id, **kwargs)

# DEPRECATED

def id2fname(id, **kwargs):

    return mapzen.whosonfirst.uri.id2fname(id, **kwargs)

# DEPRECATED

def id2path(id):

    return mapzen.whosonfirst.uri.id2path(id)

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

    inflate = kwargs.get('inflate', False)

    for (root, dirs, files) in os.walk(source):

        for f in files:

            path = os.path.join(root, f)
            path = os.path.abspath(path)

            ret = ensure_valid_wof(path, **kwargs)

            if not ret:
                continue

            yield ret

# this wraps ensure_valid_wof and returns True or False

def is_valid_wof(path, **kwargs):

    ret = ensure_valid_wof(path, **kwargs)

    if not ret:
        return False

    return True

# this returns None or a path or a GeoJSON blob

def ensure_valid_wof(path, **kwargs):

    validate = kwargs.get('validate', False)
    inflate = kwargs.get('inflate', False)

    ensure = kwargs.get('ensure_placetype', [])
    skip = kwargs.get('skip_placetype', [])

    is_wof = re.compile(r"^(\d+)(?:-([a-z0-9\-]+))?$")

    path = os.path.abspath(path)
    parsed = parse_filename(path)

    if not parsed:
        return None

    id, suffix = parsed

    # Hey look we're dealing with an alt file of some kind!

    if suffix != None:

        if not kwargs.get('include_alt', False) and not kwargs.get('require_alt', False):
            return None

        # TO DO - filter on specific suffixes...
        # (20151216/thisisaaronland)

    else:

        if kwargs.get('require_alt', False):
            return None

    # OKAY... let's maybe do something?

    ret = path

    if validate or inflate or len(skip) or len(ensure):

        try:
            fh = open(path, 'r')
            data = geojson.load(fh)

        except Exception, e:
            logging.error("failed to load %s, because %s" % (path, e))
            return None

        if len(ensure):

            props = data['properties']
            pt = props.get('wof:placetype', None)

            if not pt in ensure:
                logging.debug("skipping %s because it is a %s" % (path, pt))
                return None

            elif len(skip):

                props = data['properties']
                pt = props.get('wof:placetype', None)

                if pt in skip:
                    logging.debug("skipping %s because it is a %s" % (path, pt))
                    return None

                if not pt:
                    logging.error("can not determine placetype for %s" % path)

        ret = data

    return ret

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

        hash_ymd = hash_file(path_ymd)
        hash_latest = hash_file(path_latest)

        if hash_ymd == hash_latest:

            created = []
            modified = []

        else:
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

# PLEASE MOVE ME OUT OF py-mz-wof-utils (20161221/thisisaaronland)

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

        placetype = props.get('wof:placetype', None)

        if not placetype:

            e = "%s is missing a placetype!" % path

            logging.error(e)
            raise Exception, e

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

        root = os.path.dirname(meta)

        fname = os.path.basename(root)
        fname = fname.split("-")

        if len(fname) > 2:
            placetype = "-".join(fname[2:])

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

        # https://github.com/whosonfirst/py-mapzen-whosonfirst-utils/issues/9
        # ./scripts/wof-placetype-to-csv -s /usr/local/data/whosonfirst-data/data -p PLACETYPE -c /usr/local/data/whosonfirst-data/meta

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

def supersede_feature(old_feature, **kwargs):

    new_feature = copy.deepcopy(old_feature)
    
    old_props = old_feature['properties']
    new_props = new_feature['properties']

    old_id = old_props['wof:id']
    new_id = generate_id()

    new_props['wof:id'] = new_id

    if not old_id in new_props['wof:supersedes']:
        new_props['wof:supersedes'].append(old_id)

    if not new_id in old_props['wof:superseded_by']:
        old_props['wof:superseded_by'].append(new_id)

    now = datetime.datetime.now()
    ymd = now.strftime("%Y-%m-%d")
    
    old_props['edtf:superseded'] = ymd

    old_feature['properties'] = old_props
    new_feature['properties'] = new_props

    if kwargs.get('placetype', None):
        new_props['wof:placetype'] = kwargs['placetype']
        new_feature['properties'] = new_props

    return old_feature, new_feature
