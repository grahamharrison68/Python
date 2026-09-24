from html import escape
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

import warnings

warnings.filterwarnings(
    "ignore",
    message="Data Validation extension is not supported and will be removed",
    category=UserWarning,
)

PAGE_STYLE = """
body { font-family: Arial, sans-serif; margin: 0; padding: 2rem; color: #102a43; background: #eef5fb; }
main { max-width: 1100px; margin: 0 auto; }
h1 { color: #0b3d91; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
.tile { box-sizing: border-box; display: flex; align-items: center; justify-content: center; min-height: 180px; padding: 1rem; border: 1px solid #0b3d91; border-radius: 8px; background: #1976d2; color: white; font-size: 1.1rem; font-weight: bold; text-align: center; text-decoration: none; box-shadow: 0 3px 8px #102a4326; }
.tile:hover { background: #0b3d91; }
.army-details { margin-top: -0.5rem; margin-bottom: 1.5rem; font-size: 0.9rem; }
"""


def page(title, content):
    """Return a complete HTML page containing the supplied content."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(str(title))}</title>
<style>{PAGE_STYLE}</style>
</head>
<body><main>{content}</main></body>
</html>
"""


def unit_wrapper_page():
        """Return the reusable unit detail page populated from its query parameters."""
        return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Unit Details</title>
<style>
body { margin: 0; height: 100vh; overflow: hidden; font-family: Arial, sans-serif; }
#loadout { box-sizing: border-box; height: 120px; overflow: hidden; padding: 1rem; border-bottom: 2px solid #0b3d91; color: black; background: white; white-space: pre-wrap; }
#source { display: block; width: 100%; height: calc(100vh - 120px); border: 0; }
</style>
</head>
<body>
<div id="loadout"></div>
<iframe id="source" title="Unit reference"></iframe>
<script>
const parameters = new URLSearchParams(window.location.search);
document.title = parameters.get("unit") || "Unit Details";
document.getElementById("loadout").textContent = parameters.get("loadout") || "";
const unitUrl = parameters.get("url") || "";
try {
    const parsedUrl = new URL(unitUrl);
    if (parsedUrl.protocol === "https:" || parsedUrl.protocol === "http:") {
        document.getElementById("source").src = parsedUrl.href;
    }
} catch (error) {
    document.getElementById("source").remove();
}
</script>
</body>
</html>
"""


def validate_columns(dataframes):
    required = {
                "df_army": {"Name", "Filename", "Detachments", "Force Disposition", "Points"},
        "df_unit": {"Unit", "URL"},
                "df_army_list": {"Army", "Unit", "Points", "Loadout"},
    }
    for name, columns in required.items():
        missing = columns - set(dataframes[name].columns)
        if missing:
            raise ValueError(f"{name} is missing columns: {', '.join(sorted(missing))}")


def generate_pages(df_army, df_unit, df_army_list, output_dir):
    """Generate the army index and one linked page for every army."""
    validate_columns({"df_army": df_army, "df_unit": df_unit, "df_army_list": df_army_list})
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "unit.html").write_text(unit_wrapper_page(), encoding="utf-8")

    unit_urls = dict(zip(df_unit["Unit"], df_unit["URL"]))
    army_tiles = []

    for _, army in df_army.iterrows():
        army_name = str(army["Name"])
        filename = Path(str(army["Filename"])).name
        army_rows = df_army_list[df_army_list["Army"] == army_name].sort_values(
            by="Unit", key=lambda values: values.astype(str).str.casefold()
        )
        unit_tiles = []
        for unit in army_rows.itertuples(index=False):
            unit_name = str(unit.Unit)
            unit_url = unit_urls.get(unit_name)
            if not unit_url or pd.isna(unit_url):
                raise ValueError(f"No URL found in df_unit for unit: {unit_name}")
            unit_parameters = {
                'unit': unit_name,
                'loadout': str(unit.Loadout),
                'url': str(unit_url),
            }
            unit_page_url = f"unit.html?{urlencode(unit_parameters)}"
            unit_tiles.append(
                f'<a class="tile" href="{escape(unit_page_url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">'
                f'{escape(unit_name)} ({escape(str(unit.Points))} points)</a>'
            )

        army_content = (
            f"<h1>{escape(army_name)} ({escape(str(army['Points']))} Points)</h1>"
            f'<p class="army-details">Detachments: {escape(str(army["Detachments"]))}, '
            f'Force Disposition: {escape(str(army["Force Disposition"]))}</p>'
            f'<section class="tiles">{"".join(unit_tiles)}</section>'
        )
        (output_dir / filename).write_text(page(army_name, army_content), encoding="utf-8")
        army_tiles.append(
            f'<a class="tile" href="{escape(filename, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer">{escape(army_name)}</a>'
        )

    index_content = f'<h1>Army Lists</h1><section class="tiles">{"".join(army_tiles)}</section>'
    (output_dir / "index.html").write_text(page("Army Lists", index_content), encoding="utf-8")


def main():
    """Load the workbook and generate the HTML pages."""
    project_dir = Path(__file__).resolve().parent
    # input_file = project_dir / "data" / "in" / "ArmyList.xlsx"
    # output_dir = project_dir / "data" / "out"

    input_file = project_dir / "ArmyList.xlsx"
    output_dir = project_dir

    print("Loading army list data...")
    df_army = pd.read_excel(input_file, sheet_name="Army")
    df_unit = pd.read_excel(input_file, sheet_name="Unit")
    df_army_list = pd.read_excel(input_file, sheet_name="ArmyList")
    generate_pages(df_army, df_unit, df_army_list, output_dir)
    print(f"Generated army pages in {output_dir}")

if __name__ == "__main__":
    main()
