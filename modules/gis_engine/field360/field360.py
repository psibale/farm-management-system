from .field360_field import get_field_information
from .field360_quality import get_gis_quality
from .field360_harvest import get_harvest_information
from .field360_yield import get_actual_yield
from .field360_weather import get_weather_information
from .field360_irrigation import get_irrigation_information
from .field360_pest import get_pest_information
from .field360_fertilizer import get_fertilizer_information
from .field360_alerts import get_field_alerts
from .field360_ai import build_ai_recommendation

def build_field360(field_name):

    field360 = {}

    field360.update(get_field_information(field_name))

    field360["harvest"] = get_harvest_information(field_name)

    field360["yield"] = get_actual_yield(field_name)

    field360["quality"] = get_gis_quality(field_name)

    field360["weather"] = get_weather_information()

    field360["irrigation"] = get_irrigation_information(field_name)

    field360["pest"] = get_pest_information(field_name)

    field360["fertilizer"] = get_fertilizer_information(field_name)

    field360["alerts"] = get_field_alerts(field360)

    field360["ai"] = build_ai_recommendation(field360)

    return field360