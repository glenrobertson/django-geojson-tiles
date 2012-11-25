from django.contrib.gis.geos import Polygon
from django.http import HttpResponse
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

    serializer = GeoJSONSerializer()

    def coords_to_bbox_mmap(self, z, x, y):
        z = int(z)
        x = int(x)
        y = int(y)

        # set up bounding box from coord
        coord = ModestMaps.Core.Coordinate(y, x, z)
        tl = self.projection.coordinateLocation(coord)
        br = self.projection.coordinateLocation(coord.right().down())
        bbox = Polygon.from_bbox((tl.lon, tl.lat, br.lon, br.lat))
        bbox.srid = self.srid

        modest_map = ModestMaps.mapByExtentZoom(self.provider, tl, br, z)
        return bbox, modest_map

    def __init__(self, model, geometry_field, trim_to_boundary=True, properties=None):
        self.model = model
        self.geometry_field = geometry_field
        self.trim_to_boundary = trim_to_boundary
        self.properties = properties

    def __call__(self, request, z, x, y):
        bbox, modest_map = self.coords_to_bbox_mmap(z, x, y)

        shapes = self.model.objects.filter(**{
            '%s__intersects' % self.geometry_field: bbox
        })

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

        data = self.serializer.serialize(shapes, **serializer_options)
        return HttpResponse(data, content_type='application/json')
