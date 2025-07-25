# Lessons Learned

Overzicht van wat we hebben geleerd tijdens het project. Dit kan nuttig zijn voor toekomstige projecten en om te delen met het team.

## Technische Lessons learned

taalmodellen zijn dol op sql queries, dus wanneer je je data op die manier kan opvragen is dat nice.
Tegelijkertijd, taalmodellen snappen zonder extra hulp weinig van spatial functies binnen sql.

## Docstrings

Docstrings zijn erg belangrijk voor hoe de LLMs met je tools omgaat.
Zorg ervoor dat je altijd een duidelijke en informatieve docstring toevoegt aan elke tool.

## Pydantic Model validator

Eerst je model checken op wat we willen dat ingevuld mag worden.
En anders ModelRetry uitvoeren

Zie ook: https://docs.pydantic.dev/2.10/concepts/validators/#model-validators

Naast type validation, krijg je hiermee ook mogelijkheid om model waarden te valideren
Voordat je code uitvoert. Hier checken we of beide velden ingevuld zijn:

```python
class GetSeriesHeadersInput(BaseModel):
    """
    GetSeriesHeadersInput defines the input parameters for retrieving series headers.

    Supports querying by parameter_id OR location_id (not both) for incremental caching.
    """

    parameter_id: Optional[str] = Field(
        None, description="Parameter ID to retrieve series headers for (e.g., 'Kwel')"
    )
    location_id: Optional[str] = Field(
        None,
        description="Location ID to retrieve series headers for (e.g., 'GPG_1698')",
    )

    @model_validator(mode="after")
    def validate_exclusive_fields(cls, values):
        parameter_id, location_id = (
            values.parameter_id,
            values.location_id,
        )
        if not (parameter_id or location_id):
            raise ModelRetry("Either 'parameter_id' or 'location_id' must be provided.")
        if parameter_id and location_id:
            raise ModelRetry(
                "Only one of 'parameter_id' or 'location_id' can be provided, not both."
            )
        return values
```

## Parsen van XML vs JSON uit de FewsWebServices

Pi-XML als output lijkt sneller te parsen dan Pi-JSON

## Web Feature Service

Web Feature Service vanuit de FewsWebservices lijkt een mogelijkheid te geven voor het verkrijgen van GeoJSON data van geregistreerde grid plot scalar type. Lijkt nog work-in-progress door Deltares
