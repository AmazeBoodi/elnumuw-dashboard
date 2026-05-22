import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# We let Streamlit manage the background theme naturally based on device preferences
st.set_page_config(page_title="Alnumuw Dashboard", page_icon="📊", layout="wide")

# ══════════════════════════════════════════════════════════════════════════════
# COLOR SCHEMES & CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
BLUE   = "#3B82F6"; GREEN  = "#22C55E"; RED    = "#EF4444"
AMBER  = "#F59E0B"; PURPLE = "#8B5CF6"; GRAY   = "#6B7280"; TEAL = "#14B8A6"
PAL    = [BLUE, "#06B6D4", "#6366F1", "#A78BFA", "#EC4899", GREEN, AMBER, "#F97316", TEAL, "#84CC16"]

REJECTED_STATUSES = {"Canceled", "Cancelled", "Rejected"}

# ══════════════════════════════════════════════════════════════════════════════
# DATA ENGINE
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
        
    categorical_cols = ['Brand', 'Provider', 'Technology', 'Status', 'Location']
    for col in categorical_cols:
        for df in [o, i]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()
                
    o['Sales']    = pd.to_numeric(o['Sales'],    errors='coerce').fillna(0)
    o['Discount'] = pd.to_numeric(o['Discount'], errors='coerce').fillna(0)
    i['Quantity'] = pd.to_numeric(i['Quantity'], errors='coerce').fillna(0)
    return o, i

# ══════════════════════════════════════════════════════════════════════════════
# DATA UPLOADER GATEWAY
# ══════════════════════════════════════════════════════════════════════════════
st.title("📊 Alnumuw Platform for Commercial Services — Operational Dashboard")

uploaded = st.file_uploader("Upload Excel Template to populate dashboard views", type=["xlsx"])

if not uploaded:
    st.info("⬆️ Please upload your Excel template above to begin.")
    st.stop()

try:
    df_all_o, df_all_i = process(uploaded.read())
except Exception as e:
    st.error(f"❌ Error reading worksheets: {e}")
    st.stop()

G_MIN = df_all_o['Date'].min().date()
G_MAX = df_all_o['Date'].max().date()

# ── on_click callbacks for reset buttons. Mutating widget state via a callback
# is the Streamlit-blessed pattern; it runs before the next rerun's widgets
# are instantiated, which is the only reliable way to truly reset a widget
# that has already been rendered in this session.
_FILTER_KEYS = ["v_Brand", "v_Provider", "v_Location", "v_Technology", "v_Status", "v_Items"]

def _cb_clear_filters():
    # Explicitly set each multiselect's value to an empty list. This is more
    # reliable than pop() because Streamlit reads the value from session_state
    # at widget instantiation; SETTING the key guarantees the new state.
    for _k in _FILTER_KEYS:
        st.session_state[_k] = []

def _cb_reset_date():
    # Explicitly set the date_input back to the full data window. pop() does
    # not always make st.date_input fall back to its default arg on the next
    # rerun, so we set the value directly to (G_MIN, G_MAX).
    st.session_state["date_range_key"] = (G_MIN, G_MAX)

if 'Items' in df_all_i.columns:
    df_all_i['Items'] = df_all_i['Items'].astype(str).str.strip()

# Relational mapping matrix for dynamic cascading controls.
# Orders with no matching line in Items Report get a sentinel label so they
# are visible in the Items filter rather than silently dropped when the user
# picks specific items. Date is included so the filter options can also
# narrow when the user changes the date range.
UNMATCHED_ITEM_LABEL = "(Orders without line items)"
items_extracted = df_all_i[['Order ID', 'Items']].dropna().drop_duplicates()
master_map = df_all_o[['Order ID', 'Date', 'Brand', 'Provider', 'Technology', 'Location', 'Status']].merge(
    items_extracted, on='Order ID', how='left'
)
master_map['Items'] = master_map['Items'].fillna(UNMATCHED_ITEM_LABEL)
_unmatched_order_count = master_map[master_map['Items'] == UNMATCHED_ITEM_LABEL]['Order ID'].nunique()

# Cached "full universe" of options per dimension — used as a safe fallback
# when the user has not selected anything, so unselected filters don't
# accidentally constrain the data when combined with other filters.
ALL_OPTS = {col: sorted(master_map[col].dropna().unique().tolist())
            for col in ['Brand', 'Provider', 'Location', 'Technology', 'Status', 'Items']}

# Bidirectional cascading filter: every filter's option list is narrowed by
# every OTHER filter's selection PLUS the current date range. To avoid the
# circular case where a new pick would silently drop an already-selected
# value, we union the narrowed set with whatever the user has currently
# selected — so user picks never disappear from the option list.
#
# All access is via st.session_state, which is the native Streamlit pattern,
# and the date range is read from the same widget key that the date_input
# above uses ("date_range_key"). No extra libraries.
_FILTER_ORDER = ['Brand', 'Provider', 'Location', 'Technology', 'Status', 'Items']

def _current_date_window():
    """Read the current date-input range from session_state, falling back to
    the full data span. Returns (start_timestamp, end_timestamp)."""
    dr = st.session_state.get("date_range_key", None)
    if dr and len(dr) == 2:
        return pd.Timestamp(dr[0]), pd.Timestamp(dr[1])
    return pd.Timestamp(G_MIN), pd.Timestamp(G_MAX)

def get_allowed_options(target_col):
    if target_col not in _FILTER_ORDER:
        return sorted(master_map[target_col].dropna().unique().tolist())
    df = master_map
    # Narrow by the current date window
    ds, de = _current_date_window()
    df = df[(df['Date'] >= ds) & (df['Date'] <= de)]
    # Narrow by every other filter's selection
    for f in _FILTER_ORDER:
        if f != target_col:
            selected = st.session_state.get(f"v_{f}", [])
            if selected:
                df = df[df[f].isin(selected)]
    allowed = set(df[target_col].dropna().unique().tolist())
    # Preserve the user's existing picks for the target filter so they are
    # never silently dropped when another filter changes.
    user_picks = set(st.session_state.get(f"v_{target_col}", []) or [])
    return sorted(allowed | user_picks)

# ══════════════════════════════════════════════════════════════════════════════
# TIMELINE RANGE CONTROLS (TOP ROW)
# ══════════════════════════════════════════════════════════════════════════════
_c1, _c2, _c3 = st.columns([2, 1.5, 1])
with _c1:
    date_range = st.date_input(
        "📅 Date Range Window",
        [G_MIN, G_MAX],
        min_value=G_MIN, max_value=G_MAX,
        key="date_range_key",
    )
sd = date_range[0] if len(date_range) == 2 else G_MIN
ed = date_range[1] if len(date_range) == 2 else G_MAX

with _c2:
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    compare_on = st.toggle("🔁 Activate Period Comparison", value=False)

with _c3:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.button(
        "📅 Reset Date",
        use_container_width=True,
        help="Reset the date range to the full data window",
        on_click=_cb_reset_date,
    )

if compare_on:
    n_days = (pd.Timestamp(ed) - pd.Timestamp(sd)).days + 1
    cmp_e  = pd.Timestamp(sd) - pd.Timedelta(days=1)
    cmp_s  = max(cmp_e - pd.Timedelta(days=n_days - 1), pd.Timestamp(G_MIN))
    
    _cc1, _cc2 = st.columns([2, 2])
    with _cc1:
        cr = st.date_input("Compare to historical period", [cmp_s.date(), cmp_e.date()], min_value=G_MIN, max_value=G_MAX)
        if len(cr) == 2:
            cmp_s, cmp_e = pd.Timestamp(cr[0]), pd.Timestamp(cr[1])

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# STREAMLIT SIDEBAR CONTROLS FOR MULTI-ITEM LOGIC
# ══════════════════════════════════════════════════════════════════════════════
def _count_active(key):
    """How many items are currently selected in a given filter key."""
    return len(st.session_state.get(key, []) or [])

def _expander_label(emoji, name, key):
    n = _count_active(key)
    return f"{emoji} {name}" + (f"  ·  {n} selected" if n else "")

with st.sidebar:
    st.subheader("🔍 Filters Panel")

    # Clear-all button — uses on_click callback so widget state is mutated
    # before the next rerun renders the multiselects.
    st.button(
        "🧹 Clear Filters",
        use_container_width=True,
        help="Clear every filter selection (date range is untouched)",
        on_click=_cb_clear_filters,
    )

    # Each filter is wrapped in an expander so the sidebar stays compact when
    # many items are selected. Header shows the active selection count.
    with st.expander(_expander_label("🏷️", "Filter by Brand", "v_Brand"),
                     expanded=_count_active("v_Brand") > 0):
        sel_brand = st.multiselect("Brand", options=get_allowed_options("Brand"),
                                   key="v_Brand", label_visibility="collapsed")

    with st.expander(_expander_label("🚚", "Filter by Provider", "v_Provider"),
                     expanded=_count_active("v_Provider") > 0):
        sel_prov = st.multiselect("Provider", options=get_allowed_options("Provider"),
                                  key="v_Provider", label_visibility="collapsed")

    with st.expander(_expander_label("📍", "Filter by Branch", "v_Location"),
                     expanded=_count_active("v_Location") > 0):
        sel_loc = st.multiselect("Branch", options=get_allowed_options("Location"),
                                 key="v_Location", label_visibility="collapsed")

    with st.expander(_expander_label("⚙️", "Filter by Tech", "v_Technology"),
                     expanded=_count_active("v_Technology") > 0):
        sel_tech = st.multiselect("Technology", options=get_allowed_options("Technology"),
                                  key="v_Technology", label_visibility="collapsed")

    with st.expander(_expander_label("✅", "Filter by Status", "v_Status"),
                     expanded=_count_active("v_Status") > 0):
        sel_status = st.multiselect("Status", options=get_allowed_options("Status"),
                                    key="v_Status", label_visibility="collapsed")

    with st.expander(_expander_label("🛒", "Filter by Product Item", "v_Items"),
                     expanded=_count_active("v_Items") > 0):
        sel_items = st.multiselect("Items", options=get_allowed_options("Items"),
                                   key="v_Items", label_visibility="collapsed")
        if _unmatched_order_count > 0:
            st.caption(
                f"ℹ️ {_unmatched_order_count} orders exist in the system with no product details recorded "
                f"in the Items sheet. They appear as \"{UNMATCHED_ITEM_LABEL}\" in this filter. "
                "If you select only specific products, these orders will be excluded from all results."
            )

