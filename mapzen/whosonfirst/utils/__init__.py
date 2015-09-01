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

import mapzen.whosonfirst.placetypes

# this is only here for the generate_hierarchy stuff until we have
# a stable endpoint of some kind (21050807/thisisaaronland)

try:
    import urllib3
    urllib3.disable_warnings()

    logging.error("Disabled urllib3 warning, because guh...")

except Exception, e:
    logging.error("Failed to disable urllib3 warning, because %s" % e)

# these names are kind of stupid...
# (20150720/thisisaaronland)

def load(root, id, **kwargs):

    path = id2abspath(root, id, **kwargs)

    if not os.path.exists(path):
        raise Exception, "%s does not exist" % path

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

def generate_hierarchy(f):

    # sudo make me use py-mapzen-whosonfirst-spatial if possible
    # (21050807/thisisaaronland)

    hier = []

    props = f['properties']

    # sudo make me use 'diplay:lat,lon' or 'routing:lat,lon' once we
    # have them in the data... (20150810/thisisaaronland)

    if props.get('geom:latitude', False) and props.get('geom:longitude', False):
        lat = props['geom:latitude']
        lon = props['geom:longitude']
    else:
        geom = f['geometry']
        shp = shapely.geometry.asShape(geom)
        coords = shp.centroid
    
        lat = coords.y
        lon = coords.x

    placetype = mapzen.whosonfirst.placetypes.placetype(props['wof:placetype'])
    ancestors = placetype.ancestors()

    str_ancestors = ",".join(ancestors)

    try:
        params = {'latitude': lat, 'longitude': lon, 'placetype': str_ancestors}
        rsp = requests.get('https://54.148.56.3/', params=params, verify=False)
        data = json.loads(rsp.content)
    except Exception, e:
        logging.error(e)
        return []
        
    if len(data['features']) >= 1:

        for pf in data['features']:

            pp = pf['properties']
            
            for ph in pp.get('wof:hierarchy', []):

                for a in ancestors:
                    a_pid = "%s_id" % a

                    if not ph.get(a_pid, False):
                        ph[a_pid ] = -1

                this_pid = "%s_id" % str(placetype)
                this_id = props['wof:id']
                ph[this_pid] = this_id

                hier.append(ph)
                
    return hier

def crawl_with_callback(source, callback, **kwargs):

    iter = crawl(source, **kwargs)

    if kwargs.get('multiprocessing', False):

        import multiprocessing
        import signal

        def handler(signum, frame):
            logging.warning("Received interupt handler, exiting")
            sys.exit()

        signal.signal(signal.SIGINT, handler)

        processes = multiprocessing.cpu_count() * 2
        pool = multiprocessing.Pool(processes=processes)

        batch = []
        batch_size = kwargs.get('multiprocessing_batch_size', 1000)

        for rsp in iter:

            batch.append(rsp)

            if len(batch) >= batch_size:

                pool.map(callback, batch)
                batch = []

        if len(batch):
            pool.map(callback, batch)

    else:

        for rsp in iter:
            callback(rsp)
    
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
    
