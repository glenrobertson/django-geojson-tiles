"""
Adapted from @jeffkistler's geojson serializer at: https://gist.github.com/967274
"""

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import datetime
import decimal
import types

from django.core.serializers.python import Serializer as PythonSerializer
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.encoding import is_protected_type, smart_unicode
from django.utils import simplejson as json
from django.utils import datetime_safe
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.gis.db.models.fields import GeometryField


class DjangoGeoJSONEncoder(DjangoJSONEncoder):

    def default(self, o):
        if isinstance(o, GEOSGeometry):
            return json.loads(o.geojson)
        else:
            return super(DjangoGeoJSONEncoder, self).default(o)


class GeoJSONSerializer(PythonSerializer):
    def start_serialization(self, queryset):
        self.feature_collection = {"type": "FeatureCollection", "features": []}
        self.feature_collection["crs"] = self.get_crs(queryset)

        bbox = self.options.pop('bbox', None)
        if bbox:
            self.feature_collection["bbox"] = bbox[0][1:]

        self._current = None

    def get_crs(self, queryset):
        if self.crs == False:
            return None
        crs = {}
        srid = self.options.get("srid", "4326")

        crs["type"] = "link"
        properties = {}
        properties["href"] = "http://spatialreference.org/ref/epsg/%s/" % (str(srid))
        properties["type"] = "proj4"
        crs["properties"] = properties
        return crs

    def start_object(self, obj):
        self._current = {"type": "Feature", "properties": {}, "id": obj.pk}

    def end_object(self, obj):
        self.feature_collection["features"].append(self._current)
        self._current = None

    def end_serialization(self):
        self.options.pop('stream', None)
        self.options.pop('properties', None)
        self.options.pop('geometry_field', None)
        self.options.pop('use_natural_keys', None)
        self.options.pop('crs', None)
        self.options.pop('srid', None)

        json.dump(self.feature_collection, self.stream, cls=DjangoGeoJSONEncoder, **self.options)

    def handle_field(self, obj, field):
        # 'field' can either be a string of the field name
        # or a field object
        if isinstance(field, basestring):
            value = getattr(obj, field)
            field_name = field
        else:
            value = field._get_val_from_obj(obj)
            field_name = field.name

        if isinstance(value, GEOSGeometry):
            # ignore other geometries, only one geometry per feature
            if field_name == self.geometry_field:
                self._current['geometry'] = value
        
        elif not is_protected_type(value):
            value = field.value_to_string(obj)

        if self.properties and \
            field_name in self.properties:
            # set the field name to the key's value mapping in self.properties
            if isinstance(self.properties, dict):
                property_name = self.properties[field_name]
                self._current['properties'][property_name] = value
            else:
                self._current['properties'][field_name] = value

        elif not self.properties:
            self._current['properties'][field_name] = value            

    def getvalue(self):
        if callable(getattr(self.stream, 'getvalue', None)):
            return self.stream.getvalue()

    def handle_fk_field(self, obj, field):
        related = getattr(obj, field.name)
        if related is not None:
            if self.use_natural_keys and hasattr(related, 'natural_key'):
                related = related.natural_key()
            else:
                if field.rel.field_name == related._meta.pk.name:
                    # Related to remote object via primary key
                    related = related._get_pk_val()
                else:
                    # Related to remote object via other field
                    related = smart_unicode(getattr(related, field.rel.field_name), strings_only=True)
        self._current['properties'][field.name] = related

    def handle_m2m_field(self, obj, field):
        if field.rel.through._meta.auto_created:
            if self.use_natural_keys and hasattr(field.rel.to, 'natural_key'):
                m2m_value = lambda value: value.natural_key()
            else:
                m2m_value = lambda value: smart_unicode(value._get_pk_val(), strings_only=True)
            self._current['properties'][field.name] = [m2m_value(related)
                               for related in getattr(obj, field.name).iterator()]

    def serialize(self, queryset, **options):
        """
        Serialize a queryset.
        """
        self.options = options

        self.stream = options.get("stream", StringIO())
        self.properties = options.get("properties")
        self.geometry_field = options.get("geometry_field")
        self.use_natural_keys = options.get("use_natural_keys", False)
        self.bbox = options.get("bbox", None)
        self.crs = options.get("crs", True)

        self.start_serialization(queryset)

        opt = queryset.model._meta
        local_fields = queryset.model._meta.local_fields
        many_to_many_fields = queryset.model._meta.many_to_many

        # populate each queryset obj as a feature
        for obj in queryset:
            self.start_object(obj)

            # handle the geometry field
            self.handle_field(obj, self.geometry_field)

            # handle the property fields
            for field in local_fields:
                # don't include the pk in the properties
                # as it is in the id of the feature
                if field.name == queryset.model._meta.pk.name:
                    continue

                if field.serialize or field.primary_key:
                    if field.rel is None:
                        if self.properties is None or field.attname in self.properties:
                            self.handle_field(obj, field)
                    else:
                        if self.properties is None or field.attname[:-3] in self.properties:
                            self.handle_fk_field(obj, field)
            for field in many_to_many_fields:
                if field.serialize:
                    if self.properties is None or field.attname in self.properties:
                        self.handle_m2m_field(obj, field)

            self.end_object(obj)
        self.end_serialization()
        return self.getvalue()