# When a filter has no user selection, fall back to the full universe of
# values from ALL_OPTS (not the cascaded set). This keeps "no filter" meaning
# "no constraint on this dimension" even in comparison mode where the
# historical period may include values outside the current narrowed set.
active_brands  = sel_brand  or ALL_OPTS['Brand']
active_provs   = sel_prov   or ALL_OPTS['Provider']
active_locs    = sel_loc    or ALL_OPTS['Location']
active_techs   = sel_tech   or ALL_OPTS['Technology']
active_status  = sel_status or ALL_OPTS['Status']
active_items   = sel_items  or ALL_OPTS['Items']

# ══════════════════════════════════════════════════════════════════════════════
# COMPILING MATRICES
# ══════════════════════════════════════════════════════════════════════════════
# Track whether the user has actively filtered Status so KPIs that depend on
# rejections (Fill Rate) can fall back to a Status-unfiltered slice. Otherwise
# selecting only "Completed" would force Fill Rate to 100% by construction.
status_user_filtered = bool(sel_status)

def compile_split_data(start_d, end_d, ignore_status=False):
    status_list = active_status if not ignore_status else ALL_OPTS['Status']
    o_df = df_all_o[
        (df_all_o['Date'] >= pd.Timestamp(start_d)) & (df_all_o['Date'] <= pd.Timestamp(end_d)) &
        (df_all_o['Brand'].isin(active_brands)) & (df_all_o['Provider'].isin(active_provs)) &
        (df_all_o['Location'].isin(active_locs)) & (df_all_o['Status'].isin(status_list)) &
        (df_all_o['Technology'].isin(active_techs))
    ]
    ids = master_map[master_map['Items'].isin(active_items)]['Order ID'].unique()
    o_df = o_df[o_df['Order ID'].isin(ids)]
    i_df = df_all_i[df_all_i['Order ID'].isin(o_df['Order ID']) & df_all_i['Items'].isin(active_items)]
    return o_df, i_df

o_cur, i_cur = compile_split_data(sd, ed)

# Status-unfiltered current slice for Fill Rate, so the KPI stays meaningful
# even when the user has filtered Status in the sidebar.
o_cur_fr, _ = compile_split_data(sd, ed, ignore_status=True)

rev_cur = o_cur['Sales'].sum()
ord_cur = len(o_cur)
qty_cur = i_cur['Quantity'].sum()
fr_total = len(o_cur_fr)
fr_rej   = len(o_cur_fr[o_cur_fr['Status'].isin(REJECTED_STATUSES)])
fill_cur = ((fr_total - fr_rej) / fr_total * 100) if fr_total > 0 else 100.0

# ══════════════════════════════════════════════════════════════════════════════
# PREVIOUS PERIOD COMPUTATION (always defined so tabs can reference safely)
# ══════════════════════════════════════════════════════════════════════════════
if compare_on:
    o_old, i_old = compile_split_data(cmp_s, cmp_e)
    o_old_fr, _  = compile_split_data(cmp_s, cmp_e, ignore_status=True)
else:
    o_old    = df_all_o.iloc[0:0].copy()
    i_old    = df_all_i.iloc[0:0].copy()
    o_old_fr = df_all_o.iloc[0:0].copy()

rev_old  = o_old['Sales'].sum() if not o_old.empty else 0.0
ord_old  = len(o_old)
qty_old  = i_old['Quantity'].sum() if not i_old.empty else 0.0
comp_old = len(o_old_fr[~o_old_fr['Status'].isin(REJECTED_STATUSES)]) if not o_old_fr.empty else 0
rej_old  = len(o_old_fr[o_old_fr['Status'].isin(REJECTED_STATUSES)]) if not o_old_fr.empty else 0
fr_total_old = len(o_old_fr)
fr_rej_old   = len(o_old_fr[o_old_fr['Status'].isin(REJECTED_STATUSES)]) if not o_old_fr.empty else 0
fill_old = ((fr_total_old - fr_rej_old) / fr_total_old * 100) if fr_total_old > 0 else 100.0
disc_old = o_old['Discount'].sum() if not o_old.empty else 0.0
net_old  = rev_old - disc_old

# Completed/Rejected for current period (always Status-unfiltered).
comp_cur = len(o_cur_fr[~o_cur_fr['Status'].isin(REJECTED_STATUSES)])
rej_cur  = len(o_cur_fr[o_cur_fr['Status'].isin(REJECTED_STATUSES)])
disc_cur = o_cur['Discount'].sum()
net_cur  = rev_cur - disc_cur

def _pct(cur, old):
    return ((cur - old) / old * 100) if old > 0 else 0.0

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY KPI TILES (5)
# ══════════════════════════════════════════════════════════════════════════════
k_cols = st.columns(5)
fill_label = "🎯 Fill Rate %" + (" *" if status_user_filtered else "")

if compare_on:
    k_cols[0].metric("💰 Gross Revenue", f"{rev_cur:,.0f} SAR", f"{_pct(rev_cur, rev_old):+.1f}% vs Prev")
    k_cols[1].metric("📦 Total Orders", f"{ord_cur:,}", f"{_pct(ord_cur, ord_old):+.1f}% vs Prev")
    k_cols[2].metric("✅ Completed Orders", f"{comp_cur:,}", f"{_pct(comp_cur, comp_old):+.1f}% vs Prev")
    k_cols[3].metric("❌ Rejected Orders", f"{rej_cur:,}", f"{_pct(rej_cur, rej_old):+.1f}% vs Prev", delta_color="inverse")
    k_cols[4].metric(fill_label, f"{fill_cur:.1f}%", f"{(fill_cur - fill_old):+.1f} pp vs Prev")
    st.caption(f"Net Revenue = Gross Sales minus Discounts given. Current period: **{net_cur:,.0f} SAR** · Previous period: **{net_old:,.0f} SAR** · Discounts given this period: {disc_cur:,.0f} SAR")
else:
    k_cols[0].metric("💰 Gross Revenue", f"{rev_cur:,.0f} SAR")
    k_cols[1].metric("📦 Total Orders", f"{ord_cur:,}")
    k_cols[2].metric("✅ Completed Orders", f"{comp_cur:,}")
    k_cols[3].metric("❌ Rejected Orders", f"{rej_cur:,}")
    k_cols[4].metric(fill_label, f"{fill_cur:.1f}%")
    st.caption(f"Net Revenue = Gross Sales minus Discounts given. This period: **{net_cur:,.0f} SAR** · Discounts given: {disc_cur:,.0f} SAR")

if status_user_filtered:
    st.caption("* Fill Rate is always calculated using all order statuses — even if you have filtered by status in the sidebar. This is intentional: if we only counted 'Completed' orders, Fill Rate would always show 100%, which would be meaningless.")

# ══════════════════════════════════════════════════════════════════════════════
# COMPARISON TABLE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
# DIMENSION COMPARISON BUILDER
# Builds Sales, Orders, AOV — with growth columns when comparison is on.
def build_dim_comparison(cur_df, old_df, dim_col, with_compare):
    cur = cur_df.groupby(dim_col).agg(
        Sales  =('Sales',    'sum'),
        Orders =('Order ID', 'count'),
    ).reset_index()
    cur.columns = [dim_col, 'Sales', 'Orders']
    # Use .where() instead of replace(0, pd.NA) to avoid object-dtype issues
    cur['AOV'] = (cur['Sales'].astype(float) /
                  cur['Orders'].astype(float).where(cur['Orders'] > 0)).round(0)
    if not with_compare or old_df.empty:
        return cur.sort_values('Sales', ascending=False).reset_index(drop=True)
    old = old_df.groupby(dim_col).agg(
        Sales  =('Sales',    'sum'),
        Orders =('Order ID', 'count'),
    ).reset_index()
    old.columns = [dim_col, '_PrevSales', '_PrevOrders']
    df = cur.merge(old, on=dim_col, how='outer')
    # Force all numeric columns to float after outer merge —
    # object dtype can sneak in when NaN rows get introduced by the merge.
    for col in ['Sales', 'Orders', '_PrevSales', '_PrevOrders']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['AOV'] = (df['Sales'] / df['Orders'].where(df['Orders'] > 0)).round(0)
    prev_aov  = (df['_PrevSales'] / df['_PrevOrders'].where(df['_PrevOrders'] > 0))
    df['Sales vs Prev %']  = ((df['Sales']  - df['_PrevSales'])  /
                               df['_PrevSales'].where(df['_PrevSales']   > 0)) * 100
    df['Orders vs Prev %'] = ((df['Orders'] - df['_PrevOrders']) /
                               df['_PrevOrders'].where(df['_PrevOrders'] > 0)) * 100
    df['AOV vs Prev %']    = ((df['AOV']    - prev_aov) /
                               prev_aov.where(prev_aov > 0)) * 100
    df = df.drop(columns=['_PrevSales', '_PrevOrders'])
    return df.sort_values('Sales', ascending=False).reset_index(drop=True)

