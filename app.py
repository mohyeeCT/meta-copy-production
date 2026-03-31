import streamlit as st
import pandas as pd
import json
import time
from io import StringIO

from utils.sheets import get_gspread_client, load_sheet, write_results_to_sheet
from utils.gsc import get_gsc_client, get_top_queries_for_url
from utils.dfs import get_keyword_overview, get_keyword_difficulty
from utils.keyword import select_keyword
from utils.copy_gen import generate_copy

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Meta Copy Production",
    page_icon="✍️",
    layout="wide"
)

st.title("Meta Copy Production")
st.caption("Generate title tags and meta descriptions at scale using GSC + DataForSEO + AI.")

# ── Sidebar: credentials ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("Credentials")

    sa_file = st.file_uploader("Service Account JSON", type=["json"],
                                help="Used for both Google Sheets and GSC access.")

    st.divider()
    st.subheader("DataForSEO")
    dfs_login = st.text_input("Login (email)", type="default")
    dfs_password = st.text_input("Password", type="password")

    st.divider()
    st.subheader("AI Provider")
    ai_provider = st.selectbox("Provider", [
        "Claude",
        "OpenAI",
        "Gemini (free)",
        "Mistral (free tier)",
        "Groq (free tier)"
    ])
    _key_labels = {
        "Claude": ("Claude API Key", "console.anthropic.com"),
        "OpenAI": ("OpenAI API Key", "platform.openai.com/api-keys"),
        "Gemini (free)": ("Google AI Studio API Key", "aistudio.google.com/app/apikey - free, no card needed"),
        "Mistral (free tier)": ("Mistral API Key", "console.mistral.ai - free tier available"),
        "Groq (free tier)": ("Groq API Key", "console.groq.com - free tier available"),
    }
    _label, _hint = _key_labels[ai_provider]
    ai_key = st.text_input(_label, type="password", help=_hint)

    st.divider()
    st.subheader("Copy Settings")
    business_type = st.selectbox(
        "Business Type",
        ["b2b", "b2c", "ecommerce", "service", "local", "general"],
        help="Adjusts tone, CTA style, and copy patterns to match the client's business model."
    )
    brand_name = st.text_input("Brand Name", placeholder="Acme Inc.")
    full_brand_name = st.text_input(
        "Full Brand Name (optional)",
        placeholder="Dayson Shalabi Burkert",
        help="If the brand is an abbreviation (e.g. DSB), enter the full name here. Each word will be added to the branded filter automatically. Catches queries like 'dayson shalabi attorney' or 'shalabi law'."
    )
    forbidden_phrases = st.text_area(
        "Forbidden Phrases (one per line)",
        placeholder="best in class\nworld-class\namazing",
        height=80
    )
    branded_terms_input = st.text_area(
        "Branded Terms to Exclude (one per line)",
        placeholder="acme\nacme inc",
        height=60
    )
    location_code = st.number_input("DFS Location Code", value=2840, step=1,
                                     help="2840 = US. See DataForSEO docs for other locations.")
    min_volume = st.number_input("Min Keyword Volume", value=10, step=10,
                                     help="Lower this for smaller sites. Set to 0 to disable volume filtering.")

# ── Main: Sheet connection ────────────────────────────────────────────────────
st.header("1. Connect to Google Sheet")

col1, col2 = st.columns([3, 1])
with col1:
    sheet_url = st.text_input("Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")
with col2:
    worksheet_name = st.text_input("Worksheet Name", placeholder="Leave blank for first sheet")

st.caption("Sheet must have at minimum: a URL column. Optional: keyword column, page type column.")

if sheet_url and sa_file:
    try:
        sa_info = json.load(sa_file)

        # Show service account email so user knows what to share the sheet with
        sa_email = sa_info.get("client_email", "unknown")
        st.info(f"Service account: **{sa_email}** — make sure this email has Editor access to the sheet.")

        gc = get_gspread_client(sa_info)
        df, spreadsheet, ws = load_sheet(gc, sheet_url, worksheet_name or None)
        st.success(f"Connected. {len(df)} rows loaded.")
        st.dataframe(df.head(5), use_container_width=True)
        st.session_state["df"] = df
        st.session_state["ws"] = ws
        st.session_state["sa_info"] = sa_info
    except Exception as e:
        st.error(f"Could not connect to sheet: {e}")
        st.caption("Most common causes: (1) sheet not shared with the service account email above, (2) wrong sheet URL, (3) service account missing Google Sheets API access in Cloud Console.")

