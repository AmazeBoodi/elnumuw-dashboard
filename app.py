import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Elnumuw Dashboard", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════════════════════
# DESIGN TOKENS
# ══════════════════════════════════════════════════════════════════════════════
BLUE    = "#2563EB"; LBLUE  = "#EFF6FF"
GREEN   = "#16A34A"; LGREEN = "#F0FDF4"
RED     = "#DC2626"; LRED   = "#FEF2F2"
AMBER   = "#D97706"; PURPLE = "#7C3AED"
GRAY    = "#6B7280"; LGRAY  = "#F9FAFB"
BORDER  = "#E5E7EB"; TEXT   = "#111827"
MUTED   = "#6B7280"; WHITE  = "#FFFFFF"
PAL = [BLUE,"#0EA5E9","#6366F1","#8B5CF6","#EC4899",GREEN,AMBER,"#F97316","#14B8A6","#84CC16"]

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*, [data-testid] {{ font-family:'Inter',sans-serif; }}
[data-testid="stAppViewContainer"] {{ background:#0F1117; }}
[data-testid="stSidebar"] {{ background:#161B27; border-right:1px solid #1E2433; }}
[data-testid="stSidebar"] * {{ color:#CBD5E1 !important; font-family:'Inter',sans-serif !important; }}
.block-container {{ padding:1.5rem 2rem 3rem; max-width:1600px; }}

/* ── KPI CARD ── */
.kpi {{
    background:#161B27; border:1px solid #1E2433; border-radius:12px;
    padding:1.1rem 1.3rem; position:relative; overflow:hidden;
}}
.kpi-accent {{ position:absolute; top:0; left:0; width:4px; height:100%; border-radius:12px 0 0 12px; }}
.kpi-label  {{ font-size:.7rem; font-weight:600; text-transform:uppercase;
               letter-spacing:.07em; color:#64748B; margin-bottom:.5rem; }}
.kpi-value  {{ font-size:1.8rem; font-weight:800; color:#F1F5F9; line-height:1; letter-spacing:-.03em; }}
.kpi-delta  {{ font-size:.75rem; font-weight:600; margin-top:.4rem; display:flex; align-items:center; gap:.3rem; }}
.kpi-sub    {{ font-size:.68rem; color:#64748B; margin-top:.2rem; }}
.up   {{ color:{GREEN}; }}
.down {{ color:{RED}; }}
.neu  {{ color:#64748B; }}

/* ── SECTION DIVIDER ── */
.section-header {{
    font-size:.72rem; font-weight:700; text-transform:uppercase; letter-spacing:.1em;
    color:#64748B; padding:.4rem 0; border-bottom:1px solid #1E2433;
    margin:1.4rem 0 1rem;
}}

/* ── TABLE ── */
.tbl {{ width:100%; border-collapse:collapse; font-size:.79rem; }}
.tbl th {{
    background:#0F1117; color:#64748B; font-size:.68rem; font-weight:700;
    text-transform:uppercase; letter-spacing:.06em;
    padding:.55rem .9rem; border-bottom:1px solid #1E2433; text-align:left;
}}
.tbl td {{ padding:.6rem .9rem; border-bottom:1px solid #1E2433; color:#E2E8F0; }}
.tbl tr:last-child td {{ border-bottom:none; }}
.tbl tr:hover td {{ background:#1E2433; }}
.tbl .num {{ text-align:right; font-variant-numeric:tabular-nums; font-weight:600; }}
.badge {{ display:inline-block; padding:.15rem .55rem; border-radius:20px; font-size:.68rem; font-weight:600; }}
.badge-up   {{ background:rgba(22,163,74,.2);  color:{GREEN}; }}
.badge-down {{ background:rgba(220,38,38,.2);  color:{RED};   }}
.badge-neu  {{ background:rgba(107,114,128,.2); color:#64748B; }}

/* ── TABS ── */
[data-testid="stTabs"] {{ border-bottom:1px solid #1E2433; }}
[data-testid="stTabs"] button {{
    color:#64748B !important; font-size:.82rem; font-weight:500;
    padding:.55rem 1.1rem; background:transparent !important;
    border-bottom:2px solid transparent !important; border-radius:0 !important;
    margin-bottom:-1px;
}}
[data-testid="stTabs"] button[aria-selected="true"] {{
    color:{BLUE} !important; border-bottom:2px solid {BLUE} !important; font-weight:700 !important;
}}

/* ── SIDEBAR FILTERS ── */
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background:rgba(37,99,235,.2) !important; color:{BLUE} !important;
    border:1px solid rgba(37,99,235,.4) !important; border-radius:5px !important;
    font-size:.72rem !important;
}}
div[data-testid="stButton"] button {{
    background:#1E2433; border:1px solid #2D3748; color:#E2E8F0 !important;
    border-radius:8px; font-size:.75rem; padding:.35rem .9rem; width:100%;
    font-weight:500;
}}
div[data-testid="stButton"] button:hover {{ background:#2D3748; }}

/* comparison banner */
.cmp-bar {{
    background:rgba(37,99,235,.1); border:1px solid rgba(37,99,235,.3); border-radius:10px;
    padding:.6rem 1rem; font-size:.78rem; color:#93C5FD; font-weight:500;
    margin-bottom:1.2rem; display:flex; align-items:center; gap:.6rem; flex-wrap:wrap;
}}

/* sidebar section label */
.sbl {{
    font-size:.62rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.09em; color:#475569; margin:.8rem 0 .2rem;
}}

#MainMenu, footer {{ visibility:hidden; }}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data
def load():
    xl  = pd.ExcelFile(r"Elnumuw_Data.xlsx")
    o   = xl.parse("Order Report")
    i   = xl.parse("Items Report")
    for df in [o, i]:
        df['Date']        = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()
        df['Week Number'] = df['Date'].dt.isocalendar().week.astype(int)
        df['Month']       = df['Date'].dt.month
        df['Month Name']  = df['Date'].dt.strftime('%B')
        df['Year']        = df['Date'].dt.year
    for col in ['Brand','Provider','Technology','Status','Location']:
        for df in [o, i]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.title()
    o['Sales']    = pd.to_numeric(o['Sales'],    errors='coerce').fillna(0)
    o['Discount'] = pd.to_numeric(o['Discount'], errors='coerce').fillna(0)
    i['Quantity'] = pd.to_numeric(i['Quantity'], errors='coerce').fillna(0)
    return o, i

try:
    df_all_o, df_all_i = load()
except Exception as e:
    st.error(f"Cannot load Elnumuw_Data.xlsx — {e}"); st.stop()

G_MIN = df_all_o['Date'].min().date()
G_MAX = df_all_o['Date'].max().date()

master = df_all_o[['Order ID','Brand','Provider','Technology','Location','Status']].merge(
    df_all_i[['Order ID','Items']].drop_duplicates(), on='Order ID', how='left')

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR FILTERS
# ══════════════════════════════════════════════════════════════════════════════
def avail(col, constraints):
    df = master.copy()
    for c, vals in constraints.items():
        if c != col and vals:
            df = df[df[c].isin(vals)]
    return sorted(df[col].dropna().unique())

with st.sidebar:
    st.markdown("## 📊 Elnumuw")
    st.markdown('<div class="sbl">Date Range</div>', unsafe_allow_html=True)
    date_range = st.date_input("", [G_MIN, G_MAX],
                               min_value=G_MIN, max_value=G_MAX,
                               label_visibility="collapsed")
    sd = date_range[0] if len(date_range)==2 else G_MIN
    ed = date_range[1] if len(date_range)==2 else G_MAX

    st.markdown('<div class="sbl">Compare Period</div>', unsafe_allow_html=True)
    compare_on = st.toggle("Enable comparison", value=False, label_visibility="collapsed",
                           help="Compare current period vs a previous period")

    n_days = (pd.Timestamp(ed) - pd.Timestamp(sd)).days + 1
    cmp_e  = pd.Timestamp(sd) - pd.Timedelta(days=1)
    cmp_s  = max(cmp_e - pd.Timedelta(days=n_days-1), pd.Timestamp(G_MIN))

    if compare_on:
        cr = st.date_input("vs Period", [cmp_s.date(), cmp_e.date()],
                           min_value=G_MIN, max_value=G_MAX,
                           label_visibility="visible")
        if len(cr)==2:
            cmp_s = pd.Timestamp(cr[0])
            cmp_e = pd.Timestamp(cr[1])

    st.markdown("---")

    def ms(label, col, key):
        cx = {
            'Brand':      st.session_state.get('f_brand', []),
            'Technology': st.session_state.get('f_tech',  []),
            'Provider':   st.session_state.get('f_prov',  []),
            'Location':   st.session_state.get('f_loc',   []),
            'Status':     st.session_state.get('f_status',[]),
            'Items':      st.session_state.get('f_items', []),
        }
        opts = avail(col, cx)
        cur  = [v for v in st.session_state.get(key, []) if v in opts]
        sel  = st.multiselect(label, opts, default=opts, key=key)
        return sel if sel else opts

    brand  = ms("🏷️ Brand",      "Brand",      "f_brand")
    tech   = ms("⚙️ Technology",  "Technology", "f_tech")
    prov   = ms("🚚 Provider",    "Provider",   "f_prov")
    loc    = ms("📍 Location",    "Location",   "f_loc")
    status = ms("✅ Status",      "Status",     "f_status")

    st.markdown("---")
    i_opts   = avail('Items', {'Brand':brand,'Provider':prov,'Technology':tech,'Status':status})
    item_raw = st.multiselect("🛒 Item", i_opts, default=[], key="f_items",
                              placeholder="All items")
    item_f   = item_raw if item_raw else i_opts

    if st.button("↺ Reset All Filters"):
        for k in ['f_brand','f_tech','f_prov','f_loc','f_status','f_items']:
            st.session_state.pop(k, None)
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FILTER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def fo(s=None, e=None):
    df = df_all_o
    s  = pd.Timestamp(s or sd); e = pd.Timestamp(e or ed)
    m  = ((df['Date']>=s)&(df['Date']<=e) &
          df['Brand'].isin(brand)&df['Provider'].isin(prov)&
          df['Location'].isin(loc)&df['Status'].isin(status)&
          df['Technology'].isin(tech))
    return df[m]

def fi(s=None, e=None):
    df = df_all_i
    s  = pd.Timestamp(s or sd); e = pd.Timestamp(e or ed)
    m  = ((df['Date']>=s)&(df['Date']<=e) &
          df['Brand'].isin(brand)&df['Provider'].isin(prov)&
          df['Technology'].isin(tech)&df['Status'].isin(status)&
          df['Items'].isin(item_f))
    if 'Location' in df.columns: m = m & df['Location'].isin(loc)
    return df[m]

def agg(o, i):
    s=o['Sales'].sum(); n=o['Order ID'].nunique()
    return dict(sales=s, orders=n, aov=s/n if n else 0,
                qty=i['Quantity'].sum(), disc=o['Discount'].sum(),
                cancelled=o[o['Status']=='Canceled']['Order ID'].nunique())

def pct(a, b):
    if b and b!=0: return round((a-b)/abs(b)*100,1)
    return None

def delta_badge(v):
    if v is None: return '<span class="badge badge-neu">—</span>'
    arr="↑" if v>=0 else "↓"; cls="badge-up" if v>=0 else "badge-down"
    return f'<span class="badge {cls}">{arr} {abs(v)}%</span>'

def delta_inline(v):
    if v is None: return '<span class="neu">—</span>'
    arr="↑" if v>=0 else "↓"; cls="up" if v>=0 else "down"
    return f'<span class="{cls}">{arr} {abs(v)}%</span>'

# Chart helper
DARK = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94A3B8", size=11),
    margin=dict(t=10,b=30,l=10,r=10),
)
_n={"v":0}
def pc(fig, h=300):
    fig.update_layout(height=h, **DARK)
    fig.update_xaxes(showgrid=True,gridcolor="#1E2433",zeroline=False,
                     linecolor="#1E2433",tickfont=dict(size=10))
    fig.update_yaxes(showgrid=True,gridcolor="#1E2433",zeroline=False,
                     linecolor="#1E2433",tickfont=dict(size=10))
    _n["v"]+=1
    st.plotly_chart(fig, use_container_width=True, key=f"c{_n['v']}")

def cd(df):
    d=df.copy(); d["Date"]=d["Date"].dt.normalize(); return d

# Pull data
o_cur = fo(sd,ed);       i_cur = fi(sd,ed)
o_cmp = fo(cmp_s,cmp_e); i_cmp = fi(cmp_s,cmp_e)
cur   = agg(o_cur,i_cur); cmp_data = agg(o_cmp,i_cmp)

if compare_on:
    st.markdown(
        f'<div class="cmp-bar">🔁 <b>{sd} → {ed}</b>'
        f' &nbsp;vs&nbsp; <b>{cmp_s.date()} → {cmp_e.date()}</b>'
        f' &nbsp;·&nbsp; {n_days}-day windows</div>',
        unsafe_allow_html=True)

if o_cur.empty:
    st.warning("⚠️ No data for this selection. Adjust the filters or date range.")
    st.stop()

# KPI card builder
def kpi_card(col, label, val_str, chg, sub, accent):
    d  = delta_inline(chg) if compare_on else ""
    vs = f"<div class='kpi-sub'>vs {sub} prev</div>" if compare_on else ""
    col.markdown(f"""
    <div class="kpi">
      <div class="kpi-accent" style="background:{accent}"></div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val_str}</div>
      <div class="kpi-delta">{d}</div>
      {vs}
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
t1,t2,t3,t4 = st.tabs(["📊  Summary","📦  Orders","💰  Revenue & Sales","🛒  Items"])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
with t1:
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    k1,k2,k3,k4 = st.columns(4)
    kpi_card(k1,"Total Revenue",   f"SAR {cur['sales']:,.0f}", pct(cur['sales'],cmp_data['sales']),   f"SAR {cmp_data['sales']:,.0f}",  BLUE)
    kpi_card(k2,"Total Orders",    f"{cur['orders']:,}",        pct(cur['orders'],cmp_data['orders']), f"{cmp_data['orders']:,}",        GREEN)
    kpi_card(k3,"Avg Order Value", f"SAR {cur['aov']:,.2f}",    pct(cur['aov'],cmp_data['aov']),       f"SAR {cmp_data['aov']:,.2f}",    AMBER)
    kpi_card(k4,"Items Sold",      f"{int(cur['qty']):,}",      pct(cur['qty'],cmp_data['qty']),       f"{int(cmp_data['qty']):,}",      PURPLE)
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Revenue Over Time</div>', unsafe_allow_html=True)
    daily = cd(o_cur).groupby('Date')['Sales'].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily['Date'],y=daily['Sales'],name="Revenue",
                             line=dict(color=BLUE,width=2.5),
                             fill='tozeroy',fillcolor='rgba(37,99,235,0.07)',mode='lines'))
    if compare_on and not o_cmp.empty:
        cd2 = cd(o_cmp).groupby('Date')['Sales'].sum().reset_index()
        cd2['Day']=range(1,len(cd2)+1); daily['Day']=range(1,len(daily)+1)
        merged = pd.concat([
            daily[['Day','Sales']].assign(Period=f"Current ({sd}–{ed})"),
            cd2[['Day','Sales']].assign(Period=f"Previous ({cmp_s.date()}–{cmp_e.date()})")
        ])
        fig2 = px.line(merged,x='Day',y='Sales',color='Period',
                       color_discrete_map={f"Current ({sd}–{ed})":BLUE,
                                           f"Previous ({cmp_s.date()}–{cmp_e.date()})":GRAY})
        for tr in fig2.data:
            tr.line.width=2; tr.line.dash='dot' if 'Previous' in tr.name else 'solid'
            fig.add_trace(tr)
    fig.update_layout(legend=dict(orientation='h',y=1.12,x=0),xaxis=dict(tickformat="%b %d"))
    pc(fig,270)

    st.markdown('<div class="section-header">Breakdown</div>', unsafe_allow_html=True)
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown(f'<div style="font-size:.8rem;font-weight:700;color:#F1F5F9;margin-bottom:.5rem">By Provider</div>', unsafe_allow_html=True)
        pv=o_cur.groupby('Provider').agg(Revenue=('Sales','sum')).reset_index().sort_values('Revenue')
        fig=px.bar(pv,x='Revenue',y='Provider',orientation='h',text_auto='.2s',color_discrete_sequence=[BLUE])
        fig.update_traces(marker_color=BLUE,textfont_size=10)
        fig.update_layout(showlegend=False,yaxis=dict(categoryorder='total ascending'))
        pc(fig,250)
    with c2:
        st.markdown(f'<div style="font-size:.8rem;font-weight:700;color:#F1F5F9;margin-bottom:.5rem">By Brand (Top 8)</div>', unsafe_allow_html=True)
        bb=o_cur.groupby('Brand')['Sales'].sum().sort_values(ascending=False).head(8).reset_index()
        fig=px.bar(bb,x='Sales',y='Brand',orientation='h',text_auto='.2s',color_discrete_sequence=["#6366F1"])
        fig.update_layout(showlegend=False,yaxis=dict(categoryorder='total ascending'))
        pc(fig,250)
    with c3:
        st.markdown(f'<div style="font-size:.8rem;font-weight:700;color:#F1F5F9;margin-bottom:.5rem">By Technology</div>', unsafe_allow_html=True)
        td=o_cur.groupby('Technology')['Sales'].sum().reset_index()
        fig=px.pie(td,values='Sales',names='Technology',hole=0.55,color_discrete_sequence=[BLUE,"#6366F1",GREEN])
        fig.update_traces(textposition='outside',textinfo='percent+label',textfont_size=11)
        fig.update_layout(showlegend=False)
        pc(fig,250)

    st.markdown('<div class="section-header">Provider Performance</div>', unsafe_allow_html=True)
    pt=o_cur.groupby('Provider').agg(Revenue=('Sales','sum'),Orders=('Order ID','nunique'),
                                     AOV=('Sales','mean'),Discount=('Discount','sum')
                                    ).reset_index().sort_values('Revenue',ascending=False)
    if compare_on and not o_cmp.empty:
        pc2=o_cmp.groupby('Provider')['Sales'].sum().reset_index(name='Rev_cmp')
        pt=pt.merge(pc2,on='Provider',how='left').fillna(0)
        pt['chg']=pt.apply(lambda r:pct(r['Revenue'],r['Rev_cmp']),axis=1)
    rows=""
    for _,r in pt.iterrows():
        chg_c=delta_badge(r.get('chg')) if compare_on else ""
        rows+=f"<tr><td><b>{r['Provider']}</b></td><td class='num'>SAR {r['Revenue']:,.0f}</td><td class='num'>{int(r['Orders']):,}</td><td class='num'>SAR {r['AOV']:,.2f}</td><td class='num'>SAR {r['Discount']:,.0f}</td>{'<td>'+chg_c+'</td>' if compare_on else ''}</tr>"
    cmp_th="<th>vs Prev</th>" if compare_on else ""
    st.markdown(f"<table class='tbl'><tr><th>Provider</th><th>Revenue</th><th>Orders</th><th>AOV</th><th>Discount</th>{cmp_th}</tr>{rows}</table>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — ORDERS
# ─────────────────────────────────────────────────────────────────────────────
with t2:
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    cancelled=cur['cancelled']; cmp_canc=cmp_data['cancelled']
    apd=cur['orders']/n_days
    cmp_days=max((pd.Timestamp(cmp_e)-pd.Timestamp(cmp_s)).days+1,1)
    cmp_apd=cmp_data['orders']/cmp_days
    k1,k2,k3,k4=st.columns(4)
    kpi_card(k1,"Total Orders",     f"{cur['orders']:,}",        pct(cur['orders'],cmp_data['orders']),f"{cmp_data['orders']:,}",BLUE)
    kpi_card(k2,"Avg Orders / Day", f"{apd:.1f}",                pct(apd,cmp_apd),                    f"{cmp_apd:.1f}",         GREEN)
    kpi_card(k3,"Avg Order Value",  f"SAR {cur['aov']:,.2f}",    pct(cur['aov'],cmp_data['aov']),     f"SAR {cmp_data['aov']:,.2f}",AMBER)
    kpi_card(k4,"Cancelled Orders", f"{cancelled:,}",            pct(cancelled,cmp_canc),             f"{cmp_canc:,}",          RED)
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Daily Orders Trend</div>', unsafe_allow_html=True)
    od=cd(o_cur).groupby('Date')['Order ID'].nunique().reset_index(name='Orders')
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=od['Date'],y=od['Orders'],name="Orders",
                             line=dict(color=BLUE,width=2.5),
                             fill='tozeroy',fillcolor='rgba(37,99,235,0.07)',mode='lines'))
    if compare_on and not o_cmp.empty:
        od2=cd(o_cmp).groupby('Date')['Order ID'].nunique().reset_index(name='Orders')
        fig.add_trace(go.Scatter(x=od2['Date'],y=od2['Orders'],
                                 name=f"Prev ({cmp_s.date()}–{cmp_e.date()})",
                                 line=dict(color=GRAY,width=1.5,dash='dot'),mode='lines'))
    fig.update_layout(xaxis=dict(tickformat="%b %d"),legend=dict(orientation='h',y=1.12,x=0))
    pc(fig,260)

    c1,c2=st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Orders by Day of Week</div>', unsafe_allow_html=True)
        o2=o_cur.copy(); o2['Weekday']=o2['Date'].dt.day_name()
        wd_order=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        wd=o2.groupby('Weekday')['Order ID'].nunique().reindex(wd_order).fillna(0).reset_index(name='Orders')
        fig=px.bar(wd,x='Weekday',y='Orders',color='Orders',
                   color_continuous_scale=[[0,'#1E3A5F'],[1,BLUE]],text_auto=True)
        fig.update_layout(coloraxis_showscale=False,showlegend=False,xaxis_tickangle=-30)
        pc(fig,240)
    with c2:
        st.markdown('<div class="section-header">Orders by Status</div>', unsafe_allow_html=True)
        sf=o_cur.groupby('Status')['Order ID'].nunique().reset_index(name='Orders')
        clr={s:(GREEN if s=='Completed' else RED) for s in sf['Status']}
        fig=px.pie(sf,values='Orders',names='Status',hole=0.58,color='Status',color_discrete_map=clr)
        fig.update_traces(textposition='outside',textinfo='percent+label',textfont_size=11)
        fig.update_layout(showlegend=False)
        pc(fig,240)

    st.markdown('<div class="section-header">Orders by Brand</div>', unsafe_allow_html=True)
    bt=o_cur.groupby('Brand').agg(
        Orders=('Order ID','nunique'),Revenue=('Sales','sum'),AOV=('Sales','mean'),
        Completed=('Status',lambda x:(x=='Completed').sum()),
        Cancelled=('Status',lambda x:(x=='Canceled').sum())
    ).reset_index().sort_values('Orders',ascending=False)
    bt['Completion%']=(bt['Completed']/bt['Orders']*100).round(1)
    if compare_on and not o_cmp.empty:
        bc2=o_cmp.groupby('Brand')['Order ID'].nunique().reset_index(name='Ord_cmp')
        bt=bt.merge(bc2,on='Brand',how='left').fillna(0)
        bt['chg']=bt.apply(lambda r:pct(r['Orders'],r['Ord_cmp']),axis=1)
    rows=""
    for _,r in bt.iterrows():
        chg_c=delta_badge(r.get('chg')) if compare_on else ""
        rows+=f"<tr><td><b>{r['Brand']}</b></td><td class='num'>{int(r['Orders']):,}</td><td class='num'>SAR {r['Revenue']:,.0f}</td><td class='num'>SAR {r['AOV']:,.2f}</td><td class='num'>{r['Completion%']:.1f}%</td>{'<td>'+chg_c+'</td>' if compare_on else ''}</tr>"
    cmp_th="<th>vs Prev</th>" if compare_on else ""
    st.markdown(f"<table class='tbl'><tr><th>Brand</th><th>Orders</th><th>Revenue</th><th>AOV</th><th>Completion %</th>{cmp_th}</tr>{rows}</table>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — REVENUE & SALES
# ─────────────────────────────────────────────────────────────────────────────
with t3:
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
    gross=cur['sales']; disc=cur['disc']; net=gross-disc
    cg=cmp_data['sales']; cd_=cmp_data['disc']; cn=cg-cd_
    k1,k2,k3,k4=st.columns(4)
    kpi_card(k1,"Gross Revenue",  f"SAR {gross:,.0f}", pct(gross,cg),              f"SAR {cg:,.0f}",            BLUE)
    kpi_card(k2,"Net Revenue",    f"SAR {net:,.0f}",   pct(net,cn),                f"SAR {cn:,.0f}",            GREEN)
    kpi_card(k3,"Total Discount", f"SAR {disc:,.0f}",  pct(disc,cd_),              f"SAR {cd_:,.0f}",           AMBER)
    kpi_card(k4,"Avg Order Value",f"SAR {cur['aov']:,.2f}",pct(cur['aov'],cmp_data['aov']),f"SAR {cmp_data['aov']:,.2f}",PURPLE)
    st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Daily Revenue & Discount</div>', unsafe_allow_html=True)
    rd=cd(o_cur).groupby('Date').agg(Revenue=('Sales','sum'),Discount=('Discount','sum')).reset_index()
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=rd['Date'],y=rd['Revenue'],name="Revenue",
                             line=dict(color=BLUE,width=2.5),fill='tozeroy',fillcolor='rgba(37,99,235,0.06)',mode='lines'))
    fig.add_trace(go.Scatter(x=rd['Date'],y=rd['Discount'],name="Discount",
                             line=dict(color=AMBER,width=1.8,dash='dot'),mode='lines'))
    fig.update_layout(xaxis=dict(tickformat="%b %d"),legend=dict(orientation='h',y=1.12,x=0))
    pc(fig,260)

    col1,col2=st.columns(2)
    with col1:
        st.markdown('<div class="section-header">Weekly Revenue</div>', unsafe_allow_html=True)
        wk=o_cur.groupby(['Year','Week Number'])['Sales'].sum().reset_index()
        wk['Wk']=wk['Year'].astype(str)+'-W'+wk['Week Number'].astype(str).str.zfill(2)
        wk=wk.sort_values(['Year','Week Number'])
        if compare_on and not o_cmp.empty:
            wk2=o_cmp.groupby(['Year','Week Number'])['Sales'].sum().reset_index()
            wk2['Wk']=wk2['Year'].astype(str)+'-W'+wk2['Week Number'].astype(str).str.zfill(2)
            wk['Type']='Current'; wk2['Type']='Previous'
            fig=px.bar(pd.concat([wk,wk2]),x='Wk',y='Sales',color='Type',barmode='group',
                       color_discrete_map={'Current':BLUE,'Previous':GRAY},text_auto='.2s')
        else:
            fig=px.bar(wk,x='Wk',y='Sales',color_discrete_sequence=[BLUE],text_auto='.2s')
            fig.update_traces(marker_color=BLUE)
        fig.update_layout(xaxis_tickangle=-40,showlegend=compare_on,
                          legend=dict(orientation='h',y=1.12,x=0))
        pc(fig,260)
    with col2:
        st.markdown('<div class="section-header">Monthly Revenue</div>', unsafe_allow_html=True)
        mn=o_cur.groupby(['Year','Month','Month Name'])['Sales'].sum().reset_index()
        mn=mn.sort_values(['Year','Month']); mn['Period']=mn['Month Name']+' '+mn['Year'].astype(str)
        if compare_on and not o_cmp.empty:
            mn2=o_cmp.groupby(['Year','Month','Month Name'])['Sales'].sum().reset_index()
            mn2=mn2.sort_values(['Year','Month']); mn2['Period']=mn2['Month Name']+' '+mn2['Year'].astype(str)
            mn['Type']='Current'; mn2['Type']='Previous'
            fig=px.bar(pd.concat([mn,mn2]),x='Period',y='Sales',color='Type',barmode='group',
                       color_discrete_map={'Current':BLUE,'Previous':GRAY},text_auto='.2s')
        else:
            fig=px.bar(mn,x='Period',y='Sales',color_discrete_sequence=[BLUE],text_auto='.2s')
            fig.update_traces(marker_color=BLUE)
        fig.update_layout(xaxis_tickangle=-20,showlegend=compare_on,
                          legend=dict(orientation='h',y=1.12,x=0))
        pc(fig,260)

    st.markdown('<div class="section-header">Revenue by Provider & Brand</div>', unsafe_allow_html=True)
    d1,d2=st.columns([1,1.8])
    with d1:
        pv=o_cur.groupby('Provider')['Sales'].sum().reset_index()
        fig=px.pie(pv,values='Sales',names='Provider',hole=0.52,color_discrete_sequence=PAL)
        fig.update_traces(textposition='outside',textinfo='percent+label',textfont_size=10)
        fig.update_layout(showlegend=False)
        pc(fig,280)
    with d2:
        bb=o_cur.groupby('Brand').agg(Revenue=('Sales','sum'),Orders=('Order ID','nunique'),
                                       AOV=('Sales','mean')).reset_index().sort_values('Revenue',ascending=False)
        if compare_on and not o_cmp.empty:
            bc2=o_cmp.groupby('Brand')['Sales'].sum().reset_index(name='Rev_cmp')
            bb=bb.merge(bc2,on='Brand',how='left').fillna(0)
            bb['chg']=bb.apply(lambda r:pct(r['Revenue'],r['Rev_cmp']),axis=1)
        rows=""
        for _,r in bb.iterrows():
            chg_c=delta_badge(r.get('chg')) if compare_on else ""
            rows+=f"<tr><td><b>{r['Brand']}</b></td><td class='num'>SAR {r['Revenue']:,.0f}</td><td class='num'>{int(r['Orders']):,}</td><td class='num'>SAR {r['AOV']:,.2f}</td>{'<td>'+chg_c+'</td>' if compare_on else ''}</tr>"
        cmp_th="<th>vs Prev</th>" if compare_on else ""
        st.markdown(f"<table class='tbl'><tr><th>Brand</th><th>Revenue</th><th>Orders</th><th>AOV</th>{cmp_th}</tr>{rows}</table>",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ITEMS
# ─────────────────────────────────────────────────────────────────────────────
with t4:
    if i_cur.empty:
        st.warning("No item data for this selection.")
    else:
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)
        top_item=i_cur.groupby('Items')['Quantity'].sum().idxmax()
        top_qty=int(i_cur.groupby('Items')['Quantity'].sum().max())
        cmp_top=int(i_cmp.groupby('Items')['Quantity'].sum().get(top_item,0)) if compare_on else 0
        tot_qty=int(i_cur['Quantity'].sum()); cmp_qty2=int(i_cmp['Quantity'].sum()) if compare_on else 0
        k1,k2,k3,k4=st.columns(4)
        kpi_card(k1,"Unique Items",     f"{i_cur['Items'].nunique():,}", None,                          "—",            BLUE)
        kpi_card(k2,"Total Units Sold", f"{tot_qty:,}",                  pct(tot_qty,cmp_qty2),          f"{cmp_qty2:,}",GREEN)
        kpi_card(k3,"Best Seller",      (top_item[:20]+"…") if len(top_item)>20 else top_item,None,"—",AMBER)
        kpi_card(k4,"Best Seller Units",f"{top_qty:,}",                  pct(top_qty,cmp_top) if compare_on else None,f"{cmp_top:,}",PURPLE)
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Top 15 Items by Quantity Sold</div>', unsafe_allow_html=True)
        t15=i_cur.groupby('Items')['Quantity'].sum().sort_values(ascending=False).head(15).reset_index()
        if compare_on and not i_cmp.empty:
            t15c=i_cmp.groupby('Items')['Quantity'].sum().reset_index(name='Qty_cmp')
            t15=t15.merge(t15c,on='Items',how='left').fillna(0)
            fig=go.Figure()
            fig.add_trace(go.Bar(x=t15['Items'],y=t15['Quantity'],name='Current',
                                 marker_color=BLUE,text=t15['Quantity'],textposition='outside'))
            fig.add_trace(go.Bar(x=t15['Items'],y=t15['Qty_cmp'],name='Previous',
                                 marker_color=GRAY,text=t15['Qty_cmp'],textposition='outside'))
            fig.update_layout(barmode='group',legend=dict(orientation='h',y=1.12,x=0),xaxis_tickangle=-35)
        else:
            fig=px.bar(t15,x='Items',y='Quantity',color_discrete_sequence=[BLUE],text_auto=True)
            fig.update_traces(marker_color=BLUE); fig.update_layout(xaxis_tickangle=-35,showlegend=False)
        pc(fig,320)

        c1,c2=st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Item Trend — Top 6</div>', unsafe_allow_html=True)
            top6=i_cur.groupby('Items')['Quantity'].sum().nlargest(6).index.tolist()
            it=cd(i_cur[i_cur['Items'].isin(top6)]).groupby(['Date','Items'])['Quantity'].sum().reset_index()
            if it['Date'].nunique()>=2:
                fig=px.line(it,x='Date',y='Quantity',color='Items',line_shape='spline',color_discrete_sequence=PAL)
                fig.update_layout(legend=dict(orientation='h',y=1.12,x=0),legend_title_text='',
                                  xaxis=dict(tickformat="%b %d"))
                pc(fig,280)
            else:
                st.info("Widen the date range for trends.")
        with c2:
            st.markdown('<div class="section-header">Top 10 Items by Provider</div>', unsafe_allow_html=True)
            top10i=i_cur.groupby('Items')['Quantity'].sum().nlargest(10).index
            ib=i_cur[i_cur['Items'].isin(top10i)].groupby(['Items','Provider'])['Quantity'].sum().reset_index()
            fig=px.bar(ib,x='Items',y='Quantity',color='Provider',barmode='stack',color_discrete_sequence=PAL)
            fig.update_layout(xaxis_tickangle=-35,legend_title_text='',legend=dict(orientation='h',y=1.12,x=0))
            pc(fig,280)

        st.markdown('<div class="section-header">Full Item Table (Top 30)</div>', unsafe_allow_html=True)
        full=i_cur.groupby('Items').agg(
            Qty=('Quantity','sum'), Orders=('Order ID','nunique'),
            Revenue=('Total Amount','sum') if 'Total Amount' in i_cur.columns else ('Quantity','sum')
        ).reset_index().sort_values('Qty',ascending=False).head(30).reset_index(drop=True)
        if compare_on and not i_cmp.empty:
            fc2=i_cmp.groupby('Items')['Quantity'].sum().reset_index(name='Qty_cmp')
            full=full.merge(fc2,on='Items',how='left').fillna(0)
            full['chg']=full.apply(lambda r:pct(r['Qty'],r['Qty_cmp']),axis=1)
        rows=""
        for idx,r in full.iterrows():
            chg_c=delta_badge(r.get('chg')) if compare_on else ""
            rows+=f"<tr><td style='color:#64748B;font-size:.7rem'>{idx+1}</td><td><b>{r['Items']}</b></td><td class='num'>{int(r['Qty']):,}</td><td class='num'>{int(r['Orders']):,}</td>{'<td>'+chg_c+'</td>' if compare_on else ''}</tr>"
        cmp_th="<th>vs Prev</th>" if compare_on else ""
        st.markdown(f"<table class='tbl'><tr><th>#</th><th>Item</th><th>Units Sold</th><th>Orders</th>{cmp_th}</tr>{rows}</table>",
                    unsafe_allow_html=True)
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)