# Urban Piper-style comparison table renderer.
# Renders the current value in the theme's default color and inlines the
# comparison arrow+% in a colored <span> next to it — all in one cell.
# Uses st.markdown(unsafe_allow_html=True) because st.dataframe cannot apply
# different CSS to parts of the same cell.
def render_comparison_table(df, growth_map, value_format=None, col_labels=None,
                             inverse_cols=None, max_height="700px"):
    """
    Render a scrollable Urban Piper-style table with inlined comparison arrows.

    growth_map   : {value_col: growth_col}  — growth_col is inlined and hidden
    value_format : {col: format_str}  e.g. {'Sales': '{:,.0f}', 'Fill Rate %': '{:.1f}%'}
    col_labels   : {col: display_name}  — override column header text
    inverse_cols : value_col names where higher = worse (Cancelled, Rejected, etc.)
                   positive → red, negative → green
    max_height   : CSS max-height for the scroll container (default "700px" ≈ 20 rows)
    """
    vfmt    = value_format or {}
    labels  = col_labels   or {}
    inv_set = set(inverse_cols or [])
    display_cols = [c for c in df.columns if c not in growth_map.values()]

    def _fmt(col, val):
        if not isinstance(val, str) and pd.isna(val):
            return "—"
        fmt = vfmt.get(col)
        if fmt:
            try:
                return fmt.format(val)
            except Exception:
                pass
        # Auto-format datetime/Timestamp columns as "Jan 18"
        if hasattr(val, 'strftime'):
            return val.strftime('%b %d')
        return str(val)

    def _growth_span(g, inverse=False, is_pp=False):
        if isinstance(g, str) or pd.isna(g):
            return ""
        arrow = '↑' if g >= 0 else '↓'
        if inverse:
            color = '#EF4444' if g > 0 else ('#22C55E' if g < 0 else 'gray')
        else:
            color = '#22C55E' if g > 0 else ('#EF4444' if g < 0 else 'gray')
        suffix = ' pp' if is_pp else '%'
        return (f'<span style="color:{color};font-weight:600;'
                f'font-size:0.82em;margin-left:7px">{arrow} {g:+.1f}{suffix}</span>')

    # Sticky header — background inherits from Streamlit's secondary surface colour
    _th_style = (
        'text-align:left;padding:8px 14px;white-space:nowrap;'
        'border-bottom:2px solid rgba(128,128,128,0.25);font-weight:600;'
        'font-size:0.8rem;opacity:0.85;position:sticky;top:0;z-index:2;'
        'background:var(--secondary-background-color,#f0f2f6)'
    )
    header = ''.join(
        f'<th style="{_th_style}">{labels.get(c, c)}</th>'
        for c in display_cols
    )

    rows_html = []
    for _, row in df.iterrows():
        cells = []
        for col in display_cols:
            val   = row.get(col, None)
            v_str = _fmt(col, val)
            gc    = growth_map.get(col)
            if gc and gc in row.index:
                is_inv = col in inv_set
                is_pp  = isinstance(gc, str) and gc.endswith('pp')
                span   = _growth_span(row[gc], inverse=is_inv, is_pp=is_pp)
            else:
                span = ""
            cells.append(
                f'<td style="padding:8px 14px;white-space:nowrap;'
                f'border-bottom:1px solid rgba(128,128,128,0.1)">'
                f'{v_str}{span}</td>'
            )
        rows_html.append(f'<tr style="line-height:1.6">{"".join(cells)}</tr>')

    _h = f';max-height:{max_height};overflow-y:auto' if max_height else ''
    html = (
        f'<div style="overflow-x:auto{_h};border:1px solid rgba(128,128,128,0.15);border-radius:6px">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.875rem;font-family:inherit">'
        f'<thead><tr>{header}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table></div>'
    )
    st.markdown(html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# EXCEL EXPORT HELPER
def _to_excel_bytes(df):
    """Serialize a DataFrame to an in-memory .xlsx file and return raw bytes."""
    import io
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine='openpyxl')
    return buf.getvalue()

# ══════════════════════════════════════════════════════════════════════════════
# REUSABLE DIMENSION TAB RENDERER
# Used by Aggregators, Brands, Technologies — same structure, different dim col.
def render_dim_tab(df_raw, dim_label, compare_on, tab_key, extra_charts_fn=None):
    """
    Render a full dimension breakdown with:
      • Sort controls (selectbox + direction)
      • Urban Piper comparison table (comparison on) or native st.dataframe (off)
      • Export to Excel button
      • Optional extra_charts_fn(df_sorted) callback for tab-specific charts
    df_raw   : output of build_dim_comparison — may have growth columns
    dim_label: human label for the dimension column (e.g. 'Aggregator')
    tab_key  : short unique string used for widget keys (e.g. 'agg')
    """
    if df_raw.empty:
        st.info("No data found for the current filters.")
        return

    # ── Sort controls + Export on one row ──────────────────────────────────
    sort_candidates = ['Sales', 'Orders', 'AOV']
    sort_opts = [c for c in sort_candidates if c in df_raw.columns]
    _dim_sort_labels = {'Sales': 'Sales (SAR)', 'Orders': 'Orders', 'AOV': 'AOV (SAR)'}
    sc1, sc2, sc3 = st.columns([2, 1.5, 1])
    with sc1:
        sort_by = st.selectbox("Sort by", sort_opts,
                               format_func=lambda x: _dim_sort_labels.get(x, x),
                               key=f"sort_{tab_key}")
    with sc2:
        sort_dir = st.radio("Direction", ['↓ High → Low', '↑ Low → High'],
                            horizontal=True, key=f"dir_{tab_key}",
                            label_visibility="collapsed")
    with sc3:
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        st.download_button(
            "📥 Export Excel",
            data=_to_excel_bytes(df_raw),
            file_name=f"{tab_key}_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"exp_{tab_key}",
        )

    ascending = sort_dir.startswith('↑')
    df = df_raw.sort_values(sort_by, ascending=ascending).reset_index(drop=True)

    # ── Optional extra charts ───────────────────────────────────────────────
    if extra_charts_fn:
        extra_charts_fn(df)

    # ── Table ───────────────────────────────────────────────────────────────
    if compare_on and 'Sales vs Prev %' in df.columns:
        render_comparison_table(
            df,
            growth_map={'Sales':  'Sales vs Prev %',
                        'Orders': 'Orders vs Prev %',
                        'AOV':    'AOV vs Prev %'},
            value_format={'Sales': '{:,.0f}', 'Orders': '{:,}', 'AOV': '{:,.0f}'},
            col_labels={
                dim_label: dim_label,
                'Sales':   'Sales (SAR)',
                'Orders':  'Orders',
                'AOV':     'AOV (SAR)',
                'Sales vs Prev %':  'vs Prev',
                'Orders vs Prev %': 'vs Prev',
                'AOV vs Prev %':    'vs Prev',
            },
        )
    else:
        vfmt = {c: v for c, v in
                {'Sales': '{:,.0f}', 'Orders': '{:,}', 'AOV': '{:,.0f}'}.items()
                if c in df.columns}
        st.dataframe(
            df.style.format(vfmt, na_rep='—'),
            use_container_width=True,
            hide_index=True,
            height=min(700, 60 + 35 * len(df)),
            column_config={
                dim_label: st.column_config.TextColumn(dim_label),
                'Sales':   st.column_config.TextColumn('Sales (SAR)'),
                'Orders':  st.column_config.TextColumn('Orders'),
                'AOV':     st.column_config.TextColumn('AOV (SAR)'),
            },
        )

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
tab_summary, tab_orders, tab_lost, tab_items, tab_branches, tab_aggs, tab_brands, tab_tech = st.tabs(
    ["📊 Summary", "📦 Orders", "🚫 Lost Orders", "🛒 Items", "📍 Branches", "🚚 Aggregators", "🏷️ Brands", "⚙️ Technologies"]
)

