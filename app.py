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
st.title("📊 Alnumuw Operational Dashboard")

uploaded = st.file_uploader("Upload Elnumuw_Data.xlsx to populate dashboard views", type=["xlsx"])

if not uploaded:
    st.info("⬆️ Please upload your Excel data sheet package above to begin.")
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
                f"ℹ️ {_unmatched_order_count} orders have no matching items in the Items sheet — they "
                f"appear as \"{UNMATCHED_ITEM_LABEL}\". Picking only real items will exclude them."
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
    k_cols[0].metric("💰 Gross Revenue", f"{rev_cur:,.2f} SAR", f"{_pct(rev_cur, rev_old):+.1f}% vs Prev")
    k_cols[1].metric("📦 Total Orders", f"{ord_cur:,}", f"{_pct(ord_cur, ord_old):+.1f}% vs Prev")
    k_cols[2].metric("✅ Completed Orders", f"{comp_cur:,}", f"{_pct(comp_cur, comp_old):+.1f}% vs Prev")
    k_cols[3].metric("❌ Rejected Orders", f"{rej_cur:,}", f"{_pct(rej_cur, rej_old):+.1f}% vs Prev", delta_color="inverse")
    k_cols[4].metric(fill_label, f"{fill_cur:.2f}%", f"{(fill_cur - fill_old):+.1f} pp vs Prev")
    st.caption(f"Net Revenue (Sales − Discount): **{net_cur:,.2f} SAR** current  ·  **{net_old:,.2f} SAR** previous  ·  Discount given this period: {disc_cur:,.2f} SAR")
else:
    k_cols[0].metric("💰 Gross Revenue", f"{rev_cur:,.2f} SAR")
    k_cols[1].metric("📦 Total Orders", f"{ord_cur:,}")
    k_cols[2].metric("✅ Completed Orders", f"{comp_cur:,}")
    k_cols[3].metric("❌ Rejected Orders", f"{rej_cur:,}")
    k_cols[4].metric(fill_label, f"{fill_cur:.2f}%")
    st.caption(f"Net Revenue (Sales − Discount): **{net_cur:,.2f} SAR**  ·  Discount given: {disc_cur:,.2f} SAR")

if status_user_filtered:
    st.caption("\\* Fill Rate ignores the Status filter so it stays meaningful (otherwise filtering to 'Completed' would force it to 100%).")

# ══════════════════════════════════════════════════════════════════════════════
# COMPARISON TABLE HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def build_dim_comparison(cur_df, old_df, dim_col, with_compare):
    """Per-dimension breakdown: Current Sales/Orders + Previous + Diff + Growth%
    when with_compare. Sorted by Current Sales desc."""
    cur = cur_df.groupby(dim_col).agg(Sales=('Sales','sum'), Orders=('Order ID','count')).reset_index()
    cur.columns = [dim_col, 'Current Sales', 'Current Orders']
    if not with_compare or old_df.empty:
        return cur.sort_values('Current Sales', ascending=False).reset_index(drop=True)
    old = old_df.groupby(dim_col).agg(Sales=('Sales','sum'), Orders=('Order ID','count')).reset_index()
    old.columns = [dim_col, 'Previous Sales', 'Previous Orders']
    df = cur.merge(old, on=dim_col, how='outer').fillna(0)
    df['Difference'] = df['Current Sales'] - df['Previous Sales']
    df['Growth %'] = ((df['Current Sales'] - df['Previous Sales']) /
                      df['Previous Sales'].replace(0, pd.NA)) * 100
    return df.sort_values('Current Sales', ascending=False).reset_index(drop=True)

def comparison_column_config(with_compare):
    cfg = {
        "Current Sales":  st.column_config.NumberColumn("Current Sales (SAR)",  format="%.2f"),
        "Current Orders": st.column_config.NumberColumn("Current Orders"),
    }
    if with_compare:
        cfg.update({
            "Previous Sales":  st.column_config.NumberColumn("Previous Sales (SAR)",  format="%.2f"),
            "Previous Orders": st.column_config.NumberColumn("Previous Orders"),
            "Difference":      st.column_config.NumberColumn("Difference (SAR)",      format="%.2f"),
            "Growth %":        st.column_config.NumberColumn("Growth %",              format="%.1f%%"),
        })
    return cfg

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
tab_summary, tab_orders, tab_items, tab_branches, tab_aggs, tab_brands, tab_tech = st.tabs(
    ["📊 Summary", "📦 Orders", "🛒 Items", "📍 Branches", "🚚 Aggregators", "🏷️ Brands", "⚙️ Technologies"]
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

        fig.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title=dict(text="Revenue (SAR)", font=dict(color=BLUE)), tickfont=dict(color=BLUE)),
            yaxis2=dict(title=dict(text="Orders Count", font=dict(color=AMBER)), tickfont=dict(color=AMBER), overlaying="y", side="right"),
            margin=dict(l=20, r=20, t=30, b=20), height=400, showlegend=True,
            hovermode="x unified",
            barmode='group' if compare_on else 'overlay'
        )
        st.plotly_chart(fig, use_container_width=True)

        if compare_on:
            st.caption("Previous period dates are aligned onto the current period's calendar so the lines overlay directly. Hover any point for exact values.")
    else:
        st.info("No timeline data found for current filters.")

