import re
from pathlib import Path


def main():
    # alter with path to the configs
    configs = [r"C:\Data\FEWS\FEWS_Dommel\wsdd-wis\FEWS\Config"]
    for config_path in configs:
        config = Path(config_path)
        filter_file = config / "RegionConfigFiles" / "Filters.xml"
        webservices_file = (
            config / "PiServiceConfigFiles" / "TalkWithFEWSWebServices.xml"
        )
        new_filter_name = "AllFiltersForTalkWithFEWS"

        with open(filter_file, "r", encoding="utf-8") as f:
            filter_content = f.read()
            # Extract all filter IDs using regex
            filter_ids = re.findall(r'<filter id="([^"]+)"', filter_content)
            all_filters = f'    <filter id="{new_filter_name}">\n'
            for filter in filter_ids:
                all_filters += f'        <child foreignKey="{filter}"/>\n'
            all_filters += "    </filter>"
            # Read the existing filter file

            # Insert the new filter before </filters>
            updated_content = filter_content.replace(
                "</filters>", f"{all_filters}\n</filters>"
            )

        with open(filter_file, "w", encoding="utf-8") as fw:
            # add all the filters
            fw.write(updated_content)

        with open(webservices_file, "w") as fw:
            fw.write(
                f"""<?xml version="1.0" encoding="utf-8"?>
        <webServices xmlns="http://www.wldelft.nl/fews" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.wldelft.nl/fews https://fewsdocs.deltares.nl/schemas/version1.0/webServices.xsd">
            <general>
                <filters>
                    <filterId>{new_filter_name}</filterId>
                </filters>
                <missingValue>-999</missingValue>
                <omitMissingValues>true</omitMissingValues>
                <readonlyMode>true</readonlyMode>
                <testPageEnabled>true</testPageEnabled>
            </general>
        </webServices>
        """
            )


if __name__ == "__main__":
    main()