# ── Summary timeline with current vs previous overlay
with tab_summary:
    st.markdown("### 📈 Revenue & Order Volume Timeline")
    if not o_cur.empty:
        cur_trend = o_cur.groupby('Date').agg(Sales=('Sales','sum'), Orders=('Order ID','count')).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=cur_trend['Date'], y=cur_trend['Sales'],
            name="Current Revenue", mode='lines+markers',
            line=dict(color=BLUE, width=3),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Current Revenue: %{y:,.2f} SAR<extra></extra>"
        ))

        if compare_on and not o_old.empty:
            old_trend = o_old.groupby('Date').agg(Sales=('Sales','sum'), Orders=('Order ID','count')).reset_index()
            # Align previous period dates onto the current period's calendar so
            # both lines sit on the same x-axis for visual comparison.
            cmp_offset = pd.Timestamp(sd) - pd.Timestamp(cmp_s)
            old_trend['Aligned Date'] = old_trend['Date'] + cmp_offset
            fig.add_trace(go.Scatter(
                x=old_trend['Aligned Date'], y=old_trend['Sales'],
                name="Previous Revenue", mode='lines+markers',
                line=dict(color=AMBER, width=2, dash='dash'),
                hovertemplate="<b>%{x|%Y-%m-%d} (aligned)</b><br>Previous Revenue: %{y:,.2f} SAR<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                x=cur_trend['Date'], y=cur_trend['Orders'],
                name="Current Orders", yaxis="y2", opacity=0.35, marker_color=BLUE,
                hovertemplate="Current Orders: %{y}<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                x=old_trend['Aligned Date'], y=old_trend['Orders'],
                name="Previous Orders", yaxis="y2", opacity=0.35, marker_color=AMBER,
                hovertemplate="Previous Orders: %{y}<extra></extra>"
            ))
        else:
            fig.add_trace(go.Bar(
                x=cur_trend['Date'], y=cur_trend['Orders'],
                name="Orders Count", yaxis="y2", opacity=0.3, marker_color=AMBER
            ))

        fig.update_layout(dragmode='pan', 
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title=dict(text="Revenue (SAR)", font=dict(color=BLUE)), tickfont=dict(color=BLUE)),
            yaxis2=dict(title=dict(text="Orders Count", font=dict(color=AMBER)), tickfont=dict(color=AMBER), overlaying="y", side="right"),
            margin=dict(l=20, r=20, t=30, b=20), height=400, showlegend=True,
            hovermode="x unified",
            barmode='group' if compare_on else 'overlay'
        )
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        if compare_on:
            st.caption("The dotted amber line shows the previous period. Its dates have been shifted to align with the current period so both lines sit on the same chart and you can compare them side by side. Hover over any point to see the exact values and which period it belongs to.")

        # Export filtered orders for this period
        st.markdown("---")
        exp_sum = o_cur[['Date','Brand','Provider','Location','Technology','Status','Sales','Discount']].copy()
        st.download_button(
            "📥 Export Current Period Orders (Excel)",
            data=_to_excel_bytes(exp_sum),
            file_name="summary_orders.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exp_summary",
        )
    else:
        st.info("No timeline data found for current filters.")

