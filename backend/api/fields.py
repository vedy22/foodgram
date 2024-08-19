import base64

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            format, imgstr = data.split(";base64,")
            ext = format.split("/")[-1]

            data = ContentFile(base64.b64decode(imgstr), name="temp." + ext)
        return super().to_internal_value(data)

    def to_representation(self, value):
        url = super().to_representation(value)
        if url and "/backend_media" in url:
            url_parts = url.split("/backend_media")
            if len(url_parts) > 1:
                url_without_host = '/media' + url_parts[1]
                return url_without_host
        return url
