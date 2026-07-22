from .field360_field import get_field_information
from .field360_quality import get_gis_quality
from .field360_harvest import get_harvest_information

def build_field360(field_name):

    field360 = {}

    field360.update(
        get_field_information(field_name)
    )

    field360["quality"] = get_gis_quality(field_name)

    field360["harvest"] = get_harvest_information(field_name)

    return field360