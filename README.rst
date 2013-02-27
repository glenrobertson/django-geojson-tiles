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
                GeoJSONTile(GeometryModel, geometry_field='geometry_field', trim_to_boundary=True))
        )

Notes
=====
1. ``geometry_field='geometry_field'`` specifies the geometry to use in the feature. If no geometry_field is specified: the first GeometryField in the model's field set is used.
2. ``trim_to_boundary=True`` will result in GeoJSON tiles with geometries trimmed to the tile boundary
3. ``properties=[...]`` can be used to limit the feature's properties that are serialized
4. ``properties={'field_name': 'property name'}`` will limit the feature's properties and map field names (keys) to property names (values).
