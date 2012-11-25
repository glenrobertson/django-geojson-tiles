++++++++++++++++++++
Django GeoJSON Tiles
++++++++++++++++++++
A simple Django view to serve GeoJSON tiles from a GeoDjango model

Description
===========

The view will return a GeoJSON FeatureCollection for each tile.
Each feature corresponds to a row of the model.

Setup
=====

::

        pip install django-geojson-tiles

Add the following to your urls.py:

::

        from geojson_tiles.views import GeoJSONTile
        from your_app import GeometryModel

        urlpatterns = patterns('',
            url(r'^your_endpoint/(?P<z>\d+)/(?P<x>\d+)/(?P<y>\d+).json$', 
                GeoJSONTile(GeometryModel, 'geometry_field', trim_to_boundary=True))
        )

Notes
=====
1. ``trim_to_boundary=True`` will result in GeoJSON tiles with geometries trimmed to the tile boundary
2. ``properties=[...]`` can be used to limit the feature's properties that are serialized
