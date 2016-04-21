#!/usr/bin/env python

# Remove .egg-info directory if it exists, to avoid dependency problems with
# partially-installed packages (20160119/dphiffer)

import os, sys
from shutil import rmtree

cwd = os.path.dirname(os.path.realpath(sys.argv[0]))
egg_info = cwd + "/mapzen.whosonfirst.utils.egg-info"
if os.path.exists(egg_info):
    rmtree(egg_info)

from setuptools import setup, find_packages

packages = find_packages()
version = open("VERSION").read()
desc = open("README.md").read()

setup(
    name='mapzen.whosonfirst.utils',
    namespace_packages=['mapzen', 'mapzen.whosonfirst', 'mapzen.whosonfirst.utils'],
    version=version,
    description='Simple Python wrapper for Who\'s On First helper functions',
    author='Mapzen',
    url='https://github.com/whosonfirst/py-mapzen-whosonfirst-utils',
    install_requires=[
        'mapzen.whosonfirst.placetypes>=0.11',
        'mapzen.whosonfirst.meta>=0.8',
        'requests',
        'shapely',
        'geojson',
        'boto',
        'atomicwrites',
        ],
    dependency_links=[
        'https://github.com/whosonfirst/py-mapzen-whosonfirst-placetypes/tarball/master#egg=mapzen.whosonfirst.placetypes-0.11',
        'https://github.com/whosonfirst/py-mapzen-whosonfirst-meta/tarball/master#egg=mapzen.whosonfirst.meta-0.8',
        ],
    packages=packages,
    scripts=[
        'scripts/wof-check-etags',
        'scripts/wof-dump-concordances-local',
        'scripts/wof-dump-hierarchies',
        'scripts/wof-dump-superseded',
        'scripts/wof-concordances-to-db',
        'scripts/wof-filter-meta',
        'scripts/wof-id2git',
        'scripts/wof-inventory-properties',
        'scripts/wof-placetype-to-csv',
        'scripts/wof-placetype-to-csv-atomic',
        'scripts/wof-promote-geometry',
        'scripts/wof-properties',
        'scripts/wof-csv-to-feature-collection',
        'scripts/wof-csv-to-s3',
        'scripts/wof-mk-place',
        'scripts/wof-supersede',
        ],
    download_url='https://github.com/whosonfirst/py-mapzen-whosonfirst-utils/releases/tag/' + version,
    license='BSD')