# ── Orders tab
with tab_orders:
    st.markdown("### 📦 Order Operations")
    if not o_cur.empty:
        # Daily orders by status
        daily = o_cur.groupby(['Date','Status'])['Order ID'].count().reset_index()
        daily.columns = ['Date','Status','Orders']
        fig_o = px.bar(daily, x='Date', y='Orders', color='Status', barmode='stack',
                       color_discrete_map={'Completed': GREEN, 'Canceled': RED, 'Cancelled': RED},
                       template="plotly_dark", title=None)
        fig_o.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=320, margin=dict(t=20, b=20), hovermode='x unified')
        st.plotly_chart(fig_o, use_container_width=True)

        # AOV trend
        aov_df = o_cur.groupby('Date').agg(Sales=('Sales','sum'), Orders=('Order ID','count')).reset_index()
        aov_df['AOV'] = aov_df['Sales'] / aov_df['Orders'].replace(0, pd.NA)
        fig_a = go.Figure()
        fig_a.add_trace(go.Scatter(
            x=aov_df['Date'], y=aov_df['AOV'], mode='lines+markers',
            name="AOV", line=dict(color=PURPLE, width=2),
            hovertemplate="<b>%{x|%Y-%m-%d}</b><br>AOV: %{y:,.2f} SAR<extra></extra>"
        ))
        fig_a.update_layout(
            template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="Average Order Value (SAR)"),
            height=280, margin=dict(t=20, b=20), showlegend=False
        )
        st.markdown("#### Daily Average Order Value (AOV)")
        st.plotly_chart(fig_a, use_container_width=True)

        st.markdown("#### Raw Filtered Orders")
        st.dataframe(
            o_cur,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales":    st.column_config.NumberColumn("Sales (SAR)",    format="%.2f"),
                "Discount": st.column_config.NumberColumn("Discount (SAR)", format="%.2f"),
                "Date":     st.column_config.DateColumn("Order Date", format="YYYY-MM-DD"),
            }
        )
    else:
        st.info("No order data found for current filters.")

# ── Items tab
with tab_items:
    st.markdown("### 🛒 Item Performance")
    if not i_cur.empty:
        cur_items = i_cur.groupby('Items').agg(Sales=('Total Amount','sum'), Qty=('Quantity','sum')).reset_index()
        cur_items.columns = ['Item', 'Current Sales', 'Current Qty']

        if compare_on and not i_old.empty:
            old_items = i_old.groupby('Items').agg(Sales=('Total Amount','sum'), Qty=('Quantity','sum')).reset_index()
            old_items.columns = ['Item', 'Previous Sales', 'Previous Qty']
            items_df = cur_items.merge(old_items, on='Item', how='outer').fillna(0)
            items_df['Difference'] = items_df['Current Sales'] - items_df['Previous Sales']
            items_df['Growth %'] = ((items_df['Current Sales'] - items_df['Previous Sales']) /
                                    items_df['Previous Sales'].replace(0, pd.NA)) * 100
            items_df = items_df.sort_values('Current Sales', ascending=False).reset_index(drop=True)
            cfg = {
                "Current Sales":  st.column_config.NumberColumn("Current Sales (SAR)",  format="%.2f"),
                "Previous Sales": st.column_config.NumberColumn("Previous Sales (SAR)", format="%.2f"),
                "Difference":     st.column_config.NumberColumn("Difference (SAR)",     format="%.2f"),
                "Growth %":       st.column_config.NumberColumn("Growth %",             format="%.1f%%"),
                "Current Qty":    st.column_config.NumberColumn("Current Qty"),
                "Previous Qty":   st.column_config.NumberColumn("Previous Qty"),
            }
        else:
            items_df = cur_items.sort_values('Current Sales', ascending=False).reset_index(drop=True)
            cfg = {
                "Current Sales": st.column_config.NumberColumn("Sales (SAR)", format="%.2f"),
                "Current Qty":   st.column_config.NumberColumn("Quantity"),
            }

        # Top 10 chart
        top10 = items_df.head(10)
        fig_i = px.bar(top10, x='Current Sales', y='Item', orientation='h',
                       color_discrete_sequence=[BLUE], template="plotly_dark", text='Current Sales')
        fig_i.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_i.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=420, margin=dict(t=20, b=20),
                            yaxis=dict(autorange="reversed"), showlegend=False)
        st.markdown("#### Top 10 Items by Sales")
        st.plotly_chart(fig_i, use_container_width=True)

        st.markdown("#### Full Items Breakdown")
        st.dataframe(items_df, use_container_width=True, hide_index=True, column_config=cfg)
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
            old_b = o_old.groupby('Location').agg(Sales=('Sales','sum')).reset_index()
            old_b.columns = ['Branch', 'Previous Sales']
            branches = branches.merge(old_b, on='Branch', how='left')
            branches['Previous Sales'] = branches['Previous Sales'].fillna(0)
            branches['Sales Growth %'] = ((branches['Current Sales'] - branches['Previous Sales']) /
                                          branches['Previous Sales'].replace(0, pd.NA)) * 100
            cols_order = ['Branch','Current Sales','Previous Sales','Sales Growth %',
                          'Total Orders','Completed','Rejected','Fill Rate %','AOV']
        else:
            cols_order = ['Branch','Current Sales','Total Orders','Completed','Rejected','Fill Rate %','AOV']

        branches = branches.sort_values('Current Sales', ascending=False).reset_index(drop=True)
        branches = branches[[c for c in cols_order if c in branches.columns]]

        # Top-10 / Bottom-10 row highlight via pandas Styler. The styled
        # DataFrame still supports st.dataframe's clickable header sorting.
        def _highlight_topbot(df):
            n = len(df)
            styles = pd.DataFrame('', index=df.index, columns=df.columns)
            if n == 0:
                return styles
            top_count = min(10, n)
            # Don't overlap top and bottom when n is small
            bot_count = min(10, max(0, n - top_count))
            for i in range(top_count):
                styles.iloc[i, :] = 'background-color: rgba(34,197,94,0.18)'
            for i in range(n - bot_count, n):
                if i >= top_count:
                    styles.iloc[i, :] = 'background-color: rgba(239,68,68,0.18)'
            return styles

        fmt_map = {
            'Current Sales':   '{:,.2f}',
            'Previous Sales':  '{:,.2f}',
            'Sales Growth %':  '{:+.1f}%',
            'Total Orders':    '{:,}',
            'Completed':       '{:,}',
            'Rejected':        '{:,}',
            'Fill Rate %':     '{:.1f}%',
            'AOV':             '{:,.2f}',
        }
        fmt_apply = {k: v for k, v in fmt_map.items() if k in branches.columns}
        styled = branches.style.apply(_highlight_topbot, axis=None).format(fmt_apply, na_rep='—')

        st.dataframe(styled, use_container_width=True, hide_index=True,
                     height=min(720, 60 + 35 * len(branches)))
        st.caption("🟢 Top 10 branches by sales highlighted in green · 🔴 Bottom 10 in red · click any column header to re-sort.")
    else:
        st.info("No branch data found for current filters.")

