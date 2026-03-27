# Meta Copy Production

Streamlit app for generating title tags and meta descriptions at scale using GSC + DataForSEO + AI.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Google Service Account
This app uses a single service account for both Google Sheets and GSC access.

1. Go to Google Cloud Console > IAM > Service Accounts
2. Create a service account and download the JSON key
3. Share your Google Sheet with the service account email (Editor access)
4. Add the service account email as a verified user in GSC (Search Console > Settings > Users and permissions)

### 3. Run
```bash
streamlit run app.py
```

---

## Input Sheet Format

Your Google Sheet should have at minimum:

| URL | Keyword (optional) | Page Type (optional) |
|-----|-------------------|---------------------|
| https://example.com/page | water softener | product |

- **URL**: Required. Full URL including https://
- **Keyword**: Optional. If blank, the app will use the GSC + DFS priority chain to select one
- **Page Type**: Optional. Helps the AI understand page context (e.g. product, category, blog, landing)

---

## Keyword Priority Chain

1. If a keyword is manually assigned in the sheet, use it
2. If not, pull top 5 queries from GSC for that URL
3. Score each query using DataForSEO volume + difficulty data
4. Select the highest-scoring query as the target keyword

Rows where no keyword can be selected are flagged in the Skipped section and not written to the sheet.

---

## Output Columns Written Back to Sheet

| Column | Description |
|--------|-------------|
| SEO Target Keyword | The keyword used for copy generation |
| Keyword Source | manual / gsc+dfs / fallback reason |
| Runner Up Keyword | Second-best keyword candidate |
| Generated Title | AI-generated title tag |
| Generated Description | AI-generated meta description |
| Title Length | Character count (flagged red if > 60) |
| Description Length | Character count (flagged red if > 155) |
| Copy Status | ok / skipped / error |

---

## DFS Location Codes

Common codes:
- 2840 = United States
- 2826 = United Kingdom
- 2036 = Australia
- 2124 = Canada

Full list: https://docs.dataforseo.com/v3/appendix/locations/
