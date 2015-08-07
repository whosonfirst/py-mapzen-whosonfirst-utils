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

        hier = []

        props = f['properties']

        geom = feature['geometry']
        shp = shapely.geometry.asShape(geom)
        coords = shp.centroid

        lat = coords.y
        lon = coords.x

        # this assumes a copy of py-mapzen-whosonfirst-lookup with
        # recursive get_by_latlon (20150728/thisisaaronland)

        placetype = ('neighbourhood', 'locality', 'region', 'country', 'continent')
        placetype = ",".join(placetype)

        try:
            params = {'latitude': lat, 'longitude': lon, 'placetype': placetype}
            rsp = requests.get('https://54.148.56.3/', params=params, verify=False)
                
            data = json.loads(rsp.content)
        except Exception, e:
            logging.error(e)
            return

        if len(data['features']) == 1:
            props['wof:parent_id'] = data['features'][0]['id']

        if len(data['features']) >= 1:

            for pf in data['features']:
                pp = pf['properties']

                if pp.get('wof:hierarchy', False):
                    hier.extend(pp['wof:hierarchy'])

        return hier

        """
        props['wof:hierarchy'] = hier
        f['properties'] = props
        """

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
    
