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

    if kwargs.get('alt', False):
        return "%s-alt.geojson" % id
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

    for (root, dirs, files) in os.walk(source):

        for f in files:
            path = os.path.join(root, f)
            path = os.path.abspath(path)

            ret = path

            if not path.endswith('geojson'):
                continue

            # PLEASE FIX ME - ALLOW A WAY TO FILTER OUT alt GEOMETRIES
            # OR TO SPECIFY SOME/ONLY alt GEOMETRIES...
            # (20151216/thisisaaronland)

            if path.endswith('-alt.geojson'):
                continue

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
