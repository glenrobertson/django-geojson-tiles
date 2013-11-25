from django.contrib.gis.geos import Polygon
from django.http import HttpResponse, HttpResponseServerError
from django.contrib.gis.db.models import GeometryField, MultiPointField, PointField
from serializers import GeoJSONSerializer
import ModestMaps
import TileStache


class GeoJSONTile:
    width = 256
    height = 256

    # projection settings
    projection = TileStache.Geography.SphericalMercator()
    provider = ModestMaps.OpenStreetMap.Provider()
    srid = 4326

    def coords_to_bbox_mmap(self, z, x, y):
        # set up bounding box from coord
        coord = ModestMaps.Core.Coordinate(y, x, z)
        tl = self.projection.coordinateLocation(coord)
        br = self.projection.coordinateLocation(coord.right().down())
        bbox = Polygon.from_bbox((tl.lon, tl.lat, br.lon, br.lat))
        bbox.srid = self.srid

        modest_map = ModestMaps.mapByExtentZoom(self.provider, tl, br, z)
        return bbox, modest_map

    def pre_serialization(self, queryset, z, x, y, bbox):
        """
        Hook to modify queryset before serialization
        """
        return queryset

    def post_serialization(self, geojson, z, x, y, bbox):
        """
        Hook to modify geojson after serialization
        """
        return geojson

    def __init__(self, model, geometry_field=None, trim_to_boundary=True, properties=None, primary_key=None):
        self.model = model
        self.geometry_field = geometry_field
        self.trim_to_boundary = trim_to_boundary
        self.properties = properties
        self.primary_key = primary_key

        # if geometry field name is not specified,
        # use the first GeometryField that is found
        if self.geometry_field == None and self.model != None:
            try:
                field = [f for f in self.model._meta.fields if isinstance(f, GeometryField)][0]
                self.geometry_field = field.name
            except IndexError:
                pass

    def __call__(self, request, z, x, y):
        z = int(z)
        x = int(x)
        y = int(y)

        if self.geometry_field == None:
            return HttpResponseServerError('No geometry was specified or the model "%s" did not have a GeometryField present' % (self.model._meta.object_name))

        bbox, modest_map = self.coords_to_bbox_mmap(z, x, y)

        shapes = self.model.objects.filter(**{
            '%s__intersects' % self.geometry_field: bbox
        })

        # Can't trim point geometries to a boundary
        self.trim_to_boundary = self.trim_to_boundary \
            and not isinstance(shapes.model._meta.get_field(self.geometry_field), PointField) \
            and not isinstance(shapes.model._meta.get_field(self.geometry_field), MultiPointField) \

        if self.trim_to_boundary:
            shapes = shapes.intersection(bbox)
            geometry_field = 'intersection'
        else:
            geometry_field = self.geometry_field

        serializer_options = {
            'bbox': bbox,
            'geometry_field': geometry_field,
            'srid': self.srid,
        }
        if self.properties:
            serializer_options.update(properties=self.properties)
        if self.primary_key:
            serializer_options.update(primary_key=self.primary_key)

        serializer = GeoJSONSerializer()

        shapes = self.pre_serialization(shapes, z, x, y, bbox)
        data = serializer.serialize(shapes, **serializer_options)
        data = self.post_serialization(data, z, x, y, bbox)
        return HttpResponse(data, content_type='application/json')