# ── Orders tab
with tab_orders:
    st.markdown("### 📦 Order Operations")
    if not o_cur.empty:
        # ── Shared daily base (Status-unfiltered for accurate Fill Rate) ────
        daily_all = o_cur_fr.groupby('Date').agg(
            Total     = ('Order ID', 'count'),
            Cancelled = ('Status',   lambda s: s.isin(REJECTED_STATUSES).sum()),
        ).reset_index()
        daily_all['Completed']   = daily_all['Total'] - daily_all['Cancelled']
        daily_all['Fill Rate %'] = (daily_all['Completed'] / daily_all['Total'].replace(0, pd.NA) * 100)

        daily_rev = o_cur.groupby('Date').agg(
            CompletedRev  = ('Sales', 'sum'),
            TotalOrders   = ('Order ID', 'count'),
        ).reset_index()

        # Cancelled revenue from the Status-unfiltered slice
        daily_canc_rev = (o_cur_fr[o_cur_fr['Status'].isin(REJECTED_STATUSES)]
                          .groupby('Date')['Sales'].sum()
                          .reset_index().rename(columns={'Sales': 'CancelledRev'}))
        daily_rev = daily_rev.merge(daily_canc_rev, on='Date', how='left').fillna({'CancelledRev': 0})
        daily_rev['AOV'] = daily_rev['CompletedRev'] / daily_rev['TotalOrders'].replace(0, pd.NA)

        # ── CHART 1a: Daily order volume (stacked bar) ──────────────────────
        st.markdown("#### 📊 Daily Orders: Completed vs Cancelled")
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Bar(
            x=daily_all['Date'], y=daily_all['Completed'],
            name="Completed", marker_color=GREEN, opacity=0.85,
            hovertemplate="<b>%{x|%b %d}</b><br>Completed: %{y:,}<extra></extra>",
        ))
        fig_vol.add_trace(go.Bar(
            x=daily_all['Date'], y=daily_all['Cancelled'],
            name="Cancelled", marker_color=RED, opacity=0.9,
            hovertemplate="Cancelled: %{y:,}<extra></extra>",
        ))
        fig_vol.update_layout(dragmode='pan', 
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            barmode='stack', hovermode='x unified', height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="Orders"),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig_vol, use_container_width=True, config={'scrollZoom': True})

        # ── CHART 1b: Daily Fill Rate % trend ───────────────────────────────
        st.markdown("#### 🎯 Daily Fill Rate %")
        avg_fr = daily_all['Fill Rate %'].mean()
        fig_fr = go.Figure()
        fig_fr.add_hline(y=avg_fr, line_dash='dot', line_color=GRAY,
                         annotation_text=f"Avg {avg_fr:.1f}%",
                         annotation_position="bottom right")
        fig_fr.add_trace(go.Scatter(
            x=daily_all['Date'], y=daily_all['Fill Rate %'],
            mode='lines', name="Fill Rate %",
            line=dict(color=AMBER, width=2),
            fill='tozeroy', fillcolor='rgba(245,158,11,0.12)',
            hovertemplate="<b>%{x|%b %d}</b><br>Fill Rate: %{y:.1f}%<extra></extra>",
        ))
        fig_fr.update_layout(dragmode='pan', 
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=220, margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(title="Fill Rate %", ticksuffix='%', range=[0, 105]),
            showlegend=False,
        )
        st.plotly_chart(fig_fr, use_container_width=True, config={'scrollZoom': True})

        # ── CHART 2: Revenue — Completed vs Lost (dual-axis: bars + line) ───
        st.markdown("#### 💸 Daily Revenue: Completed vs Cancelled")
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=daily_rev['Date'], y=daily_rev['CompletedRev'],
            name="Completed Revenue", marker_color=BLUE, opacity=0.8,
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Completed Rev: %{y:,.0f} SAR<extra></extra>",
        ))
        fig_rev.add_trace(go.Bar(
            x=daily_rev['Date'], y=daily_rev['CancelledRev'],
            name="Cancelled Revenue", marker_color=RED, opacity=0.85,
            hovertemplate="Cancelled Rev: %{y:,.0f} SAR<extra></extra>",
        ))
        if compare_on and not o_old.empty:
            old_rev = o_old.groupby('Date').agg(Sales=('Sales','sum')).reset_index()
            cmp_offset = pd.Timestamp(sd) - pd.Timestamp(cmp_s)
            old_rev['Aligned Date'] = old_rev['Date'] + cmp_offset
            fig_rev.add_trace(go.Scatter(
                x=old_rev['Aligned Date'], y=old_rev['Sales'],
                name="Prev Completed Rev", mode='lines',
                line=dict(color=AMBER, width=2, dash='dot'),
                hovertemplate="<b>%{x|%Y-%m-%d} (aligned)</b><br>Prev Rev: %{y:,.0f} SAR<extra></extra>",
            ))
        fig_rev.update_layout(dragmode='pan', 
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            barmode='stack', hovermode='x unified', height=320,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis=dict(title="Revenue (SAR)"),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig_rev, use_container_width=True, config={'scrollZoom': True})

        # ── CHART 3: Day-of-Week patterns ───────────────────────────────────
        st.markdown("#### 📅 Day-of-Week Patterns")
        dow_df = o_cur.copy()
        dow_df['Day'] = dow_df['Date'].dt.day_name()
        dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        dow_agg = (dow_df.groupby('Day')
                   .agg(Avg_Orders=('Order ID','count'), Total_Rev=('Sales','sum'))
                   .reindex(dow_order).reset_index())
        n_weeks = max(1, (pd.Timestamp(ed) - pd.Timestamp(sd)).days / 7)
        dow_agg['Avg_Orders'] = (dow_agg['Avg_Orders'] / n_weeks).round(0)
        dow_agg['Avg_Rev']    = (dow_agg['Total_Rev']  / n_weeks).round(0)

        _dc1, _dc2 = st.columns(2)
        with _dc1:
            fig_dow_o = px.bar(
                dow_agg, x='Day', y='Avg_Orders', text='Avg_Orders',
                color_discrete_sequence=[BLUE], template="plotly_dark",
                labels={'Avg_Orders': 'Avg Orders / Week', 'Day': ''},
            )
            fig_dow_o.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_dow_o.update_layout(dragmode='pan', 
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=300, margin=dict(t=30, b=10), showlegend=False,
                title=dict(text="Avg Orders per Day of Week", font=dict(size=13)),
            )
            st.plotly_chart(fig_dow_o, use_container_width=True, config={'scrollZoom': True})
        with _dc2:
            fig_dow_r = px.bar(
                dow_agg, x='Day', y='Avg_Rev', text='Avg_Rev',
                color_discrete_sequence=[TEAL], template="plotly_dark",
                labels={'Avg_Rev': 'Avg Revenue (SAR)', 'Day': ''},
            )
            fig_dow_r.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_dow_r.update_layout(dragmode='pan', 
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=300, margin=dict(t=30, b=10), showlegend=False,
                title=dict(text="Avg Revenue per Day of Week", font=dict(size=13)),
            )
            st.plotly_chart(fig_dow_r, use_container_width=True, config={'scrollZoom': True})

        # ── CHART 4: AOV trend — current vs previous ─────────────────────────
        st.markdown("#### 💳 Daily Average Order Value (AOV)")
        fig_aov = go.Figure()
        fig_aov.add_trace(go.Scatter(
            x=daily_rev['Date'], y=daily_rev['AOV'],
            name="Current AOV", mode='lines+markers',
            line=dict(color=PURPLE, width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>AOV: %{y:,.0f} SAR<extra></extra>",
        ))
        if compare_on and not o_old.empty:
            old_aov = o_old.groupby('Date').agg(
                Sales=('Sales','sum'), Orders=('Order ID','count')
            ).reset_index()
            old_aov['AOV'] = old_aov['Sales'] / old_aov['Orders'].replace(0, pd.NA)
            cmp_offset = pd.Timestamp(sd) - pd.Timestamp(cmp_s)
            old_aov['Aligned Date'] = old_aov['Date'] + cmp_offset
            fig_aov.add_trace(go.Scatter(
                x=old_aov['Aligned Date'], y=old_aov['AOV'],
                name="Previous AOV", mode='lines+markers',
                line=dict(color=AMBER, width=2, dash='dash'),
                hovertemplate="<b>%{x|%Y-%m-%d} (aligned)</b><br>Prev AOV: %{y:,.0f} SAR<extra></extra>",
            ))
        fig_aov.update_layout(dragmode='pan', 
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="AOV (SAR)"), height=300,
            margin=dict(l=20, r=20, t=20, b=20), hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(fig_aov, use_container_width=True, config={'scrollZoom': True})

        # ── Raw table ────────────────────────────────────────────────────────
        # ── DAILY SUMMARY TABLE ──────────────────────────────────────────────
        st.markdown("#### 📋 Daily Summary")
        daily_sum = daily_all.merge(daily_rev[['Date','CompletedRev','AOV']], on='Date', how='left')
        daily_sum = daily_sum.rename(columns={
            'Total': 'Orders', 'CompletedRev': 'Revenue (SAR)'
        })[['Date','Orders','Completed','Cancelled','Fill Rate %','Revenue (SAR)','AOV']]

        if compare_on and not o_old.empty:
            old_daily = o_old_fr.groupby('Date').agg(
                _OldOrders=('Order ID','count'),
                _OldCancelled=('Status', lambda s: s.isin(REJECTED_STATUSES).sum()),
            ).reset_index()
            old_daily['_OldCompleted'] = old_daily['_OldOrders'] - old_daily['_OldCancelled']
            old_daily['_OldFillRate']  = (old_daily['_OldCompleted'] /
                                          old_daily['_OldOrders'].where(old_daily['_OldOrders'] > 0) * 100)
            old_rev_d = o_old.groupby('Date').agg(_OldRev=('Sales','sum'),
                                                   _OldRevOrds=('Order ID','count')).reset_index()
            old_rev_d['_OldAOV'] = old_rev_d['_OldRev'] / old_rev_d['_OldRevOrds'].where(old_rev_d['_OldRevOrds'] > 0)
            old_daily = old_daily.merge(old_rev_d[['Date','_OldRev','_OldAOV']], on='Date', how='left')
            cmp_offset = pd.Timestamp(sd) - pd.Timestamp(cmp_s)
            old_daily['Date'] = old_daily['Date'] + cmp_offset  # align dates
            daily_sum = daily_sum.merge(old_daily, on='Date', how='left')
            for c in [c for c in daily_sum.columns if c.startswith('_Old')]:
                daily_sum[c] = pd.to_numeric(daily_sum[c], errors='coerce').fillna(0)
            daily_sum['Orders vs Prev %']   = ((daily_sum['Orders']         - daily_sum['_OldOrders'])   / daily_sum['_OldOrders'].where(daily_sum['_OldOrders']   > 0)) * 100
            daily_sum['Revenue vs Prev %']  = ((daily_sum['Revenue (SAR)']  - daily_sum['_OldRev'])      / daily_sum['_OldRev'].where(daily_sum['_OldRev']         > 0)) * 100
            daily_sum['AOV vs Prev %']      = ((daily_sum['AOV']            - daily_sum['_OldAOV'])      / daily_sum['_OldAOV'].where(daily_sum['_OldAOV']         > 0)) * 100
            daily_sum['Fill Rate vs Prev pp']= daily_sum['Fill Rate %'] - daily_sum['_OldFillRate'].fillna(0)
            daily_sum = daily_sum.drop(columns=[c for c in daily_sum.columns if c.startswith('_Old')])

        # Show newest dates first
        daily_sum = daily_sum.sort_values('Date', ascending=False).reset_index(drop=True)

        _ds1, _ds2 = st.columns([5, 1])
        with _ds2:
            st.download_button("📥 Export Excel", data=_to_excel_bytes(daily_sum),
                               file_name="orders_daily.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="exp_orders_daily")

        if compare_on and 'Revenue vs Prev %' in daily_sum.columns:
            render_comparison_table(
                daily_sum,
                growth_map={
                    'Orders':       'Orders vs Prev %',
                    'Revenue (SAR)':'Revenue vs Prev %',
                    'AOV':          'AOV vs Prev %',
                    'Fill Rate %':  'Fill Rate vs Prev pp',
                },
                value_format={
                    'Orders':       '{:,}',
                    'Completed':    '{:,}',
                    'Cancelled':    '{:,}',
                    'Fill Rate %':  '{:.1f}%',
                    'Revenue (SAR)':'{:,.0f}',
                    'AOV':          '{:,.0f}',
                },
                col_labels={
                    'Revenue (SAR)':      'Revenue (SAR)',
                    'Orders vs Prev %':   'vs Prev',
                    'Revenue vs Prev %':  'vs Prev',
                    'AOV vs Prev %':      'vs Prev',
                    'Fill Rate vs Prev pp':'vs Prev',
                },
            )
            st.caption(
                "ℹ️ Each row compares that day to the matching day in the comparison period — "
                "the first day of your current window is compared to the first day of your comparison window, "
                "the second day to the second day, and so on. "
                "**pp** next to Fill Rate means 'percentage points' — "
                "it is the plain difference between two percentages. "
                "Example: Fill Rate drops from 95% to 91.5% = −3.5 pp "
                "(we subtract the two numbers; we do not calculate a ratio)."
            )
        else:
            st.dataframe(
                daily_sum.style.format({
                    'Orders':       '{:,}',
                    'Completed':    '{:,}',
                    'Cancelled':    '{:,}',
                    'Fill Rate %':  '{:.1f}%',
                    'Revenue (SAR)':'{:,.0f}',
                    'AOV':          '{:,.0f}',
                }, na_rep='—'),
                use_container_width=True, hide_index=True,
                height=min(700, 60 + 35 * len(daily_sum)),
                column_config={
                    "Date":         st.column_config.DateColumn("Date", format="MMM DD"),
                    "Orders":       st.column_config.TextColumn("Orders"),
                    "Completed":    st.column_config.TextColumn("Completed"),
                    "Cancelled":    st.column_config.TextColumn("Cancelled"),
                    "Fill Rate %":  st.column_config.TextColumn("Fill Rate %"),
                    "Revenue (SAR)":st.column_config.TextColumn("Revenue (SAR)"),
                    "AOV":          st.column_config.TextColumn("AOV (SAR)"),
                },
            )

        st.markdown("#### 📄 Raw Filtered Orders")
        st.dataframe(
            o_cur.style.format({'Sales': '{:,.0f}', 'Discount': '{:,.0f}'}, na_rep='—'),
            use_container_width=True, hide_index=True,
            column_config={
                "Sales":    st.column_config.NumberColumn("Sales (SAR)"),
                "Discount": st.column_config.NumberColumn("Discount (SAR)"),
                "Date":     st.column_config.DateColumn("Order Date", format="YYYY-MM-DD"),
            }
        )
    else:
        st.info("No order data found for current filters.")

# ── Lost Orders tab
with tab_lost:
    st.markdown("### 🚫 Cancelled / Lost Orders")
    # Filter to rejected statuses from the Status-unfiltered slice so this
    # works correctly even when the user has the Status filter set.
    lost_cur = o_cur_fr[o_cur_fr['Status'].isin(REJECTED_STATUSES)].copy()
    lost_old = o_old_fr[o_old_fr['Status'].isin(REJECTED_STATUSES)].copy() if compare_on else df_all_o.iloc[0:0].copy()

    if lost_cur.empty:
        st.success("✅ No cancelled orders in this period under current filters.")
    else:
        total_cancelled = len(lost_cur)
        lost_revenue    = lost_cur['Sales'].sum()
        total_orders_fr = len(o_cur_fr)
        cancel_rate     = (total_cancelled / total_orders_fr * 100) if total_orders_fr > 0 else 0.0

        # Previous-period equivalents
        total_cancelled_old = len(lost_old)
        lost_revenue_old    = lost_old['Sales'].sum() if not lost_old.empty else 0.0
        total_orders_fr_old = len(o_old_fr)
        cancel_rate_old     = (total_cancelled_old / total_orders_fr_old * 100) if total_orders_fr_old > 0 else 0.0

        # KPI tiles for the Lost Orders view (deltas use inverse coloring
        # because MORE cancellations / lost revenue is BAD, not good).
        k = st.columns(3)
        if compare_on:
            k[0].metric("🚫 Cancelled Orders", f"{total_cancelled:,}",
                        f"{_pct(total_cancelled, total_cancelled_old):+.1f}% vs Prev",
                        delta_color="inverse")
            k[1].metric("💸 Lost Revenue", f"{lost_revenue:,.0f} SAR",
                        f"{_pct(lost_revenue, lost_revenue_old):+.1f}% vs Prev",
                        delta_color="inverse")
            k[2].metric("📉 Cancellation Rate", f"{cancel_rate:.1f}%",
                        f"{(cancel_rate - cancel_rate_old):+.1f} pp vs Prev",
                        delta_color="inverse")
        else:
            k[0].metric("🚫 Cancelled Orders", f"{total_cancelled:,}")
            k[1].metric("💸 Lost Revenue", f"{lost_revenue:,.0f} SAR")
            k[2].metric("📉 Cancellation Rate", f"{cancel_rate:.1f}%")

        st.markdown("---")

        # Daily cancellation trend
        daily_lost = lost_cur.groupby('Date').agg(Cancelled=('Order ID','count'), Lost=('Sales','sum')).reset_index()
        fig_l = go.Figure()
        fig_l.add_trace(go.Bar(
            x=daily_lost['Date'], y=daily_lost['Cancelled'],
            name="Cancelled Orders", marker_color=RED, opacity=0.85,
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Cancelled: %{y}<extra></extra>"
        ))
        fig_l.add_trace(go.Scatter(
            x=daily_lost['Date'], y=daily_lost['Lost'],
            name="Lost Revenue (SAR)", mode='lines+markers', yaxis="y2",
            line=dict(color=AMBER, width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Lost Revenue: %{y:,.2f} SAR<extra></extra>"
        ))
        fig_l.update_layout(dragmode='pan', 
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title=dict(text="Cancelled Orders", font=dict(color=RED)), tickfont=dict(color=RED)),
            yaxis2=dict(title=dict(text="Lost Revenue (SAR)", font=dict(color=AMBER)), tickfont=dict(color=AMBER), overlaying="y", side="right"),
            margin=dict(l=20, r=20, t=20, b=20), height=320, showlegend=True,
            hovermode="x unified"
        )
        st.markdown("#### Daily Cancellation Trend")
        st.plotly_chart(fig_l, use_container_width=True, config={'scrollZoom': True})

        # Helper to build a "lost orders by dimension" breakdown — compact:
        # Cancelled Orders + Lost Revenue + Rate%, plus one Growth % column.
        def build_lost_breakdown(cur_lost, old_lost, fr_cur, fr_old, dim, with_compare):
            cur_g = cur_lost.groupby(dim).agg(Cancelled=('Order ID','count'), Lost=('Sales','sum')).reset_index()
            cur_g.columns = [dim, 'Cancelled', 'Lost Revenue']
            tot_cur = fr_cur.groupby(dim).size().reset_index()
            tot_cur.columns = [dim, 'Total Orders']
            cur_g = cur_g.merge(tot_cur, on=dim, how='left').fillna(0)
            cur_g['Cancel Rate %'] = (cur_g['Cancelled'] /
                                      cur_g['Total Orders'].where(cur_g['Total Orders'] > 0)) * 100
            # Column order: dimension → Total Orders → Cancelled → Lost Revenue → Cancel Rate
            cur_g = cur_g[[dim, 'Total Orders', 'Cancelled', 'Lost Revenue', 'Cancel Rate %']]
            if not with_compare or old_lost.empty:
                return cur_g.sort_values('Lost Revenue', ascending=False).reset_index(drop=True)

            old_g = old_lost.groupby(dim).agg(
                _PrevCancelled=('Order ID','count'), _PrevLost=('Sales','sum')
            ).reset_index()
            tot_old = fr_old.groupby(dim).size().reset_index()
            tot_old.columns = [dim, '_PrevTotal']
            old_g = old_g.merge(tot_old, on=dim, how='left').fillna(0)
            old_g['_PrevCancelRate'] = (old_g['_PrevCancelled'] /
                                        old_g['_PrevTotal'].where(old_g['_PrevTotal'] > 0)) * 100

            df = cur_g.merge(old_g, on=dim, how='outer')
            for c in ['Total Orders', 'Cancelled', 'Lost Revenue', 'Cancel Rate %',
                      '_PrevCancelled', '_PrevLost', '_PrevCancelRate', '_PrevTotal']:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

            df['Total Orders vs Prev %'] = ((df['Total Orders']  - df['_PrevTotal']) /
                                             df['_PrevTotal'].where(df['_PrevTotal'] > 0)) * 100
            df['Cancelled vs Prev %']    = ((df['Cancelled']     - df['_PrevCancelled']) /
                                             df['_PrevCancelled'].where(df['_PrevCancelled'] > 0)) * 100
            df['Lost vs Prev %']         = ((df['Lost Revenue']  - df['_PrevLost']) /
                                             df['_PrevLost'].where(df['_PrevLost'] > 0)) * 100
            df['Rate vs Prev pp']        = df['Cancel Rate %'] - df['_PrevCancelRate']
            df = df.drop(columns=['_PrevCancelled', '_PrevLost', '_PrevCancelRate', '_PrevTotal'])
            return df.sort_values('Lost Revenue', ascending=False).reset_index(drop=True)

        def _render_lost(df, dim_label):
            vfmt = {
                'Total Orders':  '{:,}',
                'Cancelled':     '{:,}',
                'Lost Revenue':  '{:,.0f}',
                'Cancel Rate %': '{:.1f}%',
            }
            if compare_on and 'Lost vs Prev %' in df.columns:
                render_comparison_table(
                    df,
                    growth_map={
                        'Total Orders':  'Total Orders vs Prev %',   # up = good → NOT inverted
                        'Cancelled':     'Cancelled vs Prev %',
                        'Lost Revenue':  'Lost vs Prev %',
                        'Cancel Rate %': 'Rate vs Prev pp',
                    },
                    value_format=vfmt,
                    col_labels={
                        dim_label:                  dim_label,
                        'Total Orders':             'Total Orders',
                        'Lost Revenue':             'Lost Revenue (SAR)',
                        'Cancel Rate %':            'Cancel Rate',
                        'Total Orders vs Prev %':   'vs Prev',
                        'Cancelled vs Prev %':      'vs Prev',
                        'Lost vs Prev %':           'vs Prev',
                        'Rate vs Prev pp':          'vs Prev',
                    },
                    inverse_cols={'Cancelled', 'Lost Revenue', 'Cancel Rate %'},
                    max_height="520px",
                )
            else:
                st.dataframe(
                    df.style.format(vfmt, na_rep='—'),
                    use_container_width=True, hide_index=True,
                    height=min(520, 60 + 35 * len(df)),
                    column_config={
                        dim_label:       st.column_config.TextColumn(dim_label),
                        'Total Orders':  st.column_config.TextColumn("Total Orders"),
                        "Cancelled":     st.column_config.TextColumn("Cancelled"),
                        "Lost Revenue":  st.column_config.TextColumn("Lost Revenue (SAR)"),
                        "Cancel Rate %": st.column_config.TextColumn("Cancel Rate"),
                    },
                )

        # ── Build all three breakdown tables then render with export ──────────
        by_branch = build_lost_breakdown(lost_cur, lost_old, o_cur_fr, o_old_fr, 'Location', compare_on)
        by_branch = by_branch.rename(columns={'Location': 'Branch'})
        by_agg    = build_lost_breakdown(lost_cur, lost_old, o_cur_fr, o_old_fr, 'Provider', compare_on)
        by_agg    = by_agg.rename(columns={'Provider': 'Aggregator'})
        by_brand  = build_lost_breakdown(lost_cur, lost_old, o_cur_fr, o_old_fr, 'Brand',    compare_on)

        # Export — one button exports all three sheets into one workbook
        import io as _io
        _lost_buf = _io.BytesIO()
        with pd.ExcelWriter(_lost_buf, engine='openpyxl') as _xw:
            by_branch.to_excel(_xw, sheet_name='By Branch',      index=False)
            by_agg.to_excel(   _xw, sheet_name='By Aggregator',  index=False)
            by_brand.to_excel( _xw, sheet_name='By Brand',       index=False)
            lost_cur[['Date','Brand','Provider','Location','Status','Sales']].to_excel(
                _xw, sheet_name='Raw Lost Orders', index=False)
        st.download_button(
            "📥 Export Lost Orders (Excel — 4 sheets)",
            data=_lost_buf.getvalue(),
            file_name="lost_orders.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="exp_lost",
        )

        if compare_on:
            st.info(
                "ℹ️ **Reading the coloured arrows (comparison vs. previous period):** "
                "🔴 ↑ Red = things got **worse** — more cancellations or a higher cancel rate than last period. "
                "🟢 ↓ Green = things got **better** — fewer cancellations or a lower cancel rate. "
                "The number shows by how much — for example ↑ +33% means 33% more cancellations than last period. "
                "**Total Orders** going up 🟢 is always good — it means the branch or aggregator is receiving more business."
            )

        st.markdown("#### 📍 Lost Orders by Branch")
        _render_lost(by_branch, "Branch")

        st.markdown("#### 🚚 Lost Orders by Aggregator")
        _render_lost(by_agg, "Aggregator")

        st.markdown("#### 🏷️ Lost Orders by Brand")
        _render_lost(by_brand, "Brand")

        st.markdown("""
<div style="margin-top:18px;padding:16px 20px;border-radius:8px;
            border-left:4px solid #F59E0B;background:rgba(245,158,11,0.07);
            font-size:0.875rem;line-height:1.85">
<b>📖 Guide — How to read this sheet</b><br><br>

<b>① What is "Total Orders"?</b><br>
This is the total number of orders the branch or aggregator received during the period —
both the ones that were completed <em>and</em> the ones that were cancelled.
It is shown here so you can see the full picture:
a branch with 4 cancellations out of 9 orders is in a very different situation
from a branch with 4 cancellations out of 100 orders.<br><br>

<b>② What is "Cancelled"?</b><br>
The number of orders that were rejected or cancelled — plain and simple.
More is worse. Fewer is better.<br><br>

<b>③ What is "Cancel Rate"?</b><br>
This is the percentage of total orders that got cancelled.
Formula: Cancelled ÷ Total Orders × 100.<br>
Example: 4 cancelled out of 9 total orders = <b>44.4% cancel rate</b>.<br><br>

<b>④ What does "pp" mean next to Cancel Rate?</b><br>
"pp" stands for <b>percentage points</b> — it is the plain difference between two percentages, not a ratio.<br>
Example: Cancel Rate was <b>50%</b> last period and is <b>44.4%</b> this period → change = <b>−5.6 pp</b>
(we simply subtracted: 44.4 − 50 = −5.6).<br>
We use pp here instead of % because saying "the rate improved by 11%" would be confusing
when the actual rate only moved by 5.6 points.<br><br>

<b>⑤ Why can Cancelled go UP 🔴 while Cancel Rate goes DOWN 🟢 at the same time?</b><br>
Because they measure different things. If a branch received far more orders this period,
the proportion (rate) can improve even if the raw count of cancellations ticked up slightly.<br>
Real example: <b>Previous period:</b> 3 cancelled out of 6 orders = 50% rate.<br>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
<b>Current period:</b> 4 cancelled out of 9 orders = 44% rate.<br>
→ One more order was cancelled (count went up), but the branch handled more customers overall,
so the rate actually improved. This is a <em>positive</em> story hidden inside a confusing number.
The Cancel Rate column tells you the real operational performance.
</div>
""", unsafe_allow_html=True)

# ── Items tab
with tab_items:
    st.markdown("### 🛒 Item Performance")
    if not i_cur.empty:
        cur_items = i_cur.groupby('Items').agg(Sales=('Total Amount','sum'), Qty=('Quantity','sum')).reset_index()
        cur_items.columns = ['Item', 'Sales', 'Qty']

        if compare_on and not i_old.empty:
            old_items = i_old.groupby('Items').agg(Sales=('Total Amount','sum'), Qty=('Quantity','sum')).reset_index()
            old_items.columns = ['Item', '_PrevSales', '_PrevQty']
            items_df = cur_items.merge(old_items, on='Item', how='outer').fillna(0)
            items_df['Sales vs Prev %'] = ((items_df['Sales'] - items_df['_PrevSales']) /
                                           items_df['_PrevSales'].replace(0, pd.NA)) * 100
            items_df['Qty vs Prev %']   = ((items_df['Qty']   - items_df['_PrevQty'])   /
                                           items_df['_PrevQty'].replace(0, pd.NA))   * 100
            items_df = items_df.drop(columns=['_PrevSales', '_PrevQty'])
            items_df = items_df[['Item', 'Sales', 'Sales vs Prev %', 'Qty', 'Qty vs Prev %']]
        else:
            items_df = cur_items.copy()

        # ── Sort controls + Export ──────────────────────────────────────────
        _items_sort_labels = {'Sales': 'Sales (SAR)', 'Qty': 'Quantity'}
        _i1, _i2, _i3 = st.columns([2, 1.5, 1])
        with _i1:
            _i_sort = st.selectbox("Sort by", ['Sales', 'Qty'],
                                   format_func=lambda x: _items_sort_labels.get(x, x),
                                   key="sort_items")
        with _i2:
            _i_dir  = st.radio("Direction", ['↓ High → Low', '↑ Low → High'],
                               horizontal=True, key="dir_items", label_visibility="collapsed")
        with _i3:
            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
            st.download_button(
                "📥 Export Excel",
                data=_to_excel_bytes(items_df),
                file_name="items.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="exp_items",
            )
        items_df = items_df.sort_values(_i_sort, ascending=_i_dir.startswith('↑')).reset_index(drop=True)

        # Top 10 chart always uses Sales-sorted top 10
        top10 = items_df.nlargest(10, 'Sales')
        fig_i = px.bar(top10, x='Sales', y='Item', orientation='h',
                       color_discrete_sequence=[BLUE], template="plotly_dark", text='Sales')
        fig_i.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_i.update_layout(dragmode='pan', paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=420, margin=dict(t=20, b=20),
                            yaxis=dict(autorange="reversed"), showlegend=False)
        st.markdown("#### Top 10 Items by Sales")
        st.plotly_chart(fig_i, use_container_width=True, config={'scrollZoom': True})

        st.markdown("#### Full Items Breakdown")
        if compare_on and 'Sales vs Prev %' in items_df.columns:
            render_comparison_table(
                items_df,
                growth_map={'Sales': 'Sales vs Prev %', 'Qty': 'Qty vs Prev %'},
                value_format={'Sales': '{:,.0f}', 'Qty': '{:,.0f}'},
                col_labels={'Sales': 'Sales (SAR)', 'Qty': 'Quantity',
                            'Sales vs Prev %': 'vs Prev', 'Qty vs Prev %': 'vs Prev'},
            )
        else:
            st.dataframe(
                items_df.style.format({'Sales': '{:,.0f}', 'Qty': '{:,.0f}'}, na_rep='—'),
                use_container_width=True,
                hide_index=True,
                height=min(700, 60 + 35 * len(items_df)),
                column_config={
                    "Item":  st.column_config.TextColumn("Item"),
                    "Sales": st.column_config.TextColumn("Sales (SAR)"),
                    "Qty":   st.column_config.TextColumn("Quantity"),
                },
            )
    else:
        st.info("No item data found for current filters.")

# ── Branches tab (full spec + Top10/Bottom10 highlight)
with tab_branches:
    st.markdown("### 📍 Sales by Branch")
    if not o_cur.empty:
        # Current period: sales + total orders per branch
        cur_b = o_cur.groupby('Location').agg(
            Sales=('Sales','sum'),
            Orders=('Order ID','count'),
        ).reset_index()
        cur_b.columns = ['Branch', 'Current Sales', 'Total Orders']

        # Status-unfiltered slice for accurate Completed / Rejected / Fill Rate
        b_total = o_cur_fr.groupby('Location').size().rename('TotalFR').reset_index()
        b_total.columns = ['Branch', 'TotalFR']
        b_rej_g = (o_cur_fr[o_cur_fr['Status'].isin(REJECTED_STATUSES)]
                   .groupby('Location').size().rename('Rejected').reset_index())
        b_rej_g.columns = ['Branch', 'Rejected']

        branches = cur_b.merge(b_total, on='Branch', how='left').merge(b_rej_g, on='Branch', how='left')
        branches['Rejected']    = branches['Rejected'].fillna(0).astype(int)
        branches['TotalFR']     = branches['TotalFR'].fillna(0).astype(int)
        branches['Completed']   = (branches['TotalFR'] - branches['Rejected']).clip(lower=0).astype(int)
        denom = (branches['Completed'] + branches['Rejected']).replace(0, pd.NA)
        branches['Fill Rate %'] = (branches['Completed'] / denom * 100).fillna(100)
        branches['AOV']         = branches['Current Sales'] / branches['Total Orders'].replace(0, pd.NA)

        if compare_on and not o_old.empty:
            # Aggregate all previous-period metrics per branch
            old_b = o_old.groupby('Location').agg(
                Sales=('Sales','sum'), Orders=('Order ID','count'),
            ).reset_index()
            old_b.columns = ['Branch', '_PrevSales', '_PrevOrders']
            old_b_fr = o_old_fr.groupby('Location').size().rename('_PrevTotalFR').reset_index()
            old_b_fr.columns = ['Branch', '_PrevTotalFR']
            old_b_rej = (o_old_fr[o_old_fr['Status'].isin(REJECTED_STATUSES)]
                         .groupby('Location').size().reset_index())
            old_b_rej.columns = ['Branch', '_PrevRejected']
            old_b = (old_b
                     .merge(old_b_fr,  on='Branch', how='left')
                     .merge(old_b_rej, on='Branch', how='left'))
            for c in ['_PrevSales','_PrevOrders','_PrevTotalFR','_PrevRejected']:
                old_b[c] = pd.to_numeric(old_b[c], errors='coerce').fillna(0)
            old_b['_PrevCompleted'] = (old_b['_PrevTotalFR'] - old_b['_PrevRejected']).clip(lower=0)
            _denom_old = (old_b['_PrevCompleted'] + old_b['_PrevRejected']).replace(0, pd.NA)
            old_b['_PrevFillRate']  = (old_b['_PrevCompleted'] / _denom_old * 100).fillna(100)
            old_b['_PrevAOV']       = (old_b['_PrevSales'] /
                                       old_b['_PrevOrders'].where(old_b['_PrevOrders'] > 0))

            branches = branches.merge(old_b[['Branch','_PrevSales','_PrevOrders',
                                              '_PrevCompleted','_PrevRejected',
                                              '_PrevFillRate','_PrevAOV']],
                                      on='Branch', how='left')
            for c in ['_PrevSales','_PrevOrders','_PrevCompleted','_PrevRejected',
                       '_PrevFillRate','_PrevAOV']:
                branches[c] = pd.to_numeric(branches[c], errors='coerce').fillna(0)

            def _pct_diff(cur, prev): return ((cur - prev) / prev.where(prev > 0)) * 100
            branches['Sales vs Prev %']     = _pct_diff(branches['Current Sales'], branches['_PrevSales'])
            branches['Orders vs Prev %']    = _pct_diff(branches['Total Orders'],  branches['_PrevOrders'])
            branches['Completed vs Prev %'] = _pct_diff(branches['Completed'],     branches['_PrevCompleted'])
            branches['Rejected vs Prev %']  = _pct_diff(branches['Rejected'],      branches['_PrevRejected'])
            branches['Fill Rate vs Prev pp']= branches['Fill Rate %'] - branches['_PrevFillRate']
            branches['AOV vs Prev %']       = _pct_diff(branches['AOV'],           branches['_PrevAOV'])
            branches = branches.drop(columns=[c for c in branches.columns if c.startswith('_Prev')])
            cols_order = ['Branch',
                          'Current Sales',  'Sales vs Prev %',
                          'Total Orders',   'Orders vs Prev %',
                          'Completed',      'Completed vs Prev %',
                          'Rejected',       'Rejected vs Prev %',
                          'Fill Rate %',    'Fill Rate vs Prev pp',
                          'AOV',            'AOV vs Prev %']
        else:
            cols_order = ['Branch','Current Sales','Total Orders','Completed','Rejected','Fill Rate %','AOV']

        branches = branches[[c for c in cols_order if c in branches.columns]]

        # ── Sort controls + Export ──────────────────────────────────────────
        _b_sort_opts = ['Current Sales', 'Total Orders', 'Completed', 'Rejected', 'Fill Rate %', 'AOV']
        _b_sort_opts = [c for c in _b_sort_opts if c in branches.columns]
        _branch_sort_labels = {
            'Current Sales': 'Sales (SAR)', 'Total Orders': 'Orders',
            'Completed': 'Completed', 'Rejected': 'Rejected',
            'Fill Rate %': 'Fill Rate %', 'AOV': 'AOV (SAR)',
        }
        _b1, _b2, _b3 = st.columns([2, 1.5, 1])
        with _b1:
            _b_sort = st.selectbox("Sort by", _b_sort_opts,
                                   format_func=lambda x: _branch_sort_labels.get(x, x),
                                   key="sort_branches")
        with _b2:
            _b_dir  = st.radio("Direction", ['↓ High → Low', '↑ Low → High'],
                               horizontal=True, key="dir_branches", label_visibility="collapsed")
        with _b3:
            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
            st.download_button(
                "📥 Export Excel",
                data=_to_excel_bytes(branches),
                file_name="branches.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="exp_branches",
            )
        branches = branches.sort_values(_b_sort, ascending=_b_dir.startswith('↑')).reset_index(drop=True)

        # Top-10 / Bottom-10 highlight (applied to the Sales-rank position)
        # Re-rank by Sales to get correct highlight positions regardless of sort
        _sales_rank = branches['Current Sales'].rank(ascending=False, method='first').astype(int)
        n_br = len(branches)
        top_count = min(10, n_br)
        bot_count = min(10, max(0, n_br - top_count))

        def _highlight_topbot(df):
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            for idx in df.index:
                r = _sales_rank[idx]
                if r <= top_count:
                    styles.loc[idx, :] = 'background-color: rgba(34,197,94,0.18)'
                elif r > n_br - bot_count and r > top_count:
                    styles.loc[idx, :] = 'background-color: rgba(239,68,68,0.18)'
            return styles

        if 'Sales vs Prev %' in branches.columns:
            render_comparison_table(
                branches,
                growth_map={
                    'Current Sales': 'Sales vs Prev %',
                    'Total Orders':  'Orders vs Prev %',
                    'Completed':     'Completed vs Prev %',
                    'Rejected':      'Rejected vs Prev %',
                    'Fill Rate %':   'Fill Rate vs Prev pp',
                    'AOV':           'AOV vs Prev %',
                },
                value_format={
                    'Current Sales': '{:,.0f}',
                    'Total Orders':  '{:,}',
                    'Completed':     '{:,}',
                    'Rejected':      '{:,}',
                    'Fill Rate %':   '{:.1f}%',
                    'AOV':           '{:,.0f}',
                },
                col_labels={
                    'Current Sales':        'Sales (SAR)',
                    'Total Orders':         'Orders',
                    'Fill Rate %':          'Fill Rate',
                    'AOV':                  'AOV (SAR)',
                    'Sales vs Prev %':      'vs Prev',
                    'Orders vs Prev %':     'vs Prev',
                    'Completed vs Prev %':  'vs Prev',
                    'Rejected vs Prev %':   'vs Prev',
                    'Fill Rate vs Prev pp': 'vs Prev',
                    'AOV vs Prev %':        'vs Prev',
                },
                inverse_cols={'Rejected'},
            )
        else:
            fmt_map = {'Current Sales':'{:,.0f}','Total Orders':'{:,}',
                       'Completed':'{:,}','Rejected':'{:,}',
                       'Fill Rate %':'{:.1f}%','AOV':'{:,.0f}'}
            fmt_apply = {k: v for k, v in fmt_map.items() if k in branches.columns}
            styled = (branches.style
                      .apply(_highlight_topbot, axis=None)
                      .format(fmt_apply, na_rep='—'))
            st.dataframe(styled, use_container_width=True, hide_index=True,
                         column_config={
                             "Branch":        st.column_config.TextColumn("Branch"),
                             "Current Sales": st.column_config.TextColumn("Sales (SAR)"),
                             "Total Orders":  st.column_config.TextColumn("Orders"),
                             "Completed":     st.column_config.TextColumn("Completed"),
                             "Rejected":      st.column_config.TextColumn("Rejected"),
                             "Fill Rate %":   st.column_config.TextColumn("Fill Rate %"),
                             "AOV":           st.column_config.TextColumn("AOV (SAR)"),
                         },
                         height=min(700, 60 + 35 * len(branches)))
        st.caption("🟢 The top 10 branches by Sales are highlighted in green — your best performers this period. 🔴 The bottom 10 are highlighted in red — these may need attention. Use the Sort controls above to re-order the table by any column.")
    else:
        st.info("No branch data found for current filters.")

# ── Aggregators tab
with tab_aggs:
    st.markdown("### 🚚 Aggregator Performance")
    df_agg = build_dim_comparison(o_cur, o_old, 'Provider', compare_on)
    df_agg = df_agg.rename(columns={'Provider': 'Aggregator'})

    def _agg_charts(df):
        if df.empty:
            return
        fig_ag = px.bar(
            df.head(10), x='Sales', y='Aggregator', orientation='h',
            color_discrete_sequence=[TEAL], template="plotly_dark", text='Sales',
        )
        fig_ag.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_ag.update_layout(dragmode='pan', 
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=max(260, 50 * min(len(df), 10) + 60),
            margin=dict(t=20, b=20), yaxis=dict(autorange="reversed"), showlegend=False,
        )
        st.markdown("#### Sales by Aggregator")
        st.plotly_chart(fig_ag, use_container_width=True, config={'scrollZoom': True})

    render_dim_tab(df_agg, 'Aggregator', compare_on, 'agg', extra_charts_fn=_agg_charts)

# ── Brands tab
with tab_brands:
    st.markdown("### 🏷️ Brand Performance")
    df_brand = build_dim_comparison(o_cur, o_old, 'Brand', compare_on)

    def _brand_charts(df):
        if df.empty:
            return
        fig_br = px.bar(
            df.head(10), x='Sales', y='Brand', orientation='h',
            color_discrete_sequence=[PURPLE], template="plotly_dark", text='Sales',
        )
        fig_br.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_br.update_layout(dragmode='pan', 
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=max(260, 50 * min(len(df), 10) + 60),
            margin=dict(t=20, b=20), yaxis=dict(autorange="reversed"), showlegend=False,
        )
        st.markdown("#### Sales by Brand")
        st.plotly_chart(fig_br, use_container_width=True, config={'scrollZoom': True})

    render_dim_tab(df_brand, 'Brand', compare_on, 'brand', extra_charts_fn=_brand_charts)

# ── Technologies tab
with tab_tech:
    st.markdown("### ⚙️ Technology / Channel Performance")
    df_tech = build_dim_comparison(o_cur, o_old, 'Technology', compare_on)

    def _tech_charts(df):
        if df.empty:
            return
        fig_tc = px.pie(
            df, values='Sales', names='Technology',
            color_discrete_sequence=PAL, template="plotly_dark",
            hole=0.4,
        )
        fig_tc.update_traces(
            textinfo='label+percent',
            hovertemplate="<b>%{label}</b><br>Sales: %{value:,.0f} SAR<br>Share: %{percent}<extra></extra>",
        )
        fig_tc.update_layout(dragmode='pan', 
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=360, margin=dict(t=20, b=20), showlegend=True,
        )
        st.markdown("#### Sales Mix by Technology")
        st.plotly_chart(fig_tc, use_container_width=True, config={'scrollZoom': True})

    render_dim_tab(df_tech, 'Technology', compare_on, 'tech', extra_charts_fn=_tech_charts)
