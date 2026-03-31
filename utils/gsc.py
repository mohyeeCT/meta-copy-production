from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta


def get_gsc_client(service_account_info: dict):
    scopes = ["https://www.googleapis.com/auth/webmasters.readonly"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    return build("searchconsole", "v1", credentials=creds)


def get_top_queries_for_url(client, site_url: str, page_url: str, top_n: int = 10) -> list:
    """
    Returns top N queries for a given page URL sorted by impressions.
    Each item: { query, impressions, clicks, ctr, position }
    Pulling 10 by default to give the scorer more candidates to work with.
    """
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=90)).strftime("%Y-%m-%d")

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "dimensionFilterGroups": [{
            "filters": [{
                "dimension": "page",
                "operator": "equals",
                "expression": page_url
            }]
        }],
        "rowLimit": top_n,
        "orderBy": [{"fieldName": "impressions", "sortOrder": "DESCENDING"}]
    }

    try:
        response = client.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = response.get("rows", [])
        results = []
        for row in rows:
            impressions = row.get("impressions", 0)
            clicks = row.get("clicks", 0)
            ctr = round(clicks / impressions, 4) if impressions > 0 else 0.0
            results.append({
                "query":       row["keys"][0],
                "impressions": impressions,
                "clicks":      clicks,
                "ctr":         ctr,
                "position":    round(row.get("position", 0), 1)
            })
        return results
    except Exception as e:
        # Return error details so app can surface them
        return [{"_error": str(e), "_site_url": site_url, "_page_url": page_url}]


def list_verified_properties(client) -> list:
    """
    Returns all GSC properties the service account has access to.
    Useful for diagnosing property URL mismatches.
    """
    try:
        response = client.sites().list().execute()
        return [
            {
                "site_url":         s.get("siteUrl"),
                "permission_level": s.get("permissionLevel")
            }
            for s in response.get("siteEntry", [])
        ]
    except Exception as e:
        return [{"_error": str(e)}]