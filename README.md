# Interior Quotation Generator

This is a small Streamlit app to create interior project estimates by selecting materials from a categorized inventory, adding new materials when needed, entering quantities, and exporting a final estimate.

Getting started (Windows PowerShell):

1. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install requirements:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
streamlit run app.py
```

How it works
- The app reads `inventory.json` which is a mapping of categories to materials with per-unit prices.
- For each category you can select an existing material or choose "Add new material" to add a name and price; new items are saved back to `inventory.json`.
- Provide quantities for selected items, review breakdown, and download the estimate as JSON.

Notes & next steps
- Currently quantity is a generic "units" field — you can adapt the UI to collect lengths, areas, or other measures per category.
- Consider adding persistence via a database (SQLite) if multiple users will modify inventory concurrently.
