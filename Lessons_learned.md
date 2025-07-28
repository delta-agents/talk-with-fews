# Lessons Learned

Overzicht van wat we hebben geleerd tijdens het project. Dit kan nuttig zijn voor toekomstige projecten en om te delen met het team.

## Technische Lessons Learned

- Taalmodellen zijn dol op sql queries, dus wanneer je je data op die manier kan opvragen is dat nice.
- Tegelijkertijd, taalmodellen snappen zonder extra hulp weinig van spatial functies binnen sql.

## Docstrings

Docstrings zijn erg belangrijk voor hoe de LLMs met je tools omgaat.
Zorg ervoor dat je altijd een duidelijke en informatieve docstring toevoegt aan elke tool.

## Pydantic Model Validator

Eerst je model checken op wat we willen dat ingevuld mag worden.
En anders ModelRetry uitvoeren.

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

# Feature Requests

## Flag Sources in FEWS PI REST Web Service

Voorgestelde feature request voor Deltares:

```
Titel: Add flag source information to timeseries events in PI REST Web Service

Beschrijving:
Voorstel om flag source informatie toe te voegen aan de timeseries events in de FEWS PI REST Web Service. Dit maakt het mogelijk om niet alleen te zien welke kwaliteitsvlag (0-9) een waarde heeft, maar ook waarom deze vlag is gezet (IMP, SN, HX, etc.).

Technische details:
1. Nieuwe optionele query parameter: includeFlagSources=true
2. Wanneer aangezet, voegt de service een 'flagSource' attribuut toe aan events in de XML/JSON response:

XML voorbeeld:
<event date="2024-01-01" time="00:00:00" value="1.23" flag="3" flagSource="SN"/>

JSON voorbeeld:
{
  "date": "2024-01-01",
  "time": "00:00:00",
  "value": 1.23,
  "flag": 3,
  "flagSource": "SN"
}

Use case:
- Analyseren van datakwaliteit en bronnen van kwaliteitsproblemen
- Traceren van de oorsprong van flags voor troubleshooting
- Genereren van kwaliteitsrapporten met gedetailleerde flag-source statistieken

Impact:
- Minimale impact op bestaande clients (backwards compatible door optionele parameter)
- Kleine toename in response grootte alleen wanneer expliciet gevraagd
- Grote meerwaarde voor kwaliteitsanalyse en monitoring
```

## XML Schema Validatie van FEWS XML als MCP Tool

Voorgestelde feature request voor Deltares:

```
Titel: Onderzoek en implementeer XML Schema validatie met xmlschema package

Beschrijving:
Voorstel om te onderzoeken hoe de Python xmlschema library gebruikt kan worden voor XML validatie in FEWS. Deze library biedt robuuste XSD validatie mogelijkheden en ondersteunt ook partiële validatie van XML documenten.

Technische details:
1. Evalueer de xmlschema Python package (MIT licentie) voor:
   - Volledige XSD 1.0 en 1.1 validatie
   - Partiële validatie van specifieke XML elementen/secties
   - Offline caching van schema's
   - Bescherming tegen XML aanvallen

2. Mogelijke implementatie scenarios:
   - Validatie tijdens import/export van configuraties
   - Runtime validatie van XML berichten
   - Validatie van specifieke onderdelen zonder het hele document te laden

Voordelen:
- Betere validatie van XML configuraties en data
- Mogelijkheid om alleen relevante delen te valideren (performance)
- Moderne Python library met actieve ondersteuning
- Veilige verwerking van XML documenten

Impact:
- Verbeterde data kwaliteit en betrouwbaarheid
- Efficiëntere validatie door partiële checks
- Betere foutmeldingen bij configuratie problemen
```

# Lessons still to Learn

## Performance PI-XML vs PI-JSON

Onderzoeksvraag: Wat is sneller - het parsen van PI-XML of PI-JSON uit de FEWS Web Services naar bruikbare Python objecten?

Huidige observatie: PI-XML lijkt sneller te parsen dan PI-JSON, maar dit moet nog goed onderzocht worden.

Aandachtspunten voor onderzoek:
- Vergelijk de verwerkingssnelheid van de FEWS Web Service voor beide formaten
- Analyseer de verschillende verwerkingsmethoden in Python (zie verschil tussen `get_parameters.py` en `get_series_data.py`)
- Meet de totale doorlooptijd van request tot bruikbaar Python object
- Onderzoek impact van datagrootte op performance
- Vergelijk memory gebruik van beide methoden

## Agent Response Format Optimalisatie

Onderzoeksvraag: Wat werkt beter voor de Agent - markdown, JSON of XML als response format van MCP tools?

Context: Volgens de Pydantic AI documentatie vinden LLMs het vaak makkelijker om semi-gestructureerde data als XML te lezen dan bijvoorbeeld JSON.

Aandachtspunten voor onderzoek:
- Test verschillende response formats met dezelfde data
- Meet de kwaliteit van de Agent's interpretatie per format
- Onderzoek of complexiteit van de data invloed heeft op de beste keuze
- Vergelijk processing tijd van de Agent per format
- Test of een combinatie van formats (bv. XML voor structuur, markdown voor tekst) optimaal kan zijn
- Evalueer of de format_as_xml functie van Pydantic AI meerwaarde biedt voor onze use case