# ── Main: Column mapping ──────────────────────────────────────────────────────
if "df" in st.session_state:
    st.header("2. Map Columns")
    df = st.session_state["df"]
    cols = ["(none)"] + list(df.columns)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        url_col = st.selectbox("URL column *", [c for c in cols if c != "(none)"] or cols)
    with col2:
        keyword_col = st.selectbox("Keyword column (optional)", cols)
    with col3:
        page_type_col = st.selectbox("Page type column (optional)", cols)
    with col4:
        h1_col = st.selectbox("H1 column (optional)", cols,
                              help="Map this to a column in your sheet containing the current page H1. Used as topic context for copy generation.")

    st.divider()

    # ── Main: GSC settings ────────────────────────────────────────────────────
    st.header("3. GSC Settings")
    gsc_site_url = st.text_input(
        "GSC Property URL",
        placeholder="https://example.com/ or sc-domain:example.com"
    )

    # ── Main: Brand Detection ─────────────────────────────────────────────────
    st.header("4. Brand Detection")

    detect_ready = (
        sa_file is not None and
        gsc_site_url and
        "df" in st.session_state and
        "sa_info" in st.session_state
    )

    if detect_ready:
        detect_btn = st.button("Auto-detect Branded Terms", type="secondary")

        if detect_btn:
            with st.spinner("Scanning GSC queries for branded signals..."):
                _sa_info  = st.session_state["sa_info"]
                _gsc      = get_gsc_client(_sa_info)
                _df       = st.session_state["df"].copy()

                # Sample up to 10 URLs from the sheet
                _sample_urls = _df[url_col].dropna().tolist()[:10]

                _all_queries = {}
                for _url in _sample_urls:
                    _url = str(_url).strip()
                    if not _url.startswith("http"):
                        continue
                    _rows = get_top_queries_for_url(_gsc, gsc_site_url, _url, top_n=20)
                    for _r in _rows:
                        if "_error" in _r:
                            continue
                        _q = _r["query"].lower()
                        if _q not in _all_queries:
                            _all_queries[_q] = _r
                        else:
                            # Accumulate impressions across URLs
                            _all_queries[_q]["impressions"] += _r.get("impressions", 0)
                            _all_queries[_q]["clicks"]      += _r.get("clicks", 0)

                # Auto-detect branded signals
                # Extract domain words from site URL for domain-based detection
                import re as _re
                _domain_raw = _re.sub(r"https?://(www\.)?|sc-domain:", "", gsc_site_url).rstrip("/")
                _domain_parts = set(_re.findall(r"[a-z]+", _domain_raw.lower()))
                _domain_parts -= {"com","net","org","co","uk","io","house","app","law","firm","group","inc","llc","ltd"}

                # Also include words from full brand name as detection seeds
                _full_name_parts = set(
                    w.lower() for w in _re.findall(r"[a-zA-Z]+", full_brand_name)
                    if len(w) >= 3
                )
                _domain_parts = _domain_parts | _full_name_parts

                _detected = {}
                for _q, _r in _all_queries.items():
                    _imp  = _r.get("impressions", 0)
                    _clk  = _r.get("clicks", 0)
                    _pos  = _r.get("position", 99)
                    _ctr  = _clk / _imp if _imp > 0 else 0
                    _reasons = []

                    # Signal 1: high CTR (branded queries get clicked almost every time)
                    if _ctr >= 0.15 and _imp >= 10:
                        _reasons.append(f"CTR {round(_ctr*100)}%")

                    # Signal 2: dominant position + strong clicks
                    if _pos <= 2.0 and _clk >= 5:
                        _reasons.append(f"pos {_pos}")

                    # Signal 3: query contains a domain word
                    _q_words = set(_re.findall(r"[a-z]+", _q))
                    _dom_match = _domain_parts & _q_words
                    if _dom_match:
                        _reasons.append(f"domain word: {', '.join(_dom_match)}")

                    if _reasons:
                        # Extract shortest root term from query for filtering
                        # Prefer domain word if detected, else first word
                        if _dom_match:
                            _root = sorted(_dom_match, key=len)[0]
                        else:
                            _root = _q.split()[0]

                        if _root not in _detected:
                            _detected[_root] = {
                                "queries": [],
                                "reasons": set()
                            }
                        _detected[_root]["queries"].append(_q)
                        _detected[_root]["reasons"].update(_reasons)

                st.session_state["detected_branded"] = _detected
                if not _detected:
                    st.info("No branded terms detected automatically. Use manual entry in the sidebar if needed.")

        # Show detected terms as checkboxes
        if "detected_branded" in st.session_state and st.session_state["detected_branded"]:
            st.caption("Detected branded terms. Checked = will be excluded from keyword scoring.")
            _confirmed = {}
            for _root, _data in st.session_state["detected_branded"].items():
                _label = f"**{_root}** — matches: {', '.join(_data['queries'][:3])}{'...' if len(_data['queries']) > 3 else ''}"
                _reason_str = " | ".join(_data["reasons"])
                _checked = st.checkbox(
                    f"`{_root}` ({_reason_str})",
                    value=True,
                    key=f"brand_chk_{_root}",
                    help=f"Queries that will be excluded: {', '.join(_data['queries'][:5])}"
                )
                if _checked:
                    _confirmed[_root] = _data
            st.session_state["confirmed_branded"] = list(_confirmed.keys())
        elif "detected_branded" not in st.session_state:
            st.caption("Click 'Auto-detect Branded Terms' to scan GSC queries before running.")
    else:
        st.caption("Complete credentials and connect your sheet first.")

    # ── Main: Run ─────────────────────────────────────────────────────────────
    st.header("5. Run")

    ready = (
        sa_file is not None and
        dfs_login and dfs_password and
        ai_key and
        gsc_site_url and
        "df" in st.session_state
    )

    if not ready:
        st.warning("Complete all credentials and settings in the sidebar before running.")

    run_btn = st.button("Generate Copy", type="primary", disabled=not ready)

    if run_btn:
        df_work = st.session_state["df"].copy()
        sa_info = st.session_state["sa_info"]

        gsc_client = get_gsc_client(sa_info)

        # Merge manual + full brand name words + auto-detected confirmed branded terms
        _manual    = [t.strip().lower() for t in branded_terms_input.strip().splitlines() if t.strip()]
        _auto      = st.session_state.get("confirmed_branded", [])

        # Extract individual words from full brand name (skip short words < 3 chars)
        import re as _re2
        _full_name_words = [
            w.lower() for w in _re2.findall(r"[a-zA-Z]+", full_brand_name)
            if len(w) >= 3
        ] if full_brand_name.strip() else []

        branded_terms = list(set(_manual + _auto + _full_name_words))

        if branded_terms:
            st.info(f"Branded filter active: {', '.join(sorted(branded_terms))}")

        results = []
        skipped = []

        progress = st.progress(0, text="Starting...")
        total = len(df_work)

        for i, row in df_work.iterrows():
            url = str(row.get(url_col, "")).strip()
            if not url or not url.startswith("http"):
                skipped.append({"row": i + 2, "reason": "Invalid or missing URL"})
                results.append({
                    "url": url,
                    "selected_keyword": None,
                    "keyword_source": None,
                    "runner_up": None,
                    "generated_title": None,
                    "generated_description": None,
                    "title_length": None,
                    "description_length": None,
                    "status": "skipped: invalid URL"
                })
                progress.progress((i + 1) / total, text=f"Row {i+1}/{total}: skipped")
                continue

            page_type = str(row.get(page_type_col, "general")).strip() if page_type_col != "(none)" else "general"
            if not page_type:
                page_type = "general"

            # H1: manual entry only
            h1_value = ""
            h1_source = ""
            if h1_col != "(none)":
                manual_h1 = str(row.get(h1_col, "")).strip()
                if manual_h1 and manual_h1.lower() != "none":
                    h1_value = manual_h1
                    h1_source = "manual"

            # Priority 1: manual keyword
            manual_kw = str(row.get(keyword_col, "")).strip() if keyword_col != "(none)" else ""
            keyword_source = None
            selected_keyword = None
            runner_up_kw = None

            if manual_kw:
                selected_keyword = manual_kw
                keyword_source = "manual"
            else:
                # Priority 2: GSC
                progress.progress((i + 1) / total, text=f"Row {i+1}/{total}: fetching GSC data...")
                gsc_queries = get_top_queries_for_url(gsc_client, gsc_site_url, url, top_n=10)

                # Surface API errors rather than silently returning empty
                if gsc_queries and "_error" in gsc_queries[0]:
                    keyword_source = f"fallback: GSC error - {gsc_queries[0]['_error'][:120]}"
                    gsc_queries = []

                if gsc_queries:
                    # Priority 3: enrich with DFS
                    query_list = [q["query"] for q in gsc_queries]
                    # Store GSC queries in result for diagnostics
                    _gsc_debug = ", ".join([f"{q['query']} (pos {q['position']}, imp {q['impressions']})" for q in gsc_queries])
                    progress.progress((i + 1) / total, text=f"Row {i+1}/{total}: fetching DFS data...")
                    dfs_volumes = get_keyword_overview(dfs_login, dfs_password, query_list, location_code=int(location_code))
                    dfs_difficulty = get_keyword_difficulty(dfs_login, dfs_password, query_list, location_code=int(location_code))

                    # Merge volume + difficulty
                    dfs_merged = {}
                    for kw in query_list:
                        kw_lower = kw.lower()
                        vol = dfs_volumes.get(kw_lower, {}).get("volume", 0)
                        diff = dfs_difficulty.get(kw_lower, {}).get("difficulty", 50)
                        dfs_merged[kw_lower] = {"volume": vol, "difficulty": diff}

                    result = select_keyword(
                        gsc_queries=gsc_queries,
                        dfs_data=dfs_merged,
                        branded_terms=branded_terms,
                        min_volume=int(min_volume),
                        h1=h1_value
                    )

                    if not result["fallback_triggered"]:
                        selected_keyword = result["selected_keyword"]
                        keyword_source = "gsc+dfs"
                        runner_up_kw = result["runner_up"]["keyword"] if result["runner_up"] else None
                    else:
                        # Secondary fallback: use top GSC query by impressions
                        # (ignoring volume filter - useful for niche sites with low DFS volume)
                        non_branded = [
                            q for q in gsc_queries
                            if not any(b in q["query"].lower() for b in branded_terms)
                            and q.get("position", 99) > 1.0
                        ]
                        if non_branded:
                            top_gsc = sorted(non_branded, key=lambda x: x["impressions"], reverse=True)[0]
                            selected_keyword = top_gsc["query"]
                            keyword_source = "gsc-only (low DFS volume)"
                            runner_up_kw = non_branded[1]["query"] if len(non_branded) > 1 else None
                        else:
                            keyword_source = f"fallback: no keyword passed scoring (GSC queries: {_gsc_debug})"

                else:
                    keyword_source = "fallback: no GSC data"

            if not selected_keyword:
                skipped.append({"row": i + 2, "reason": keyword_source})
                results.append({
                    "url": url,
                    "selected_keyword": None,
                    "keyword_source": keyword_source,
                    "runner_up": runner_up_kw,
                    "generated_title": None,
                    "generated_description": None,
                    "title_length": None,
                    "description_length": None,
                    "status": f"skipped: {keyword_source}"
                })
                progress.progress((i + 1) / total, text=f"Row {i+1}/{total}: skipped ({keyword_source})")
                continue

            # Generate copy
            progress.progress((i + 1) / total, text=f"Row {i+1}/{total}: generating copy for '{selected_keyword}'...")
            try:
                copy = generate_copy(
                    provider=ai_provider,
                    api_key=ai_key,
                    url=url,
                    keyword=selected_keyword,
                    page_type=page_type,
                    brand_name=brand_name,
                    forbidden_phrases="\n".join([p.strip() for p in forbidden_phrases.strip().splitlines() if p.strip()]),
                    context="",
                    business_type=business_type,
                    h1=h1_value
                )
                results.append({
                    "url": url,
                    "h1_used": h1_value,
                    "h1_source": h1_source,
                    "selected_keyword": selected_keyword,
                    "keyword_source": keyword_source,
                    "runner_up": runner_up_kw,
                    "generated_title": copy["title"],
                    "generated_description": copy["description"],
                    "title_length": len(copy["title"]),
                    "description_length": len(copy["description"]),
                    "status": "ok"
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "selected_keyword": selected_keyword,
                    "keyword_source": keyword_source,
                    "runner_up": runner_up_kw,
                    "generated_title": None,
                    "generated_description": None,
                    "title_length": None,
                    "description_length": None,
                    "status": f"error: {str(e)}"
                })
                skipped.append({"row": i + 2, "reason": str(e)})

            # Rate limiting: Gemini free tier = 15 RPM (2 calls per URL = ~4s needed)
            _rate_delays = {
                "Gemini (free)": 5.0,
                "Mistral (free tier)": 2.0,
                "Groq (free tier)": 2.0,
                "Claude": 0.5,
                "OpenAI": 0.5,
            }
            time.sleep(_rate_delays.get(ai_provider, 0.5))

        progress.progress(1.0, text="Done.")
        results_df = pd.DataFrame(results)
        st.session_state["results_df"] = results_df
        st.session_state["skipped"]    = skipped
        st.session_state["total"]      = total
        st.rerun()

