#!/usr/bin/env python

from setuptools import setup, find_packages

packages = find_packages()
desc = open("README.md").read(),

setup(
    name='mapzen.whosonfirst.utils',
    namespace_packages=['mapzen', 'mapzen.whosonfirst', 'mapzen.whosonfirst.utils'],
    version='0.13',
    description='Simple Python wrapper for Who\'s On First helper functions',
    author='Mapzen',
    url='https://github.com/mapzen/py-mapzen-whosonfirst-utils',
    install_requires=[
        'mapzen.whosonfirst.placetypes>=0.07',
        'mapzen.whosonfirst.meta>=0.04',
        'requests',
        'shapely',
        'geojson',
        'boto',
        ],
    dependency_links=[
        'https://github.com/whosonfirst/py-mapzen-whosonfirst-placetypes/tarball/master#egg=mapzen.whosonfirst.placetypes-0.07',
        'https://github.com/whosonfirst/py-mapzen-whosonfirst-meta/tarball/master#egg=mapzen.whosonfirst.meta-0.04',
        ],
    packages=packages,
    scripts=[
        'scripts/wof-dump-concordances-local',
        'scripts/wof-dump-hierarchies',
        'scripts/wof-dump-superseded',
        'scripts/wof-concordances-to-db',
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
    download_url='https://github.com/mapzen/py-mapzen-whosonfirst-utils/releases/tag/v0.13',
    license='BSD')
