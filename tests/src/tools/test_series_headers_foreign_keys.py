import asyncio
import duckdb
from src.talk_with_fews.routers.setup_connections import get_runtime_ctx
from src.talk_with_fews.tools.webservice.ingest_series_headers import (
    ingest_series_headers,
)
from tests.utils_tests import setup_dot_env


def test_series_headers_foreign_keys():
    """
    Controleer of alle series_headers geldige foreign keys hebben naar parameters en locations.
    De test faalt als er een series_header is met een locationId of parameterId die niet bestaat.
    """
    user_settings = setup_dot_env()
    # Setup context en database connectie
    ctx = get_runtime_ctx(user_settings)
    db: duckdb.DuckDBPyConnection = ctx.deps.cache_FewsWebServices_db
    webservice_url = ctx.deps.webservice_url

    # Eerst data inladen als de tabel leeg is
    series_count = db.execute("SELECT COUNT(*) FROM series_headers").fetchone()[0]
    if series_count == 0:
        print("Series headers tabel is leeg, laad data in...")
        try:
            result = asyncio.run(
                ingest_series_headers(
                    webservice_url=webservice_url,
                    cache_FewsWebServices_db=db,
                    parameter_id="Kwel",
                )
            )
            print(f"Data ingeladen: {result}")
        except Exception as e:
            print(f"Error bij inladen data: {e}")
            import traceback

            traceback.print_exc()

    # Query voor series_headers met ongeldige locationId
    invalid_locations = db.execute(
        """
        SELECT sh.id, sh.locationId
        FROM series_headers sh
        LEFT JOIN locations l ON sh.locationId = l.locationId
        WHERE l.locationId IS NULL
        """
    ).fetchall()

    # Query voor series_headers met ongeldige parameterId
    invalid_parameters = db.execute(
        """
        SELECT sh.id, sh.parameterId
        FROM series_headers sh
        LEFT JOIN parameters p ON sh.parameterId = p.id
        WHERE p.id IS NULL
        """
    ).fetchall()

    assert not invalid_locations, (
        f"Er zijn series_headers met een ongeldige locationId: {invalid_locations}"
    )
    assert not invalid_parameters, (
        f"Er zijn series_headers met een ongeldige parameterId: {invalid_parameters}"
    )

    # Controleer of er überhaupt series_headers zijn
    total_series = db.execute("SELECT COUNT(*) FROM series_headers").fetchone()[0]
    print(f"Totaal aantal series_headers in de database: {total_series}")

    # Als er series_headers zijn, toon dan een overzicht
    if total_series > 0:
        series_overview = db.execute(
            """
            SELECT sh.parameterId, sh.locationId, COUNT(*) as count
            FROM series_headers sh
            GROUP BY sh.parameterId, sh.locationId
            ORDER BY sh.parameterId, sh.locationId
            LIMIT 10
            """
        ).fetchall()
        print(f"Overzicht van series_headers: {series_overview}")
    else:
        print("Geen series_headers gevonden in de database")