# ── Results and Export (outside run block so buttons persist across reruns) ──
if "results_df" in st.session_state:
    results_df = st.session_state["results_df"]
    skipped    = st.session_state.get("skipped", [])
    total      = st.session_state.get("total", len(results_df))

    st.header("6. Results")

    ok_count   = len(results_df[results_df["status"] == "ok"])
    skip_count = len(skipped)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total Rows", total)
    m2.metric("Generated", ok_count)
    m3.metric("Skipped / Errors", skip_count)

    def highlight_length(row):
        styles = [""] * len(row)
        try:
            ti = results_df.columns.get_loc("title_length")
            di = results_df.columns.get_loc("description_length")
            if row["title_length"] and int(row["title_length"]) > 60:
                styles[ti] = "background-color: #ffe0e0"
            if row["description_length"] and int(row["description_length"]) > 155:
                styles[di] = "background-color: #ffe0e0"
        except Exception:
            pass
        return styles

    st.dataframe(
        results_df.style.apply(highlight_length, axis=1),
        use_container_width=True,
        height=400
    )

    if skipped:
        with st.expander(f"Skipped rows ({skip_count})"):
            st.dataframe(pd.DataFrame(skipped), use_container_width=True)

    st.header("7. Export")
    ec1, ec2 = st.columns(2)

    with ec1:
        csv_buffer = StringIO()
        results_df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="meta_copy_output.csv",
            mime="text/csv"
        )

    with ec2:
        if st.button("Write Back to Google Sheet"):
            ws  = st.session_state["ws"]
            col_map = {
                "h1_used":              "H1 Used",
                "h1_source":            "H1 Source",
                "selected_keyword":     "SEO Target Keyword",
                "keyword_source":       "Keyword Source",
                "runner_up":            "Runner Up Keyword",
                "generated_title":      "Generated Title",
                "generated_description":"Generated Description",
                "title_length":         "Title Length",
                "description_length":   "Description Length",
                "status":               "Copy Status"
            }
            with st.spinner("Writing to sheet..."):
                try:
                    write_results_to_sheet(ws, results_df, col_map)
                    st.success(f"Done. {len(results_df)} rows written to Google Sheet.")
                except Exception as e:
                    st.error(f"Write failed: {e}")
                    st.caption("Common causes: service account does not have Editor access to the sheet, or the sheet is protected.")