# ── Aggregators
with tab_aggs:
    st.markdown("### 🚚 Channel Delivery Aggregator Performance")
    if not o_cur.empty:
        agg_df = build_dim_comparison(o_cur, o_old, 'Provider', compare_on)
        agg_df = agg_df.rename(columns={'Provider':'Aggregator'})

        col_p, col_t = st.columns([1, 2])
        with col_p:
            pie_df = agg_df[['Aggregator','Current Sales']].copy()
            fig_p = px.pie(pie_df, names='Aggregator', values='Current Sales',
                           color_discrete_sequence=PAL, hole=0.4, template="plotly_dark")
            fig_p.update_traces(textposition='inside', textinfo='percent+label')
            fig_p.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                height=340, margin=dict(t=10, b=10, l=10, r=10),
                                showlegend=False)
            st.plotly_chart(fig_p, use_container_width=True)
        with col_t:
            cfg = comparison_column_config(compare_on)
            cfg["Aggregator"] = st.column_config.TextColumn("Aggregator")
            st.dataframe(agg_df, use_container_width=True, hide_index=True, column_config=cfg)
    else:
        st.info("No aggregator data found for current filters.")

# ── Brands
with tab_brands:
    st.markdown("### 🏷️ Brand Performance")
    if not o_cur.empty:
        brand_df = build_dim_comparison(o_cur, o_old, 'Brand', compare_on)

        fig_b = px.bar(brand_df, x='Brand', y='Current Sales', color='Brand', text_auto='.2s',
                       color_discrete_sequence=PAL, template="plotly_dark")
        fig_b.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=360, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig_b, use_container_width=True)

        cfg = comparison_column_config(compare_on)
        cfg["Brand"] = st.column_config.TextColumn("Brand")
        st.dataframe(brand_df, use_container_width=True, hide_index=True, column_config=cfg)
    else:
        st.info("No brand data found for current filters.")

# ── Technologies
with tab_tech:
    st.markdown("### ⚙️ Order Management Technology")
    if not o_cur.empty:
        tech_df = build_dim_comparison(o_cur, o_old, 'Technology', compare_on)

        fig_t = px.bar(tech_df, y='Technology', x='Current Sales', orientation='h', color='Technology',
                       color_discrete_sequence=PAL, template="plotly_dark")
        fig_t.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=300, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig_t, use_container_width=True)

        cfg = comparison_column_config(compare_on)
        cfg["Technology"] = st.column_config.TextColumn("Technology")
        st.dataframe(tech_df, use_container_width=True, hide_index=True, column_config=cfg)
    else:
        st.info("No technology data found for current filters.")
