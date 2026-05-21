import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Alnumuw Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="collapsed")

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS  — Option C: warm dark
# ══════════════════════════════════════════════════════════════════════════════
BLUE   = "#3B82F6"; GREEN  = "#22C55E"; RED    = "#EF4444"
AMBER  = "#F59E0B"; PURPLE = "#8B5CF6"; GRAY   = "#6B7280"; TEAL = "#14B8A6"
PAL    = [BLUE, "#06B6D4", "#6366F1", "#A78BFA", "#EC4899",
          GREEN, AMBER, "#F97316", TEAL, "#84CC16"]

REJECTED_STATUSES = {"Canceled", "Cancelled", "Rejected"}

# ══════════════════════════════════════════════════════════════════════════════
# CSS  — warm dark palette + top-bar filters + keyboard icon fix
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/icon?family=Material+Icons+Round');

*, [data-testid] {{ font-family:'Inter',sans-serif; }}

/* ── APP BACKGROUND ── */
[data-testid="stAppViewContainer"] {{ background:#111827; }}
[data-testid="stHeader"] {{ background:transparent !important; }}
.block-container {{ padding:1rem 1.75rem 3rem; max-width:1680px; }}

/* ── SIDEBAR (upload-only, mostly hidden) ── */
[data-testid="stSidebar"] {{
    background:#1F2937;
    border-right:0.5px solid #374151;
    min-width:260px !important;
    max-width:260px !important;
}}
[data-testid="stSidebar"] * {{
    color:#D1D5DB !important;
    font-family:'Inter',sans-serif !important;
}}

/* ── KPI CARD ── */
.kpi {{
    background:#1F2937;
    border:0.5px solid #374151;
    border-radius:12px;
    padding:1rem 1.1rem;
    position:relative;
    overflow:hidden;
    height:100%;
}}
.kpi-icon {{
    position:absolute; top:.9rem; right:.9rem;
    width:32px; height:32px; border-radius:8px;
    display:flex; align-items:center; justify-content:center;
    font-size:.85rem; opacity:.9;
}}
.kpi-accent {{ position:absolute; top:0; left:0; width:3px; height:100%;
               border-radius:12px 0 0 12px; }}
.kpi-label  {{ font-size:.68rem; font-weight:600; text-transform:uppercase;
               letter-spacing:.08em; color:#6B7280; margin-bottom:.45rem; }}
.kpi-value  {{ font-size:1.7rem; font-weight:700; color:#F9FAFB;
               line-height:1; letter-spacing:-.03em; }}
.kpi-delta  {{ font-size:.72rem; font-weight:600; margin-top:.35rem;
               display:flex; align-items:center; gap:.25rem; }}
.kpi-sub    {{ font-size:.65rem; color:#4B5563; margin-top:.2rem; }}
.up         {{ color:{GREEN}; }}
.down       {{ color:{RED}; }}
.neu        {{ color:#6B7280; }}

/* ── SECTION HEADER ── */
.section-header {{
    font-size:.68rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.1em; color:#6B7280; padding:.35rem 0;
    border-bottom:0.5px solid #374151; margin:1.2rem 0 .9rem;
}}
.sub-label {{ font-size:.8rem; font-weight:600; color:#E5E7EB; margin-bottom:.4rem; }}

/* ── POPOVER PILL FILTERS ── */
/* font-size:0 on the button silences the built-in "expand_more" icon
   that Streamlit appends; restored on <p> so only the label shows */
[data-testid="stPopover"] button {{
    background:#111827 !important;
    border:0.5px solid #374151 !important;
    border-radius:999px !important;
    color:#9CA3AF !important;
    font-size:0 !important;
    font-weight:500 !important;
    padding:.22rem .85rem !important;
    min-height:30px !important;
    height:auto !important;
    width:100% !important;
    justify-content:center !important;
    white-space:nowrap !important;
    overflow:hidden !important;
}}
[data-testid="stPopover"] button p,
[data-testid="stPopover"] button [data-testid="stMarkdownContainer"] p {{
    font-size:.72rem !important;
    line-height:1.4 !important;
    color:#9CA3AF !important;
    font-weight:500 !important;
    margin:0 !important;
    overflow:hidden !important;
    text-overflow:ellipsis !important;
    white-space:nowrap !important;
}}
[data-testid="stPopover"] button:hover {{
    background:#1F2937 !important;
    border-color:#6B7280 !important;
}}
[data-testid="stPopover"] button:hover p,
[data-testid="stPopover"] button:hover [data-testid="stMarkdownContainer"] p {{
    color:#E5E7EB !important;
}}

/* ── COMPARISON BANNER ── */
.cmp-bar {{
    background:rgba(59,130,246,.08);
    border:0.5px solid rgba(59,130,246,.3);
    border-radius:8px;
    padding:.5rem .9rem; font-size:.75rem; color:#93C5FD;
    font-weight:500; margin-bottom:.9rem;
    display:flex; align-items:center; gap:.5rem; flex-wrap:wrap;
}}

/* ── TABS ── */
[data-testid="stTabs"] {{ border-bottom:0.5px solid #374151; }}
[data-testid="stTabs"] button {{
    color:#6B7280 !important; font-size:.82rem; font-weight:500;
    padding:.5rem 1rem; background:transparent !important;
    border-bottom:2px solid transparent !important;
    border-radius:0 !important; margin-bottom:-1px;
    transition: color .15s;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color:{BLUE} !important;
    border-bottom:2px solid {BLUE} !important;
    font-weight:700 !important;
}}
[data-testid="stTabs"] button:hover {{ color:#D1D5DB !important; }}

/* ── MULTISELECT TAGS ── */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background:rgba(59,130,246,.18) !important;
    color:#93C5FD !important;
    border:0.5px solid rgba(59,130,246,.4) !important;
    border-radius:5px !important; font-size:.7rem !important;
}}

/* ── SIDEBAR BUTTON ── */
div[data-testid="stButton"] button {{
    background:#374151; border:0.5px solid #4B5563;
    color:#E5E7EB !important; border-radius:8px;
    font-size:.75rem; padding:.35rem .9rem; width:100%; font-weight:500;
}}
div[data-testid="stButton"] button:hover {{ background:#4B5563; }}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {{
    border:0.5px solid #374151 !important;
    border-radius:8px !important;
}}
[data-testid="stDataFrame"] th {{
    background:#1F2937 !important; color:#9CA3AF !important;
    font-size:.7rem !important; font-weight:600 !important;
    text-transform:uppercase; letter-spacing:.06em !important;
}}
[data-testid="stDataFrame"] td {{
    background:#111827 !important; color:#E5E7EB !important;
    font-size:.8rem !important;
}}

/* ── BADGE ── */
.badge {{ display:inline-block; padding:.15rem .55rem;
          border-radius:20px; font-size:.68rem; font-weight:600; }}
.badge-up   {{ background:rgba(34,197,94,.18);  color:{GREEN}; }}
.badge-down {{ background:rgba(239,68,68,.18);  color:{RED}; }}

/* ── MULTISELECT: cap height so 5+ tags don't blow up the row ── */
[data-testid="stMultiSelect"] [data-baseweb="select"] > div:first-child {{
    max-height:64px; overflow-y:auto;
    scrollbar-width:thin; scrollbar-color:#374151 transparent;
}}

/* ── SIDEBAR FILE UPLOADER: clean up native button ── */
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {{
    background:#111827 !important;
    border:0.5px solid #374151 !important;
    border-radius:8px !important;
    padding:.5rem .75rem !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] section button {{
    background:#1F2937 !important;
    border:0.5px solid #4B5563 !important;
    color:#D1D5DB !important;
    border-radius:6px !important;
    font-size:.75rem !important;
    padding:.3rem .8rem !important;
    width:auto !important;
}}
[data-testid="stSidebar"] [data-testid="stFileUploader"] label {{
    font-size:.72rem !important;
    color:#9CA3AF !important;
    font-weight:500 !important;
}}

/* ── EXPORT BUTTON ── */
div[data-testid="stDownloadButton"] button {{
    background:#1F2937 !important;
    border:0.5px solid #374151 !important;
    color:#D1D5DB !important;
    border-radius:8px !important;
    font-size:.78rem !important;
    padding:.4rem 1rem !important;
    width:auto !important;
}}
div[data-testid="stDownloadButton"] button:hover {{
    background:#374151 !important;
    border-color:{BLUE} !important;
    color:{BLUE} !important;
}}

/* ── FIX: Material Icons font not available locally — hide all icon text ── */
span.material-icons,
span.material-icons-round,
span.material-icons-sharp,
span.material-icons-outlined,
span.material-symbols-outlined,
span.material-symbols-rounded {{
    font-size:0 !important;
    max-width:0 !important;
    overflow:hidden !important;
    display:inline-block !important;
    vertical-align:middle !important;
}}
/* Keep sidebar toggle button visible (just hide text inside) */
button[data-testid="baseButton-headerNoPadding"] {{
    overflow:hidden;
}}

#MainMenu, footer {{ visibility:hidden; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def process(file_bytes):
    import io
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    o  = xl.parse("Order Report")
    i  = xl.parse("Items Report")
    for df in [o, i]:
        df['Date']        = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()
        df['Week Number'] = df['Date'].dt.isocalendar().week.astype(int)
        df['Month']       = df['Date'].dt.month
        df['Month Name']  = df['Date'].dt.strftime('%B')
        df['Year']        = df['Date'].dt.year
    for col in ['Brand', 'Provider', 'Technology', 'Status', 'Location']:
        for df in [o, i]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()
    o['Sales']    = pd.to_numeric(o['Sales'],    errors='coerce').fillna(0)
    o['Discount'] = pd.to_numeric(o['Discount'], errors='coerce').fillna(0)
    i['Quantity'] = pd.to_numeric(i['Quantity'], errors='coerce').fillna(0)
    return o, i

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — upload only
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        "<div style='font-size:1.1rem;font-weight:700;color:#F9FAFB;"
        "padding:.4rem 0 .6rem;letter-spacing:-.01em'>📊 Alnumuw</div>",
        unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:.62rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.09em;color:#6B7280;margin-bottom:.3rem'>📂 Data Source</div>",
        unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Excel file (.xlsx)",
        type=["xlsx"],
        help="File stays local — never stored or sent anywhere",
        label_visibility="visible",
    )

    if uploaded:
        file_bytes = uploaded.read()
        st.markdown(
            f"<div style='font-size:.7rem;color:#34D399;margin:.3rem 0 .5rem'>"
            f"✅ <b>{uploaded.name}</b> &nbsp;"
            f"<span style='color:#6B7280'>{len(file_bytes)//1024} KB</span></div>",
            unsafe_allow_html=True)
    else:
        file_bytes = None
        st.markdown(
            "<div style='font-size:.72rem;color:#FBBF24;margin:.3rem 0 .5rem;"
            "line-height:1.5'>⬆️ Upload <b>Alnumuw_Data.xlsx</b> to begin</div>",
            unsafe_allow_html=True)

    st.markdown("<hr style='border:none;border-top:0.5px solid #374151;margin:.6rem 0'>",
                unsafe_allow_html=True)
    st.caption("Filter pills live above the dashboard →")

# ══════════════════════════════════════════════════════════════════════════════
# GATE — nothing loaded yet
# ══════════════════════════════════════════════════════════════════════════════
if not file_bytes:
    st.markdown("""
    <div style='display:flex;flex-direction:column;align-items:center;
                justify-content:center;min-height:72vh;gap:1.2rem;text-align:center;'>
      <div style='font-size:3.5rem'>📂</div>
      <div style='font-size:1.4rem;font-weight:700;color:#F9FAFB;letter-spacing:-.02em'>
        Upload your data to get started
      </div>
      <div style='font-size:.88rem;color:#6B7280;max-width:400px;line-height:1.7'>
        Click the <b style='color:#D1D5DB'>← arrow</b> at the top-left to open the sidebar,
        then upload <b style='color:#D1D5DB'>Alnumuw_Data.xlsx</b>.
      </div>
      <div style='background:#1F2937;border:0.5px solid #374151;border-radius:10px;
                  padding:.75rem 1.4rem;font-size:.78rem;color:#6B7280;margin-top:.4rem'>
        💡 Your file is never stored — it only exists for this session
      </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

try:
    df_all_o, df_all_i = process(file_bytes)
except Exception as e:
    st.error(f"❌ Could not read file — ensure it has sheets named "
             f"'Order Report' and 'Items Report'. Error: {e}")
    st.stop()

G_MIN = df_all_o['Date'].min().date()
G_MAX = df_all_o['Date'].max().date()

master = df_all_o[
    ['Order ID', 'Brand', 'Provider', 'Technology', 'Location', 'Status']
].merge(df_all_i[['Order ID', 'Items']].drop_duplicates(), on='Order ID', how='left')

# ══════════════════════════════════════════════════════════════════════════════
# CASCADING FILTER HELPER
# ══════════════════════════════════════════════════════════════════════════════
def avail(col, constraints):
    df = master.copy()
    for c, vals in constraints.items():
        if c != col and vals:
            df = df[df[c].isin(vals)]
    return sorted(df[col].dropna().unique())

# ══════════════════════════════════════════════════════════════════════════════
# TOP FILTER BAR  — popover pill design
# ══════════════════════════════════════════════════════════════════════════════

# ── Popover filter helper
def popover_filter(label, col_name, key, icon=""):
    """Render a pill button that opens a popover with a multiselect inside."""
    cx = {
        'Brand':      st.session_state.get('f_brand',  []),
        'Technology': st.session_state.get('f_tech',   []),
        'Provider':   st.session_state.get('f_prov',   []),
        'Location':   st.session_state.get('f_loc',    []),
        'Status':     st.session_state.get('f_status', []),
        'Items':      st.session_state.get('f_items',  []),
    }
    opts   = avail(col_name, cx)
    stored = st.session_state.get(key, [])
    current = [s for s in stored if s in opts]
    count   = len(current)
    pill    = f"{icon} {label}  ·  {count}" if count else f"{icon} {label}"
    with st.popover(pill, use_container_width=True):
        st.caption(f"Select {label.lower()} — empty = all")
        sel = st.multiselect(
            label, opts, default=current, key=key,
            placeholder=f"All ({len(opts)})",
            label_visibility="collapsed",
        )
    return sel if sel else opts

# ── Row 1: date range + comparison toggle + reset
_fc1, _fc2, _fc3 = st.columns([2.2, 2, 0.65])
with _fc1:
    date_range = st.date_input(
        "📅 Date range", [G_MIN, G_MAX],
        min_value=G_MIN, max_value=G_MAX,
        label_visibility="visible",
    )
sd = date_range[0] if len(date_range) == 2 else G_MIN
ed = date_range[1] if len(date_range) == 2 else G_MAX

n_days = (pd.Timestamp(ed) - pd.Timestamp(sd)).days + 1
cmp_e  = pd.Timestamp(sd) - pd.Timedelta(days=1)
cmp_s  = max(cmp_e - pd.Timedelta(days=n_days - 1), pd.Timestamp(G_MIN))

with _fc2:
    compare_on = st.toggle("🔁 Compare with previous period", value=False)
with _fc3:
    reset = st.button("↺ Reset", use_container_width=True)
    if reset:
        for k in ['f_brand', 'f_tech', 'f_prov', 'f_loc', 'f_status', 'f_items']:
            st.session_state.pop(k, None)
        st.rerun()

if compare_on:
    cr = st.date_input(
        "Compare to period", [cmp_s.date(), cmp_e.date()],
        min_value=G_MIN, max_value=G_MAX,
    )
    if len(cr) == 2:
        cmp_s, cmp_e = pd.Timestamp(cr[0]), pd.Timestamp(cr[1])

st.markdown("<div style='height:.3rem'></div>", unsafe_allow_html=True)

# ── Row 2: filter pills
_p1, _p2, _p3, _p4, _p5, _p6 = st.columns([1, 1, 1, 1, 1, 1])
with _p1: brand  = popover_filter("Brand",      "Brand",      "f_brand",  "🏷️")
with _p2: prov   = popover_filter("Aggregator", "Provider",   "f_prov",   "🚚")
with _p3: loc    = popover_filter("Branch",     "Location",   "f_loc",    "📍")
with _p4: tech   = popover_filter("Technology", "Technology", "f_tech",   "⚙️")
with _p5: status = popover_filter("Status",     "Status",     "f_status", "✅")
with _p6:
    i_opts    = avail('Items', {'Brand': brand, 'Provider': prov,
                                'Technology': tech, 'Status': status})
    stored_i  = st.session_state.get('f_items', [])
    current_i = [s for s in stored_i if s in i_opts]
    count_i   = len(current_i)
    pill_i    = f"🛒 Item  ·  {count_i}" if count_i else "🛒 Item"
    with st.popover(pill_i, use_container_width=True):
        st.caption("Select items — empty = all")
        item_raw = st.multiselect(
            "Item", i_opts, default=current_i, key="f_items",
            placeholder=f"All ({len(i_opts)})",
            label_visibility="collapsed",
        )
    item_f = item_raw if item_raw else i_opts

st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# FILTER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def fo(s=None, e=None):
    df = df_all_o
    s  = pd.Timestamp(s or sd)
    e  = pd.Timestamp(e or ed)
    m  = ((df['Date'] >= s) & (df['Date'] <= e) &
          df['Brand'].isin(brand) & df['Provider'].isin(prov) &
          df['Location'].isin(loc) & df['Status'].isin(status) &
          df['Technology'].isin(tech))
    return df[m]

def fi(s=None, e=None):
    df = df_all_i
    s  = pd.Timestamp(s or sd)
    e  = pd.Timestamp(e or ed)
    m  = ((df['Date'] >= s) & (df['Date'] <= e) &
          df['Brand'].isin(brand) & df['Provider'].isin(prov) &
          df['Technology'].isin(tech) & df['Status'].isin(status) &
          df['Items'].isin(item_f))
    if 'Location' in df.columns:
        m = m & df['Location'].isin(loc)
    return df[m]

def norm(df):
    d = df.copy(); d["Date"] = d["Date"].dt.normalize(); return d

# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATION & HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def agg(o, i):
    sales     = o['Sales'].sum()
    orders    = o['Order ID'].nunique()
    completed = o[o['Status'] == 'Completed']['Order ID'].nunique()
    rejected  = o[o['Status'].isin(REJECTED_STATUSES)]['Order ID'].nunique()
    fill_rate = (completed / orders * 100) if orders else 0
    return dict(
        sales=sales, orders=orders, aov=(sales / orders) if orders else 0,
        qty=i['Quantity'].sum(), disc=o['Discount'].sum(),
        completed=completed, rejected=rejected, fill_rate=fill_rate,
    )

def pct(a, b):
    if b and b != 0: return round((a - b) / abs(b) * 100, 1)
    return None

def delta_inline(v):
    if v is None: return '<span class="neu">—</span>'
    arr = "↑" if v >= 0 else "↓"
    cls = "up" if v >= 0 else "down"
    return f'<span class="{cls}">{arr} {abs(v):.1f}%</span>'

def color_growth(val):
    try:
        v = float(val)
        if v > 0: return 'color: #4ADE80; font-weight:600'
        if v < 0: return 'color: #F87171; font-weight:600'
    except (TypeError, ValueError):
        pass
    return 'color: #6B7280'

# ── Chart theme
DARK = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#9CA3AF", size=11),
    margin=dict(t=10, b=30, l=10, r=10),
)
_ck = {"n": 0}

def pc(fig, h=300):
    fig.update_layout(height=h, **DARK)
    fig.update_xaxes(showgrid=True, gridcolor="#1F2937", zeroline=False,
                     linecolor="#374151", tickfont=dict(size=10))
    fig.update_yaxes(showgrid=True, gridcolor="#1F2937", zeroline=False,
                     linecolor="#374151", tickfont=dict(size=10))
    _ck["n"] += 1
    st.plotly_chart(fig, use_container_width=True, key=f"c{_ck['n']}")

# ── KPI card with icon
def kpi_card(col, label, val_str, chg, sub, accent, icon="💰"):
    d  = delta_inline(chg) if compare_on else ""
    vs = f"<div class='kpi-sub'>vs {sub}</div>" if compare_on else ""
    col.markdown(f"""
    <div class="kpi">
      <div class="kpi-accent" style="background:{accent}"></div>
      <div class="kpi-icon" style="background:{accent}20">{icon}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val_str}</div>
      <div class="kpi-delta">{d}</div>
      {vs}
    </div>""", unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)

# ── Excel export helper
def to_excel_bytes(sheets: dict) -> bytes:
    """Convert a dict of {sheet_name: DataFrame} to Excel bytes."""
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()

def export_button(tab_name: str, sheets: dict):
    """Render a download button that exports filtered data to Excel."""
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:.65rem;color:#6B7280;margin-bottom:.25rem'>"
        f"Export reflects current filters · {sd} → {ed}</div>",
        unsafe_allow_html=True)
    xlsx = to_excel_bytes(sheets)
    fname = f"alnumuw_{tab_name.lower().replace(' ','_')}_{sd}_{ed}.xlsx"
    st.download_button(
        label="⬇️  Export to Excel",
        data=xlsx,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PULL & AGGREGATE
# ══════════════════════════════════════════════════════════════════════════════
o_cur = fo(sd, ed);        i_cur = fi(sd, ed)
o_cmp = fo(cmp_s, cmp_e); i_cmp = fi(cmp_s, cmp_e)
cur      = agg(o_cur, i_cur)
cmp_data = agg(o_cmp, i_cmp)

if compare_on:
    st.markdown(
        f'<div class="cmp-bar">🔁 <b>{sd} → {ed}</b>'
        f'&nbsp; vs &nbsp;<b>{cmp_s.date()} → {cmp_e.date()}</b>'
        f'&nbsp;·&nbsp; {n_days}-day windows</div>',
        unsafe_allow_html=True)

if o_cur.empty:
    st.warning("⚠️ No data for this selection. Adjust the filters or date range.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
t1, t2, t3, t4, t5 = st.tabs([
    "📊  Summary",
    "📦  Orders",
    "💰  Revenue & Sales",
    "🛒  Items",
    "🏪  Branches",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
with t1:
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)
    kpi_card(k1, "Total Revenue",   f"SAR {cur['sales']:,.0f}",
             pct(cur['sales'], cmp_data['sales']),
             f"SAR {cmp_data['sales']:,.0f}", BLUE, "💰")
    kpi_card(k2, "Total Orders",    f"{cur['orders']:,}",
             pct(cur['orders'], cmp_data['orders']),
             f"{cmp_data['orders']:,}", "#6366F1", "🛒")
    kpi_card(k3, "Avg Order Value", f"SAR {cur['aov']:,.2f}",
             pct(cur['aov'], cmp_data['aov']),
             f"SAR {cmp_data['aov']:,.2f}", AMBER, "📈")

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    k4, k5, k6 = st.columns(3)
    kpi_card(k4, "Completed Orders", f"{cur['completed']:,}",
             pct(cur['completed'], cmp_data['completed']),
             f"{cmp_data['completed']:,}", TEAL, "✅")
    kpi_card(k5, "Rejected Orders",  f"{cur['rejected']:,}",
             pct(cur['rejected'], cmp_data['rejected']),
             f"{cmp_data['rejected']:,}", RED, "❌")
    kpi_card(k6, "Fill Rate",        f"{cur['fill_rate']:.1f}%",
             pct(cur['fill_rate'], cmp_data['fill_rate']),
             f"{cmp_data['fill_rate']:.1f}%", PURPLE, "📊")

    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    section("Revenue Over Time")
    daily = norm(o_cur).groupby('Date')['Sales'].sum().reset_index()
    fig   = go.Figure()

    if compare_on and not o_cmp.empty:
        daily_c = norm(o_cmp).groupby('Date')['Sales'].sum().reset_index()
        daily['Day']   = range(1, len(daily) + 1)
        daily_c['Day'] = range(1, len(daily_c) + 1)
        fig.add_trace(go.Scatter(
            x=daily['Day'], y=daily['Sales'],
            name=f"Current  ({sd} → {ed})",
            line=dict(color=BLUE, width=2.5),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
            mode='lines+markers', marker=dict(size=4, color=BLUE),
            hovertemplate="Day %{x}<br><b>SAR %{y:,.0f}</b><extra>Current</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=daily_c['Day'], y=daily_c['Sales'],
            name=f"Previous ({cmp_s.date()} → {cmp_e.date()})",
            line=dict(color="#9CA3AF", width=1.8, dash='dot'),
            mode='lines+markers', marker=dict(size=4, color="#9CA3AF"),
            hovertemplate="Day %{x}<br><b>SAR %{y:,.0f}</b><extra>Previous</extra>",
        ))
        fig.update_layout(xaxis_title="Day of Period",
                          legend=dict(orientation='h', y=1.15, x=0,
                                      bgcolor='rgba(0,0,0,0)'))
    else:
        fig.add_trace(go.Scatter(
            x=daily['Date'], y=daily['Sales'], name="Revenue",
            line=dict(color=BLUE, width=2.5),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)', mode='lines',
            hovertemplate="%{x|%b %d}<br><b>SAR %{y:,.0f}</b><extra></extra>",
        ))
        fig.update_layout(xaxis=dict(tickformat="%b %d"))

    pc(fig, 260)

    section("Breakdown")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="sub-label">By Aggregator</div>', unsafe_allow_html=True)
        pv = (o_cur.groupby('Provider').agg(Revenue=('Sales', 'sum'))
                   .reset_index().sort_values('Revenue', ascending=False))
        fig = px.bar(pv, x='Revenue', y='Provider', orientation='h',
                     text_auto='.2s', color_discrete_sequence=[BLUE])
        fig.update_traces(marker_color=BLUE, textfont_size=10)
        fig.update_layout(showlegend=False, yaxis=dict(categoryorder='total ascending'))
        pc(fig, 240)
    with c2:
        st.markdown('<div class="sub-label">By Brand (Top 8)</div>', unsafe_allow_html=True)
        bb = (o_cur.groupby('Brand')['Sales'].sum()
                   .sort_values(ascending=False).head(8).reset_index())
        fig = px.bar(bb, x='Sales', y='Brand', orientation='h',
                     text_auto='.2s', color_discrete_sequence=["#6366F1"])
        fig.update_layout(showlegend=False, yaxis=dict(categoryorder='total ascending'))
        pc(fig, 240)
    with c3:
        st.markdown('<div class="sub-label">By Technology</div>', unsafe_allow_html=True)
        td = o_cur.groupby('Technology')['Sales'].sum().reset_index()
        fig = px.pie(td, values='Sales', names='Technology', hole=0.55,
                     color_discrete_sequence=[BLUE, "#6366F1", GREEN, AMBER])
        fig.update_traces(textposition='outside', textinfo='percent+label', textfont_size=11)
        fig.update_layout(showlegend=False)
        pc(fig, 240)

    section("Aggregator Performance — click any column header to sort ↕")
    pt = (o_cur.groupby('Provider').agg(
            Revenue=('Sales', 'sum'),
            Orders=('Order ID', 'nunique'),
            AOV=('Sales', 'mean'),
            Discount=('Discount', 'sum'),
            Completed=('Status', lambda x: (x == 'Completed').sum()),
            Rejected=('Status', lambda x: x.isin(REJECTED_STATUSES).sum()),
          ).reset_index().sort_values('Revenue', ascending=False).reset_index(drop=True))
    pt['Fill Rate %'] = (pt['Completed'] / pt['Orders'] * 100).round(1)

    if compare_on and not o_cmp.empty:
        pc2 = (o_cmp.groupby('Provider')
                    .agg(Rev_Prev=('Sales', 'sum'), Ord_Prev=('Order ID', 'nunique'))
                    .reset_index())
        pt = pt.merge(pc2, on='Provider', how='left').fillna(0)
        pt['Rev Diff']   = (pt['Revenue'] - pt['Rev_Prev']).round(0)
        pt['Rev Growth'] = pt.apply(lambda r: pct(r['Revenue'], r['Rev_Prev']), axis=1)
        pt['Ord Growth'] = pt.apply(lambda r: pct(r['Orders'],  r['Ord_Prev']),  axis=1)
        disp = pt[['Provider', 'Revenue', 'Rev_Prev', 'Rev Diff', 'Rev Growth',
                   'Orders', 'Ord_Prev', 'Ord Growth', 'AOV', 'Fill Rate %']].copy()
        disp.columns = ['Aggregator', 'Revenue (SAR)', 'Prev Revenue (SAR)',
                        'Diff (SAR)', 'Rev Growth %',
                        'Orders', 'Prev Orders', 'Ord Growth %',
                        'AOV (SAR)', 'Fill Rate %']
        grw = ['Rev Growth %', 'Ord Growth %']
        styled = disp.style.applymap(color_growth, subset=grw)
    else:
        disp = pt[['Provider', 'Revenue', 'Orders', 'AOV', 'Discount',
                   'Completed', 'Rejected', 'Fill Rate %']].copy()
        disp.columns = ['Aggregator', 'Revenue (SAR)', 'Orders', 'AOV (SAR)',
                        'Discount (SAR)', 'Completed', 'Rejected', 'Fill Rate %']
        styled = disp.style

    st.dataframe(
        styled.format({
            col: "{:,.0f}" for col in disp.columns
            if any(x in col for x in ('SAR', 'Orders', 'Prev Orders',
                                       'Completed', 'Rejected'))
        } | {"Fill Rate %": "{:.1f}%",
             **({k: "{:+.1f}" for k in ['Rev Growth %', 'Ord Growth %']}
                if compare_on else {})}),
        use_container_width=True, hide_index=True,
    )

    # ── Export
    export_cols = ['Order ID', 'Date', 'Brand', 'Provider', 'Technology',
                   'Location', 'Status', 'Sales', 'Discount']
    export_button("Summary", {
        "Aggregator Performance": disp.reset_index(drop=True),
        "Filtered Orders":        o_cur[[c for c in export_cols if c in o_cur.columns]],
    })
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ORDERS
# ─────────────────────────────────────────────────────────────────────────────
with t2:
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    cmp_days = max((pd.Timestamp(cmp_e) - pd.Timestamp(cmp_s)).days + 1, 1)
    apd      = cur['orders'] / n_days
    cmp_apd  = cmp_data['orders'] / cmp_days

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "Total Orders",     f"{cur['orders']:,}",
             pct(cur['orders'], cmp_data['orders']),
             f"{cmp_data['orders']:,}", BLUE, "🛒")
    kpi_card(k2, "Avg Orders / Day", f"{apd:.1f}",
             pct(apd, cmp_apd), f"{cmp_apd:.1f}", "#6366F1", "📅")
    kpi_card(k3, "Avg Order Value",  f"SAR {cur['aov']:,.2f}",
             pct(cur['aov'], cmp_data['aov']),
             f"SAR {cmp_data['aov']:,.2f}", AMBER, "💳")
    kpi_card(k4, "Rejected Orders",  f"{cur['rejected']:,}",
             pct(cur['rejected'], cmp_data['rejected']),
             f"{cmp_data['rejected']:,}", RED, "❌")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    section("Daily Orders Trend")
    od  = norm(o_cur).groupby('Date')['Order ID'].nunique().reset_index(name='Orders')
    fig = go.Figure()

    if compare_on and not o_cmp.empty:
        od2 = norm(o_cmp).groupby('Date')['Order ID'].nunique().reset_index(name='Orders')
        od['Day']  = range(1, len(od) + 1)
        od2['Day'] = range(1, len(od2) + 1)
        fig.add_trace(go.Scatter(
            x=od['Day'], y=od['Orders'],
            name=f"Current  ({sd} → {ed})",
            line=dict(color=BLUE, width=2.5),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)',
            mode='lines+markers', marker=dict(size=4),
            hovertemplate="Day %{x}<br><b>%{y:,} orders</b><extra>Current</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=od2['Day'], y=od2['Orders'],
            name=f"Previous ({cmp_s.date()} → {cmp_e.date()})",
            line=dict(color="#9CA3AF", width=1.8, dash='dot'),
            mode='lines+markers', marker=dict(size=4, color="#9CA3AF"),
            hovertemplate="Day %{x}<br><b>%{y:,} orders</b><extra>Previous</extra>",
        ))
        fig.update_layout(xaxis_title="Day of Period",
                          legend=dict(orientation='h', y=1.15, x=0,
                                      bgcolor='rgba(0,0,0,0)'))
    else:
        fig.add_trace(go.Scatter(
            x=od['Date'], y=od['Orders'], name="Orders",
            line=dict(color=BLUE, width=2.5),
            fill='tozeroy', fillcolor='rgba(59,130,246,0.08)', mode='lines',
            hovertemplate="%{x|%b %d}<br><b>%{y:,} orders</b><extra></extra>",
        ))
        fig.update_layout(xaxis=dict(tickformat="%b %d"))

    pc(fig, 250)

    c1, c2 = st.columns(2)
    with c1:
        section("Orders by Day of Week")
        o2       = o_cur.copy(); o2['Weekday'] = o2['Date'].dt.day_name()
        wd_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        wd = (o2.groupby('Weekday')['Order ID'].nunique()
                .reindex(wd_order).fillna(0).reset_index(name='Orders'))
        fig = px.bar(wd, x='Weekday', y='Orders', color='Orders',
                     color_continuous_scale=[[0, '#1E3A5F'], [1, BLUE]], text_auto=True)
        fig.update_layout(coloraxis_showscale=False, showlegend=False,
                          xaxis_tickangle=-30)
        pc(fig, 240)
    with c2:
        section("Orders by Status")
        sf  = o_cur.groupby('Status')['Order ID'].nunique().reset_index(name='Orders')
        clr = {s: (GREEN if s == 'Completed'
                   else RED if s in REJECTED_STATUSES else AMBER)
               for s in sf['Status']}
        fig = px.pie(sf, values='Orders', names='Status', hole=0.58,
                     color='Status', color_discrete_map=clr)
        fig.update_traces(textposition='outside', textinfo='percent+label', textfont_size=11)
        fig.update_layout(showlegend=False)
        pc(fig, 240)

    section("Orders by Brand — click any column header to sort ↕")
    bt = (o_cur.groupby('Brand').agg(
            Orders=('Order ID', 'nunique'),
            Revenue=('Sales', 'sum'),
            AOV=('Sales', 'mean'),
            Completed=('Status', lambda x: (x == 'Completed').sum()),
            Rejected=('Status', lambda x: x.isin(REJECTED_STATUSES).sum()),
          ).reset_index().sort_values('Orders', ascending=False).reset_index(drop=True))
    bt['Fill Rate %'] = (bt['Completed'] / bt['Orders'] * 100).round(1)

    if compare_on and not o_cmp.empty:
        bc2 = (o_cmp.groupby('Brand')
                    .agg(Ord_Prev=('Order ID', 'nunique'), Rev_Prev=('Sales', 'sum'))
                    .reset_index())
        bt = bt.merge(bc2, on='Brand', how='left').fillna(0)
        bt['Ord Growth'] = bt.apply(lambda r: pct(r['Orders'],  r['Ord_Prev']),  axis=1)
        bt['Rev Growth'] = bt.apply(lambda r: pct(r['Revenue'], r['Rev_Prev']), axis=1)
        disp = bt[['Brand', 'Orders', 'Ord_Prev', 'Ord Growth',
                   'Revenue', 'Rev_Prev', 'Rev Growth', 'AOV', 'Fill Rate %']].copy()
        disp.columns = ['Brand', 'Orders', 'Prev Orders', 'Ord Growth %',
                        'Revenue (SAR)', 'Prev Revenue (SAR)', 'Rev Growth %',
                        'AOV (SAR)', 'Fill Rate %']
        styled = disp.style.applymap(color_growth, subset=['Ord Growth %', 'Rev Growth %'])
    else:
        disp = bt[['Brand', 'Orders', 'Revenue', 'AOV',
                   'Completed', 'Rejected', 'Fill Rate %']].copy()
        disp.columns = ['Brand', 'Orders', 'Revenue (SAR)', 'AOV (SAR)',
                        'Completed', 'Rejected', 'Fill Rate %']
        styled = disp.style

    st.dataframe(
        styled.format({
            col: "{:,.0f}" for col in disp.columns
            if any(x in col for x in ('SAR', 'Orders', 'Prev Orders',
                                       'Completed', 'Rejected'))
        } | {"Fill Rate %": "{:.1f}%",
             **({k: "{:+.1f}" for k in ['Ord Growth %', 'Rev Growth %']}
                if compare_on else {})}),
        use_container_width=True, hide_index=True,
    )

    # ── Export
    export_cols = ['Order ID', 'Date', 'Brand', 'Provider', 'Technology',
                   'Location', 'Status', 'Sales', 'Discount']
    export_button("Orders", {
        "Orders by Brand": disp.reset_index(drop=True),
        "Filtered Orders": o_cur[[c for c in export_cols if c in o_cur.columns]],
    })
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — REVENUE & SALES
# ─────────────────────────────────────────────────────────────────────────────
with t3:
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    gross = cur['sales'];       disc = cur['disc'];    net = gross - disc
    cg    = cmp_data['sales'];  cd   = cmp_data['disc']; cn = cg - cd

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "Gross Revenue",   f"SAR {gross:,.0f}",
             pct(gross, cg), f"SAR {cg:,.0f}", BLUE, "💰")
    kpi_card(k2, "Net Revenue",     f"SAR {net:,.0f}",
             pct(net, cn),   f"SAR {cn:,.0f}", GREEN, "📈")
    kpi_card(k3, "Total Discount",  f"SAR {disc:,.0f}",
             pct(disc, cd),  f"SAR {cd:,.0f}", AMBER, "🏷️")
    kpi_card(k4, "Avg Order Value", f"SAR {cur['aov']:,.2f}",
             pct(cur['aov'], cmp_data['aov']),
             f"SAR {cmp_data['aov']:,.2f}", PURPLE, "🧾")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    section("Daily Revenue & Discount")
    rd  = norm(o_cur).groupby('Date').agg(
            Revenue=('Sales', 'sum'), Discount=('Discount', 'sum')).reset_index()
    fig = go.Figure()

    if compare_on and not o_cmp.empty:
        rd2 = norm(o_cmp).groupby('Date').agg(
                Revenue=('Sales', 'sum'), Discount=('Discount', 'sum')).reset_index()
        rd['Day']  = range(1, len(rd) + 1)
        rd2['Day'] = range(1, len(rd2) + 1)
        fig.add_trace(go.Scatter(
            x=rd['Day'], y=rd['Revenue'], name="Revenue · Current",
            line=dict(color=BLUE, width=2.5), fill='tozeroy',
            fillcolor='rgba(59,130,246,0.07)', mode='lines+markers',
            marker=dict(size=4),
            hovertemplate="Day %{x}<br><b>SAR %{y:,.0f}</b><extra>Revenue Current</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=rd2['Day'], y=rd2['Revenue'], name="Revenue · Previous",
            line=dict(color="#9CA3AF", width=1.8, dash='dot'),
            mode='lines+markers', marker=dict(size=4, color="#9CA3AF"),
            hovertemplate="Day %{x}<br><b>SAR %{y:,.0f}</b><extra>Revenue Prev</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=rd['Day'], y=rd['Discount'], name="Discount",
            line=dict(color=AMBER, width=1.5, dash='dash'), mode='lines',
            hovertemplate="Day %{x}<br><b>SAR %{y:,.0f}</b><extra>Discount</extra>",
        ))
        fig.update_layout(xaxis_title="Day of Period")
    else:
        fig.add_trace(go.Scatter(
            x=rd['Date'], y=rd['Revenue'], name="Revenue",
            line=dict(color=BLUE, width=2.5), fill='tozeroy',
            fillcolor='rgba(59,130,246,0.07)', mode='lines',
            hovertemplate="%{x|%b %d}<br><b>SAR %{y:,.0f}</b><extra>Revenue</extra>",
        ))
        fig.add_trace(go.Scatter(
            x=rd['Date'], y=rd['Discount'], name="Discount",
            line=dict(color=AMBER, width=1.8, dash='dot'), mode='lines',
            hovertemplate="%{x|%b %d}<br><b>SAR %{y:,.0f}</b><extra>Discount</extra>",
        ))
        fig.update_layout(xaxis=dict(tickformat="%b %d"))

    fig.update_layout(legend=dict(orientation='h', y=1.15, x=0, bgcolor='rgba(0,0,0,0)'))
    pc(fig, 260)

    col1, col2 = st.columns(2)
    with col1:
        section("Weekly Revenue")
        wk = (o_cur.groupby(['Year', 'Week Number'])['Sales'].sum().reset_index())
        wk['Wk'] = wk['Year'].astype(str) + '-W' + wk['Week Number'].astype(str).str.zfill(2)
        wk = wk.sort_values(['Year', 'Week Number'])
        if compare_on and not o_cmp.empty:
            wk2 = o_cmp.groupby(['Year', 'Week Number'])['Sales'].sum().reset_index()
            wk2['Wk'] = (wk2['Year'].astype(str) + '-W' +
                         wk2['Week Number'].astype(str).str.zfill(2))
            wk['Type'] = 'Current'; wk2['Type'] = 'Previous'
            fig = px.bar(pd.concat([wk, wk2]), x='Wk', y='Sales', color='Type',
                         barmode='group',
                         color_discrete_map={'Current': BLUE, 'Previous': GRAY},
                         text_auto='.2s')
            fig.update_layout(legend=dict(orientation='h', y=1.12, x=0,
                                          bgcolor='rgba(0,0,0,0)'))
        else:
            fig = px.bar(wk, x='Wk', y='Sales', text_auto='.2s',
                         color_discrete_sequence=[BLUE])
            fig.update_traces(marker_color=BLUE)
            fig.update_layout(showlegend=False)
        fig.update_layout(xaxis_tickangle=-40)
        pc(fig, 250)

    with col2:
        section("Monthly Revenue")
        mn = (o_cur.groupby(['Year', 'Month', 'Month Name'])['Sales']
                   .sum().reset_index().sort_values(['Year', 'Month']))
        mn['Period'] = mn['Month Name'] + ' ' + mn['Year'].astype(str)
        if compare_on and not o_cmp.empty:
            mn2 = (o_cmp.groupby(['Year', 'Month', 'Month Name'])['Sales']
                       .sum().reset_index().sort_values(['Year', 'Month']))
            mn2['Period'] = mn2['Month Name'] + ' ' + mn2['Year'].astype(str)
            mn['Type'] = 'Current'; mn2['Type'] = 'Previous'
            fig = px.bar(pd.concat([mn, mn2]), x='Period', y='Sales', color='Type',
                         barmode='group',
                         color_discrete_map={'Current': BLUE, 'Previous': GRAY},
                         text_auto='.2s')
            fig.update_layout(legend=dict(orientation='h', y=1.12, x=0,
                                          bgcolor='rgba(0,0,0,0)'))
        else:
            fig = px.bar(mn, x='Period', y='Sales', text_auto='.2s',
                         color_discrete_sequence=[BLUE])
            fig.update_traces(marker_color=BLUE)
            fig.update_layout(showlegend=False)
        fig.update_layout(xaxis_tickangle=-20)
        pc(fig, 250)

    section("Revenue by Aggregator & Brand")
    d1, d2 = st.columns([1, 1.8])
    with d1:
        pv = o_cur.groupby('Provider')['Sales'].sum().reset_index()
        fig = px.pie(pv, values='Sales', names='Provider', hole=0.52,
                     color_discrete_sequence=PAL)
        fig.update_traces(textposition='outside', textinfo='percent+label', textfont_size=10)
        fig.update_layout(showlegend=False)
        pc(fig, 270)
    with d2:
        section("Brand Revenue — click any column header to sort ↕")
        bb = (o_cur.groupby('Brand')
                   .agg(Revenue=('Sales', 'sum'), Orders=('Order ID', 'nunique'),
                        AOV=('Sales', 'mean'))
                   .reset_index().sort_values('Revenue', ascending=False).reset_index(drop=True))
        if compare_on and not o_cmp.empty:
            bc2 = o_cmp.groupby('Brand')['Sales'].sum().reset_index(name='Rev_Prev')
            bb = bb.merge(bc2, on='Brand', how='left').fillna(0)
            bb['Diff']   = (bb['Revenue'] - bb['Rev_Prev']).round(0)
            bb['Growth'] = bb.apply(lambda r: pct(r['Revenue'], r['Rev_Prev']), axis=1)
            disp = bb[['Brand', 'Revenue', 'Rev_Prev', 'Diff', 'Growth',
                        'Orders', 'AOV']].copy()
            disp.columns = ['Brand', 'Revenue (SAR)', 'Prev Revenue (SAR)',
                            'Diff (SAR)', 'Growth %', 'Orders', 'AOV (SAR)']
            styled = disp.style.applymap(color_growth, subset=['Growth %'])
        else:
            disp = bb[['Brand', 'Revenue', 'Orders', 'AOV']].copy()
            disp.columns = ['Brand', 'Revenue (SAR)', 'Orders', 'AOV (SAR)']
            styled = disp.style
        st.dataframe(
            styled.format({
                col: "{:,.0f}" for col in disp.columns
                if 'SAR' in col or col == 'Orders'
            } | ({} if not compare_on else {"Growth %": "{:+.1f}"})),
            use_container_width=True, hide_index=True,
        )

    # ── Export (outside columns)
    export_cols = ['Order ID', 'Date', 'Brand', 'Provider', 'Technology',
                   'Location', 'Status', 'Sales', 'Discount']
    daily_export = norm(o_cur).groupby('Date').agg(
        Revenue=('Sales', 'sum'), Discount=('Discount', 'sum'),
        Orders=('Order ID', 'nunique')).reset_index()
    export_button("Revenue_Sales", {
        "Brand Revenue":    disp.reset_index(drop=True),
        "Daily Revenue":    daily_export,
        "Filtered Orders":  o_cur[[c for c in export_cols if c in o_cur.columns]],
    })
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ITEMS
# ─────────────────────────────────────────────────────────────────────────────
with t4:
    if i_cur.empty:
        st.warning("No item data for this selection.")
    else:
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

        top_item = i_cur.groupby('Items')['Quantity'].sum().idxmax()
        top_qty  = int(i_cur.groupby('Items')['Quantity'].sum().max())
        cmp_top  = (int(i_cmp.groupby('Items')['Quantity'].sum()
                       .get(top_item, 0)) if compare_on and not i_cmp.empty else 0)
        tot_qty  = int(i_cur['Quantity'].sum())
        cmp_qty2 = (int(i_cmp['Quantity'].sum())
                    if compare_on and not i_cmp.empty else 0)

        k1, k2, k3, k4 = st.columns(4)
        kpi_card(k1, "Unique Items",      f"{i_cur['Items'].nunique():,}",
                 None, "—", BLUE, "🗂️")
        kpi_card(k2, "Total Units Sold",  f"{tot_qty:,}",
                 pct(tot_qty, cmp_qty2), f"{cmp_qty2:,}", GREEN, "📦")
        kpi_card(k3, "Best Seller",
                 (top_item[:18] + "…") if len(top_item) > 18 else top_item,
                 None, "—", AMBER, "🏆")
        kpi_card(k4, "Best Seller Units", f"{top_qty:,}",
                 pct(top_qty, cmp_top) if compare_on else None,
                 f"{cmp_top:,}", PURPLE, "⭐")

        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

        section("Top 15 Items by Quantity Sold")
        t15 = (i_cur.groupby('Items')['Quantity']
                    .sum().sort_values(ascending=False).head(15).reset_index())

        if compare_on and not i_cmp.empty:
            t15c = i_cmp.groupby('Items')['Quantity'].sum().reset_index(name='Qty_cmp')
            t15  = t15.merge(t15c, on='Items', how='left').fillna(0)
            fig  = go.Figure()
            fig.add_trace(go.Bar(
                x=t15['Items'], y=t15['Quantity'], name='Current',
                marker_color=BLUE, text=t15['Quantity'].astype(int),
                textposition='outside',
                hovertemplate="%{x}<br><b>%{y:,} units</b><extra>Current</extra>",
            ))
            fig.add_trace(go.Bar(
                x=t15['Items'], y=t15['Qty_cmp'], name='Previous',
                marker_color=GRAY, text=t15['Qty_cmp'].astype(int),
                textposition='outside',
                hovertemplate="%{x}<br><b>%{y:,} units</b><extra>Previous</extra>",
            ))
            fig.update_layout(barmode='group',
                              legend=dict(orientation='h', y=1.12, x=0,
                                          bgcolor='rgba(0,0,0,0)'),
                              xaxis_tickangle=-35)
        else:
            fig = px.bar(t15, x='Items', y='Quantity',
                         color_discrete_sequence=[BLUE], text_auto=True)
            fig.update_traces(marker_color=BLUE)
            fig.update_layout(xaxis_tickangle=-35, showlegend=False)

        pc(fig, 310)

        c1, c2 = st.columns(2)
        with c1:
            section("Item Trend — Top 6")
            top6 = i_cur.groupby('Items')['Quantity'].sum().nlargest(6).index.tolist()
            it   = (norm(i_cur[i_cur['Items'].isin(top6)])
                        .groupby(['Date', 'Items'])['Quantity'].sum().reset_index())
            if it['Date'].nunique() >= 2:
                fig = px.line(it, x='Date', y='Quantity', color='Items',
                              line_shape='spline', color_discrete_sequence=PAL)
                fig.update_layout(legend=dict(orientation='h', y=1.12, x=0,
                                              bgcolor='rgba(0,0,0,0)'),
                                  legend_title_text='',
                                  xaxis=dict(tickformat="%b %d"))
                fig.update_traces(
                    hovertemplate="%{x|%b %d}<br><b>%{y:,} units</b><extra>%{fullData.name}</extra>")
                pc(fig, 270)
            else:
                st.info("Widen the date range to see item trends.")

        with c2:
            section("Top 10 Items by Aggregator")
            top10i = i_cur.groupby('Items')['Quantity'].sum().nlargest(10).index
            ib = (i_cur[i_cur['Items'].isin(top10i)]
                     .groupby(['Items', 'Provider'])['Quantity'].sum().reset_index())
            fig = px.bar(ib, x='Items', y='Quantity', color='Provider',
                         barmode='stack', color_discrete_sequence=PAL)
            fig.update_layout(xaxis_tickangle=-35, legend_title_text='',
                              legend=dict(orientation='h', y=1.12, x=0,
                                          bgcolor='rgba(0,0,0,0)'))
            pc(fig, 270)

        section("Full Item Table (Top 50) — click any column header to sort ↕")
        has_amount = 'Total Amount' in i_cur.columns
        full_agg = {'Qty': ('Quantity', 'sum'), 'Orders': ('Order ID', 'nunique')}
        if has_amount:
            full_agg['Revenue'] = ('Total Amount', 'sum')
        full = (i_cur.groupby('Items').agg(**full_agg)
                     .reset_index().sort_values('Qty', ascending=False)
                     .head(50).reset_index(drop=True))

        if compare_on and not i_cmp.empty:
            cmp_agg = {'Qty_Prev': ('Quantity', 'sum')}
            if has_amount:
                cmp_agg['Rev_Prev'] = ('Total Amount', 'sum')
            fc2 = i_cmp.groupby('Items').agg(**cmp_agg).reset_index()
            full = full.merge(fc2, on='Items', how='left').fillna(0)
            full['Qty Diff']   = (full['Qty'] - full['Qty_Prev']).astype(int)
            full['Qty Growth'] = full.apply(lambda r: pct(r['Qty'], r['Qty_Prev']), axis=1)
            if has_amount:
                full['Rev Diff']   = (full['Revenue'] - full['Rev_Prev']).round(0)
                full['Rev Growth'] = full.apply(
                    lambda r: pct(r['Revenue'], r['Rev_Prev']), axis=1)

            base_cols  = ['Items', 'Qty', 'Qty_Prev', 'Qty Diff', 'Qty Growth', 'Orders']
            base_names = ['Item', 'Current Units', 'Prev Units', 'Unit Diff',
                          'Qty Growth %', 'Orders']
            if has_amount:
                base_cols  += ['Revenue', 'Rev_Prev', 'Rev Diff', 'Rev Growth']
                base_names += ['Revenue (SAR)', 'Prev Revenue (SAR)',
                               'Rev Diff (SAR)', 'Rev Growth %']
            disp = full[base_cols].copy(); disp.columns = base_names
            grw = [c for c in disp.columns if 'Growth' in c]
            styled = disp.style.applymap(color_growth, subset=grw)
        else:
            base_cols  = ['Items', 'Qty', 'Orders']
            base_names = ['Item', 'Units Sold', 'Orders']
            if has_amount:
                base_cols  += ['Revenue']
                base_names += ['Revenue (SAR)']
            disp = full[base_cols].copy(); disp.columns = base_names
            styled = disp.style

        st.dataframe(
            styled.format({
                col: "{:,.0f}" for col in disp.columns
                if any(x in col for x in ('Units', 'Orders', 'SAR', 'Diff'))
                and 'Growth' not in col
            } | ({k: "{:+.1f}" for k in [c for c in disp.columns if 'Growth' in c]}
                 if compare_on else {})),
            use_container_width=True, hide_index=True,
        )

        # ── Export
        item_export_cols = ['Order ID', 'Date', 'Brand', 'Provider',
                            'Technology', 'Status', 'Items', 'Quantity']
        if 'Total Amount' in i_cur.columns:
            item_export_cols.append('Total Amount')
        export_button("Items", {
            "Items Summary":   disp.reset_index(drop=True),
            "Filtered Items":  i_cur[[c for c in item_export_cols if c in i_cur.columns]],
        })
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — BRANCHES
# ─────────────────────────────────────────────────────────────────────────────
with t5:
    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    branches_cur   = o_cur['Location'].nunique()
    branches_cmp   = o_cmp['Location'].nunique() if compare_on and not o_cmp.empty else 0
    top_branch_rev = o_cur.groupby('Location')['Sales'].sum().max() if not o_cur.empty else 0
    top_branch_nm  = (o_cur.groupby('Location')['Sales'].sum().idxmax()
                      if not o_cur.empty else "—")

    k1, k2, k3, k4 = st.columns(4)
    kpi_card(k1, "Active Branches",    f"{branches_cur:,}",
             pct(branches_cur, branches_cmp) if compare_on else None,
             f"{branches_cmp:,}", BLUE, "🏪")
    kpi_card(k2, "Top Branch Revenue", f"SAR {top_branch_rev:,.0f}",
             None, "—", GREEN, "🏆")
    kpi_card(k3, "Top Branch",
             (top_branch_nm[:18] + "…") if len(str(top_branch_nm)) > 18
             else str(top_branch_nm),
             None, "—", AMBER, "📍")
    kpi_card(k4, "Overall Fill Rate",  f"{cur['fill_rate']:.1f}%",
             pct(cur['fill_rate'], cmp_data['fill_rate']) if compare_on else None,
             f"{cmp_data['fill_rate']:.1f}%", PURPLE, "📊")

    st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)

    section("Revenue by Branch (Top 20)")
    br_rev = (o_cur.groupby('Location')['Sales'].sum()
                   .sort_values(ascending=False).head(20).reset_index())
    fig = px.bar(br_rev, x='Sales', y='Location', orientation='h',
                 text_auto='.2s', color_discrete_sequence=[BLUE])
    fig.update_traces(marker_color=BLUE, textfont_size=10)
    fig.update_layout(showlegend=False, yaxis=dict(categoryorder='total ascending'))
    pc(fig, max(280, len(br_rev) * 24))

    section("Branch Performance — click any column header to sort ↕")
    br = (o_cur.groupby('Location').agg(
            Revenue=('Sales', 'sum'),
            Orders=('Order ID', 'nunique'),
            AOV=('Sales', 'mean'),
            Discount=('Discount', 'sum'),
            Completed=('Status', lambda x: (x == 'Completed').sum()),
            Rejected=('Status', lambda x: x.isin(REJECTED_STATUSES).sum()),
          ).reset_index().sort_values('Revenue', ascending=False).reset_index(drop=True))
    br['Fill Rate %'] = (br['Completed'] / br['Orders'] * 100).round(1)
    br['Rank']        = range(1, len(br) + 1)

    if compare_on and not o_cmp.empty:
        bc2 = (o_cmp.groupby('Location').agg(
                Rev_Prev=('Sales', 'sum'),
                Ord_Prev=('Order ID', 'nunique'),
                Comp_Prev=('Status', lambda x: (x == 'Completed').sum()),
                Rej_Prev=('Status', lambda x: x.isin(REJECTED_STATUSES).sum()),
               ).reset_index())
        br = br.merge(bc2, on='Location', how='left').fillna(0)
        br['Rev Diff']   = (br['Revenue'] - br['Rev_Prev']).round(0)
        br['Rev Growth'] = br.apply(lambda r: pct(r['Revenue'], r['Rev_Prev']), axis=1)
        br['Ord Growth'] = br.apply(lambda r: pct(r['Orders'],  r['Ord_Prev']),  axis=1)
        br['Fr_Prev']    = (br['Comp_Prev'] / br['Ord_Prev'].replace(0, 1) * 100).round(1)
        disp = br[['Rank', 'Location', 'Revenue', 'Rev_Prev', 'Rev Diff', 'Rev Growth',
                   'Orders', 'Ord_Prev', 'Ord Growth',
                   'Completed', 'Rejected', 'Fill Rate %', 'Fr_Prev', 'AOV']].copy()
        disp.columns = ['#', 'Branch', 'Revenue (SAR)', 'Prev Revenue (SAR)',
                        'Diff (SAR)', 'Rev Growth %',
                        'Orders', 'Prev Orders', 'Ord Growth %',
                        'Completed', 'Rejected', 'Fill Rate %', 'Prev Fill Rate %',
                        'AOV (SAR)']
        grw = ['Rev Growth %', 'Ord Growth %']
        styled = disp.style.applymap(color_growth, subset=grw)
    else:
        disp = br[['Rank', 'Location', 'Revenue', 'Orders', 'AOV',
                   'Completed', 'Rejected', 'Fill Rate %', 'Discount']].copy()
        disp.columns = ['#', 'Branch', 'Revenue (SAR)', 'Orders', 'AOV (SAR)',
                        'Completed', 'Rejected', 'Fill Rate %', 'Discount (SAR)']
        styled = disp.style

    st.dataframe(
        styled.format({
            col: "{:,.0f}" for col in disp.columns
            if any(x in col for x in ('SAR', 'Orders', 'Completed', 'Rejected',
                                       'Prev Orders'))
        } | {"Fill Rate %": "{:.1f}%", "Prev Fill Rate %": "{:.1f}%",
             **({k: "{:+.1f}" for k in ['Rev Growth %', 'Ord Growth %']}
                if compare_on else {})}),
        use_container_width=True, hide_index=True,
    )

    # Top 10 / Bottom 10
    n_branches = len(br)
    if n_branches >= 2:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        col_top, col_bot = st.columns(2)

        for side, label, rows, bg in [
            (col_top, "🏆 Top 10 Branches",    br.head(min(10, n_branches)),
             'rgba(34,197,94,0.07)'),
            (col_bot, "⚠️ Bottom 10 Branches", br.tail(min(10, n_branches))
             .sort_values('Revenue', ascending=True).reset_index(drop=True),
             'rgba(239,68,68,0.07)'),
        ]:
            with side:
                section(label)
                if compare_on and not o_cmp.empty:
                    t_disp = rows[['Location', 'Revenue', 'Rev_Prev',
                                   'Rev Growth', 'Fill Rate %']].copy()
                    t_disp.columns = ['Branch', 'Revenue (SAR)', 'Prev Revenue (SAR)',
                                      'Growth %', 'Fill Rate %']
                    t_styled = t_disp.style.applymap(color_growth, subset=['Growth %'])
                    t_styled = t_styled.applymap(
                        lambda _: f'background-color: {bg}', subset=['Branch'])
                else:
                    t_disp = rows[['Location', 'Revenue', 'Orders', 'Fill Rate %']].copy()
                    t_disp.columns = ['Branch', 'Revenue (SAR)', 'Orders', 'Fill Rate %']
                    t_styled = t_disp.style.applymap(
                        lambda _: f'background-color: {bg}', subset=['Branch'])

                st.dataframe(
                    t_styled.format({
                        col: "{:,.0f}" for col in t_disp.columns
                        if 'SAR' in col or col == 'Orders'
                    } | {"Fill Rate %": "{:.1f}%",
                         **({} if not compare_on else {"Growth %": "{:+.1f}"})}),
                    use_container_width=True, hide_index=True,
                )

    # ── Export
    export_cols = ['Order ID', 'Date', 'Brand', 'Provider', 'Technology',
                   'Location', 'Status', 'Sales', 'Discount']
    export_button("Branches", {
        "Branch Performance": disp.reset_index(drop=True),
        "Filtered Orders":    o_cur[[c for c in export_cols if c in o_cur.columns]],
    })
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
