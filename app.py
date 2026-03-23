"""TaxGuru v10"""
import streamlit as st
import sys,os,copy,random
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tax_engine import TaxpayerProfile,compare_regimes,format_currency,format_lakhs
from knowledge_base import TAX_KNOWLEDGE_BASE
from gemini_integration import call_gemini,analyze_document,build_rag_query,anonymize_text,extract_financial_only
from vector_db import TaxVectorDB
st.set_page_config(page_title="TaxGuru",page_icon="🏛️",layout="wide",initial_sidebar_state="collapsed")
LOGO=""
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_app_b64.txt')
if os.path.exists(_p):
    with open(_p) as f:LOGO=f.read().strip()
if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag

# ══════ NAVIGATION FIX: set the radio widget key directly ══════
def nav(p):
    st.session_state.pg=p
    st.session_state.nav_radio=p  # THIS is what the radio reads

if 'pg' not in st.session_state:st.session_state.pg='Home'

st.markdown("""<style>
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,
.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,
iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],
button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}
footer:after{content:'';visibility:hidden;display:block;}.stApp>header{display:none!important;}
.stApp,[data-testid="stAppViewContainer"]{background:#0B0F19!important;color:#F1F5F9;}
[data-testid="stVerticalBlock"]{gap:0.3rem!important;}
h1,h2,h3,h4{color:#F1F5F9!important;}p,li,span,.stMarkdown{color:#E2E8F0;}
.stApp{margin-top:0;}.block-container{padding:0.3rem 1.2rem 0.5rem!important;max-width:100%!important;}
[data-testid="stAppViewContainer"]>div:first-child{padding-top:0.2rem!important;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{background:#1E293B;border:1px solid #475569;border-radius:6px;padding:0.35rem 0.8rem;font-size:0.95rem;font-weight:600;color:#E2E8F0;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#334155;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){background:#D4A843!important;color:#000!important;border-color:#D4A843!important;font-weight:700;}
.cd{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin:0.3rem 0;font-size:1rem;color:#E2E8F0;}
.cd.green{border-left:3px solid #10B981;}.cd.amber{border-left:3px solid #F59E0B;}.cd.red{border-left:3px solid #EF4444;}.cd.blue{border-left:3px solid #3B82F6;}
.tg{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0;}
.tt{background:#1A1F2E;border:2px solid #D4A843;border-radius:10px;padding:0.9rem;}
.tt h4{color:#D4A843!important;margin:0 0 0.4rem;font-size:1.15rem;}
.tt ul{list-style:none;padding:0;margin:0;}.tt li{padding:0.15rem 0;font-size:1rem;color:#F1F5F9;line-height:1.5;}.tt li::before{content:'✓ ';color:#10B981;font-weight:700;}
.su{background:#1C1917;border:2px solid #D4A843;border-radius:10px;padding:0.7rem 1rem;margin:0.6rem 0 0.8rem;text-align:center;}
.su b{font-size:1.2rem;color:#FDE68A;}.su span{color:#E2E8F0;font-size:1rem;}
.fb{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin-bottom:0.3rem;}
.fb h4{color:#D4A843;margin:0 0 0.2rem;font-size:1.05rem;}.fb p{color:#CBD5E1;font-size:0.92rem;margin:0;line-height:1.4;}
.ch{background:#1E293B;border:1px solid #475569;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}
.ch .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}
@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}
.ch .nm{font-weight:700;font-size:1rem;color:#F1F5F9;}.ch .rl{font-size:0.85rem;color:#CBD5E1;}
.cd2{font-size:0.85rem;color:#CBD5E1;font-style:italic;margin-top:0.3rem;}
.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.9rem;color:#93C5FD;margin-bottom:0.5rem;}
[data-testid="stSelectbox"]>div>div{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stNumberInput"] input{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stFileUploader"]{background:#111827;border:1px solid #374151;border-radius:8px;padding:0.5rem;}
.stTextInput input{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stExpander"]{background:#111827;border:1px solid #374151;border-radius:8px;}
[data-testid="stExpander"] summary{color:#F1F5F9!important;font-size:1rem;}
[data-testid="stMultiSelect"]>div>div{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stMetric"]{background:#111827;border:1px solid #374151;border-radius:8px;padding:0.5rem;}
[data-testid="stMetricValue"]{color:#D4A843!important;font-size:1.3rem!important;}
[data-testid="stMetricLabel"]{color:#CBD5E1!important;}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:#D4A843!important;color:#000!important;border:none!important;font-weight:900!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#F1F5F9!important;border:1px solid #475569!important;font-weight:700!important;font-size:0.95rem!important;-webkit-text-fill-color:#F1F5F9!important;}
[data-testid="stChatInput"]{background:#FFF!important;border:2px solid #475569;border-radius:8px;min-height:50px;}
[data-testid="stChatInput"] textarea{background:#FFF!important;color:#000!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
[data-testid="stChatInput"] button{background:#D4A843!important;color:#000!important;}
[data-testid="stToggle"] label span{color:#F1F5F9!important;font-size:1rem!important;}
@media(max-width:900px){.tg{grid-template-columns:1fr;}}
</style>""",unsafe_allow_html=True)

# Session — single profile only
for k,v in {'profile':TaxpayerProfile(),'pc':False,'ch':[]}.items():
    if k not in st.session_state:st.session_state[k]=v
if 'vdb' not in st.session_state:
    st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profile
def IC():return st.session_state.pc

# Short chat system prompt override
SHORT_PROMPT="""You are {agent_name}, a personal Indian income tax advisor on TaxGuru for FY 2025-26.
Rules: Be CONCISE — max 3-4 sentences per answer. No introduction line. No disclaimer. No "consult a CA" line.
Cite the section number. If asked for detail, then expand. Respond in the requested language.
Knowledge: IT Act 2025 effective Apr 2026. 8 HRA metro cities. CARF for crypto. Budget 2026 no rate changes."""

TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Law Updates","About"]
sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",
    index=TABS.index(st.session_state.pg) if st.session_state.pg in TABS else 0,key="nav_radio")
st.session_state.pg=sel

# Chat with logo in top-right
def chat_with_logo(k=""):
    if LOGO:
        st.markdown(f'<div style="text-align:center;padding:0"><img src="data:image/png;base64,{LOGO}" style="height:80px;filter:drop-shadow(0 0 10px rgba(212,168,67,0.3))"></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A}</span><br><span class="rl">Your Tax Agent</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=420)
    with bx:
        if not st.session_state.ch:
            st.markdown(f"👋 **I'm {A}.** Ask me any tax question.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A}...",key=f"c{k}"):
        cl,_=anonymize_text(pr);st.session_state.ch.append({'role':'user','content':pr})
        if not K:rsp="⚠️ API key not set."
        else:
            pf=extract_financial_only(vars(P())) if IC() else {};rg=build_rag_query(cl,pf)
            rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K,
                agent_name=A,system_prompt=SHORT_PROMPT)
        st.session_state.ch.append({'role':'assistant','content':rsp});st.rerun()
    st.markdown(f'<div class="cd2">💡 {A} is grounded in the Income Tax Act, latest circulars and case law.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat_with_logo(k)

# ══════ HOME ══════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        st.markdown('<h1 style="font-size:1.7rem!important;margin:0 0 0.2rem!important">Stop overpaying your taxes.</h1><p style="font-size:1.05rem;color:#E2E8F0;margin:0 0 0.5rem">AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p>',unsafe_allow_html=True)
        st.markdown('<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter your details manually.</span></div>',unsafe_allow_html=True)
        bc1,bc2=st.columns(2)
        with bc1:st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary",on_click=nav,args=("Tax Profile",))
        with bc2:st.button("✏️ Enter Manually",use_container_width=True,on_click=nav,args=("Tax Profile",))
        fc1,fc2,fc3=st.columns(3)
        with fc1:
            st.markdown('<div class="fb"><h4>⚖️ Tax Calculator</h4><p>Old vs New regime — see exact savings in rupees.</p></div>',unsafe_allow_html=True)
            st.button("Open Tax Calculator →",use_container_width=True,key="h1",on_click=nav,args=("Tax Calculator",))
        with fc2:
            st.markdown('<div class="fb"><h4>🔀 What-If Scenarios</h4><p>Raise, home loan, ELSS, share sale — see tax impact.</p></div>',unsafe_allow_html=True)
            st.button("Open Scenarios →",use_container_width=True,key="h4",on_click=nav,args=("What-If Scenarios",))
        with fc3:
            st.markdown('<div class="fb"><h4>💡 Savings Finder</h4><p>What to invest, how much, by when. With tax impact.</p></div>',unsafe_allow_html=True)
            st.button("Open Savings Finder →",use_container_width=True,key="h3",on_click=nav,args=("Savings Finder",))
        st.markdown(f'<div class="tg"><div class="tt"><h4>🛡️ Always Accurate</h4><ul><li>Tax numbers from a precise calculation engine — not AI guesses</li><li>Every answer cites the actual Income Tax Act section</li><li>When unsure, {A} says "check with a CA" — never makes things up</li><li>Updated real-time with Budget 2026 changes, circulars, court judgements</li></ul></div><div class="tt"><h4>🔒 Your Data Stays Private</h4><ul><li>We never see your PAN, Aadhaar, address, DOB, phone, or email</li><li>Bank accounts, PF/UAN, employer name — all auto-deleted</li><li>Only salary/deduction numbers used — in your browser session only</li><li>Close the browser → everything gone. Nothing saved. Ever.</li></ul></div></div>',unsafe_allow_html=True)
    with c2:chat_with_logo("home")

# ══════ TAX PROFILE ══════
elif sel=="Tax Profile":
    def tp():
        st.markdown("## Tax Profile")
        st.markdown("#### 📄 Upload Document")
        st.markdown('<div class="pv">🔒 Only financial numbers extracted. Personal details auto-ignored.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip, Form 16, or tax sheet",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner(f"🔍 {A} is reading..."):doc=analyze_document(up.read(),K,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual';mul=1 if ann else 12
                st.success(f"✅ {'Annual' if ann else 'Monthly'} data:")
                for ky,v in doc.items():
                    if ky not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{ky.replace('_',' ').title()}:** ₹{v:,.0f}"+("" if ann else f" → ₹{v*mul:,.0f}/yr"))
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in("NOT_FOUND",None):return d
                    try:return float(v)*mul
                    except:return d
                def _use():
                    p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary');p.basic_salary=gv('basic_salary',p.gross_salary*0.4)
                    p.hra_received=gv('hra');p.tds_deducted=gv('tds_deducted')
                    p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'))
                    st.session_state.pc=True;nav("Tax Calculator")
                st.button("✅ Use This Data",type="primary",use_container_width=True,on_click=_use)
            else:st.error("Couldn't read. Try manual.")
        elif up:st.error("API key not configured.")
        st.markdown("---")
        st.markdown("#### ✏️ Manual Entry")
        c1,c2=st.columns(2)
        with c1:
            types=st.multiselect("I earn income from...",["Salary","Business","Professional services","Trading (stocks, F&O, crypto)","Investments","Freelancing","Other"],default=["Salary"])
            age=st.number_input("Age",18,100,30)
        with c2:
            st.markdown("**Residency**")
            citizenship=st.selectbox("Citizenship",["Indian citizen","Person of Indian origin","Foreign citizen"])
            days_india=st.number_input("Days in India this FY",0,366,365)
            days_4yr=st.number_input("Days in India, last 4 years",0,1461,1400)
            income_15l=st.checkbox("Indian income > ₹15 lakh")
            if days_india>=182:res_s="resident";st.markdown("✅ **Resident**")
            elif citizenship!="Foreign citizen":
                if income_15l and days_india>=120 and days_4yr>=365:res_s="rnor";st.markdown("⚠️ **RNOR**")
                elif days_india>=60 and days_4yr>=365 and not income_15l:res_s="resident";st.markdown("✅ **Resident**")
                else:res_s="nri";st.markdown("🌍 **NRI**")
            else:
                res_s="nri" if not(days_india>=60 and days_4yr>=365) else "resident"
                st.markdown("✅ **Resident**" if res_s=="resident" else "🌍 **NRI**")
            met=st.selectbox("Metro? (50% HRA)",["Yes — Del/Mum/Kol/Che/Hyd/Pune/Ahd/Blr","No"])
        t="salaried"
        if "Business" in types:t="business"
        if "Professional services" in types:t="professional"
        if "Trading (stocks, F&O, crypto)" in types:t="trader"
        gs=bs=hra=rent=enps=biz=trd=ii=ri=di=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0;fe=False
        st.markdown("**💰 Income**")
        if "Salary" in types:
            c1,c2,c3=st.columns(3)
            with c1:gs=st.number_input("Gross Salary ₹/yr",0,value=0,step=50000,format="%d")
            with c2:bs=st.number_input("Basic ₹/yr",0,value=0,step=25000,format="%d")
            with c3:hra=st.number_input("HRA ₹/yr",0,value=0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:rent=st.number_input("Rent ₹/yr",0,value=0,step=10000,format="%d")
            with c2:enps=st.number_input("Employer NPS ₹/yr",0,value=0,step=5000,format="%d")
        if any(x in types for x in ["Business","Professional services","Freelancing"]):
            biz=st.number_input("Business/Professional Income ₹",0,value=0,step=100000,format="%d")
        if "Trading (stocks, F&O, crypto)" in types:
            trd=st.number_input("Trading Profit/(Loss) ₹",value=0,step=50000,format="%d")
        with st.expander("📈 Investments, capital gains, ESOPs"):
            c1,c2,c3=st.columns(3)
            with c1:ii=st.number_input("Interest",0,value=0,step=5000,format="%d")
            with c2:ri=st.number_input("Rental",0,value=0,step=10000,format="%d")
            with c3:di=st.number_input("Dividend",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1:stcg=st.number_input("STCG",0,value=0,step=10000,format="%d")
            with c2:ltcg=st.number_input("LTCG",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP perquisite",0,value=0,step=50000,format="%d");fe=st.checkbox("Foreign ESOPs")
        with st.expander("🏦 Deductions (Old Regime)"):
            c1,c2,c3=st.columns(3)
            with c1:s80c=st.number_input("80C",0,150000,0,step=10000,format="%d")
            with c2:s80d=st.number_input("80D",0,50000,0,step=5000,format="%d")
            with c3:s80n=st.number_input("NPS",0,50000,0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:s80e=st.number_input("Edu Loan",0,value=0,step=10000,format="%d")
            with c2:s24b=st.number_input("Home Loan",0,200000,0,step=10000,format="%d")
        with st.expander("💳 TDS / Advance Tax"):
            c1,c2=st.columns(2)
            with c1:tds=st.number_input("TDS",0,value=0,step=10000,format="%d")
            with c2:adv=st.number_input("Advance Tax",0,value=0,step=10000,format="%d")
        def _save():
            p=P();p.taxpayer_type=t;p.age=age;p.residency=res_s;p.metro_city="Yes" in met
            p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent
            p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd
            p.interest_income=ii;p.rental_income=ri;p.dividend_income=di;p.stcg_equity=stcg;p.ltcg_equity=ltcg
            p.esop_perquisite=esop;p.foreign_esop=fe;p.section_80c=s80c;p.section_80d_self=s80d
            p.section_80d_parents=0;p.section_80ccd_1b=s80n;p.section_80e=s80e;p.section_24b=s24b
            p.tds_deducted=tds;p.advance_tax_paid=adv;st.session_state.pc=True;nav("Tax Calculator")
        st.button("✅ Save & See My Tax",type="primary",use_container_width=True,on_click=_save)
    with_chat(tp,"tp")

# ══════ TAX CALCULATOR ══════
elif sel=="Tax Calculator":
    def calc():
        st.markdown("## Tax Calculator")
        if not IC():
            st.warning("Set up your tax profile first.")
            st.button("→ Set Up Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        show_old=st.toggle("Show Old Regime details",value=True)
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"### {'✅ ' if rc=='new' else ''}New Regime")
            st.markdown(f"Taxable: **{format_currency(n['taxable_income'])}**")
            st.markdown(f"Slab tax: {format_currency(n['slab_tax'])}")
            if n['rebate_87a']>0:st.markdown(f"87A rebate: -{format_currency(n['rebate_87a'])}")
            if n['surcharge']>0:st.markdown(f"Surcharge: {format_currency(n['surcharge'])}")
            st.markdown(f"Cess: {format_currency(n['cess'])}")
            st.markdown(f"### Total: {format_currency(n['total_tax'])} ({n['effective_rate']}%)")
            np2=n['net_payable']
            if np2<0:st.markdown(f"**💰 Refund: {format_currency(abs(np2))}**")
            elif np2>0:st.markdown(f"Net payable: {format_currency(np2)}")
        with c2:
            if show_old:
                st.markdown(f"### {'✅ ' if rc=='old' else ''}Old Regime")
                st.markdown(f"Taxable: **{format_currency(o['taxable_income'])}**")
                if o.get('hra_exemption',0)>0:st.caption(f"HRA: {format_currency(o['hra_exemption'])}")
                if o['total_deductions']>0:st.caption(f"Deductions: {format_currency(o['total_deductions'])}")
                st.markdown(f"Slab tax: {format_currency(o['slab_tax'])}")
                if o['rebate_87a']>0:st.markdown(f"87A rebate: -{format_currency(o['rebate_87a'])}")
                if o['surcharge']>0:st.markdown(f"Surcharge: {format_currency(o['surcharge'])}")
                st.markdown(f"Cess: {format_currency(o['cess'])}")
                st.markdown(f"### Total: {format_currency(o['total_tax'])} ({o['effective_rate']}%)")
            else:st.info("Toggle above to compare")
    with_chat(calc,"calc")

# ══════ SAVINGS FINDER ══════
elif sel=="Savings Finder":
    def sf():
        st.markdown("## Savings Finder")
        if not IC():
            st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);rc=r['recommended'];ct=r[rc+'_regime']['total_tax']
        regime=st.toggle("Analyze for Old Regime",value=(rc=='old'))
        rk='old' if regime else 'new';ct=r[rk+'_regime']['total_tax']
        recs=[]
        if regime and p.section_80c<150000:
            g=150000-p.section_80c;p2=copy.deepcopy(p);p2.section_80c=150000;r2=compare_regimes(p2)
            sv=ct-r2['old_regime']['total_tax']
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more (80C)',f'Save **{format_currency(max(sv,0))}**','ELSS/PPF/FD','best ELSS tax saving funds India 2025'))
        if p.section_80ccd_2==0:recs.append(('red','80CCD(2)','Employer NPS','Save ₹15K-50K+','Both regimes',None))
        if p.esop_perquisite>0:recs.append(('amber','17(2)(vi)',f'ESOP: ₹{p.esop_perquisite:,.0f}','Taxed at slab rate','Time exercise',None))
        if p.foreign_esop:recs.append(('red','Sched FA','Foreign ESOP disclosure','₹10L penalty risk','File Form 67',None))
        if p.trading_income!=0:recs.append(('red','43(5)','Trading → ITR-3','Report losses for carry-forward','Engage CA',None))
        if regime and p.section_80d_self==0:
            p2=copy.deepcopy(p);p2.section_80d_self=25000;r2=compare_regimes(p2)
            sv=ct-r2['old_regime']['total_tax']
            recs.append(('amber','80D','Health insurance',f'Save **{format_currency(max(sv,0))}**','₹25K self + ₹50K parents','best health insurance India tax saving 2025'))
        if regime and p.section_24b==0:recs.append(('amber','24(b)','Home loan interest','Save up to ₹62,400','Max ₹2L deduction','best home loan rates India 2025'))
        if not recs:st.success("🎉 Well optimized!")
        for col,sec,t,impact,detail,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> ({sec}) — {impact}<br><em>{detail}</em></div>',unsafe_allow_html=True)
            if q:
                if st.button(f"🔍 Explore options",key=f"s_{sec}"):
                    if K:
                        with st.spinner(f"{A} is searching..."):
                            rsp=call_gemini(prompt=f"List top 3 {q}. For each: name, return%, lock-in. No disclaimers. Max 5 lines total.",
                                context="",language="en",api_key=K,agent_name=A,system_prompt=SHORT_PROMPT)
                        st.markdown(rsp)
    with_chat(sf,"sf")

# ══════ WHAT-IF SCENARIOS — 15+ options ══════
elif sel=="What-If Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        if not IC():
            st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();cur=compare_regimes(p)
        regime=st.toggle("Compare using Old Regime",value=(cur['recommended']=='old'))
        rk='old' if regime else 'new';ct=cur[rk+'_regime']['total_tax']
        st.caption(f"Base: **{rk.title()} Regime** — current tax: {format_currency(ct)}")
        scenarios=[
            "Switch tax regime","Salary raise (10-50%)","Invest in 80C (ELSS/PPF/FD)",
            "Start employer NPS","Buy health insurance (80D)","Take a home loan",
            "Pay rent (claim HRA)","Sell equity shares (LTCG)","Sell equity shares (STCG)",
            "Sell property","Receive ESOPs","Take education loan",
            "Start a side business","Earn rental income","Receive a large bonus",
            "Make a donation (80G)","Invest in NPS self (80CCD1B)",
            "Receive foreign income (NRI)","Earn interest on FDs"]
        s=st.selectbox("What do you want to explore?",scenarios)
        def calc_tax(p2):
            r2=compare_regimes(p2);return r2[rk+'_regime']['total_tax']
        if s=="Switch tax regime":
            alt='old' if rk=='new' else 'new';at=cur[alt+'_regime']['total_tax']
            st.metric(f"{alt.title()} Regime",format_currency(at),delta=f"{format_currency(at-ct)}",delta_color="inverse")
        elif s=="Salary raise (10-50%)":
            pct=st.slider("Raise %",5,100,20,5);p2=copy.deepcopy(p)
            p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100));p2.hra_received=int(p.hra_received*(1+pct/100))
            c1,c2=st.columns(2)
            with c1:st.metric("New salary",format_lakhs(p2.gross_salary))
            with c2:st.metric("Tax change",format_currency(calc_tax(p2)-ct))
        elif s=="Invest in 80C (ELSS/PPF/FD)":
            ex=st.slider("80C investment ₹",0,150000,min(150000-p.section_80c,150000),10000)
            p2=copy.deepcopy(p);p2.section_80c=min(p.section_80c+ex,150000)
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
        elif s=="Start employer NPS":
            nps=st.slider("Employer NPS ₹/yr",0,int(max(p.basic_salary*0.14,100000)),50000,5000)
            p2=copy.deepcopy(p);p2.section_80ccd_2=nps
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            st.caption("80CCD(2) works in BOTH regimes.")
        elif s=="Buy health insurance (80D)":
            d=st.slider("Premium ₹/yr (self+family)",0,50000,25000,5000)
            p2=copy.deepcopy(p);p2.section_80d_self=d
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
        elif s=="Take a home loan":
            li=st.number_input("Loan interest ₹/yr",0,value=200000,step=25000)
            lp=st.number_input("Principal ₹/yr",0,value=100000,step=25000)
            p2=copy.deepcopy(p);p2.section_24b=min(li,200000);p2.section_80c=min(p.section_80c+lp,150000)
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
        elif s=="Pay rent (claim HRA)":
            rn=st.number_input("Annual rent ₹",0,value=240000,step=12000)
            p2=copy.deepcopy(p);p2.rent_paid_annual=rn
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
        elif s=="Sell equity shares (LTCG)":
            lg=st.number_input("LTCG ₹",0,value=200000,step=25000)
            p2=copy.deepcopy(p);p2.ltcg_equity+=lg
            st.markdown(f"Exempt: ₹{min(lg,125000):,}")
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
        elif s=="Sell equity shares (STCG)":
            sg=st.number_input("STCG ₹",0,value=100000,step=25000)
            p2=copy.deepcopy(p);p2.stcg_equity+=sg
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
        elif s=="Sell property":
            st.markdown("Property sale → LTCG at 12.5% (no indexation from Jul 2024). Exempt under 54/54F if reinvested.")
            gain=st.number_input("Capital gain ₹",0,value=500000,step=50000)
            p2=copy.deepcopy(p);p2.ltcg_other+=gain
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
        elif s=="Receive ESOPs":
            ep=st.number_input("ESOP perquisite value ₹",0,value=500000,step=50000)
            p2=copy.deepcopy(p);p2.esop_perquisite+=ep
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
        elif s=="Take education loan":
            ei=st.number_input("Loan interest ₹/yr",0,value=100000,step=10000)
            p2=copy.deepcopy(p);p2.section_80e=ei
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            st.caption("80E: full interest, no limit, 8 years. Old Regime.")
        elif s=="Start a side business":
            bi=st.number_input("Expected business income ₹",0,value=300000,step=50000)
            p2=copy.deepcopy(p);p2.business_income+=bi
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            st.caption("If turnover < ₹2Cr, can use presumptive taxation (44AD). Need ITR-3 or ITR-4.")
        elif s=="Earn rental income":
            ri2=st.number_input("Annual rent received ₹",0,value=240000,step=12000)
            p2=copy.deepcopy(p);p2.rental_income+=ri2
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            st.caption("30% standard deduction on net rental income. Municipal taxes deductible.")
        elif s=="Receive a large bonus":
            bn=st.number_input("Bonus amount ₹",0,value=500000,step=50000)
            p2=copy.deepcopy(p);p2.gross_salary+=bn
            st.metric("Tax on bonus",format_currency(calc_tax(p2)-ct))
        elif s=="Make a donation (80G)":
            dn=st.number_input("Donation ₹",0,value=50000,step=5000)
            p2=copy.deepcopy(p);p2.section_80g=dn
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            st.caption("80G: 50% or 100% deduction depending on donee. Old Regime only.")
        elif s=="Invest in NPS self (80CCD1B)":
            np2=st.slider("NPS self ₹",0,50000,50000,5000)
            p2=copy.deepcopy(p);p2.section_80ccd_1b=np2
            st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            st.caption("₹50K over 80C limit. Old Regime only.")
        elif s=="Receive foreign income (NRI)":
            st.markdown("NRIs taxed only on Indian income. RNOR taxed on Indian income. Residents taxed on global income.")
            fi=st.number_input("Foreign income ₹",0,value=1000000,step=100000)
            st.info(f"If Resident: this ₹{fi:,} is fully taxable. If NRI/RNOR: not taxable in India.")
        elif s=="Earn interest on FDs":
            fd=st.number_input("FD interest ₹/yr",0,value=100000,step=10000)
            p2=copy.deepcopy(p);p2.interest_income+=fd
            st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            st.caption("TDS at 10% if >₹40K (₹50K seniors). Consider tax-saving 5yr FD under 80C.")
    with_chat(sc,"sc")

# ══════ LAW UPDATES ══════
elif sel=="Law Updates":
    def lu():
        st.markdown("## Latest Tax Law Updates")
        for dt,t,d,col in [
            ('Mar 20, 2026','🆕 IT Rules 2026 Notified','HRA→8 metros. Form 124. Sections 819→536. CARF crypto.','blue'),
            ('Mar 5, 2026','🆕 CARF: Crypto Reporting','All exchanges must report from Jan 2026.','blue'),
            ('Mar 2026','Significant Transaction Emails','CBDT sending AIS alerts. Verify on e-filing portal.','blue'),
            ('Feb 2026','Budget 2026 — No slab changes','"Tax Year" replaces "PY/AY" from Apr 2026.','blue'),
            ('Oct 2025','ITR Deadline Extended','Audit cases: Oct 31 → Dec 10, 2025.','amber'),
            ('Jul 2024','Capital Gains Changed','STCG 15→20%. LTCG 10→12.5%. No indexation.','amber'),
            ('Feb 2025','₹12.75L Tax-Free (Salaried)','New regime: ₹4L exempt, 87A ₹60K, SD ₹75K.','green'),
            ('Apr 2024','Angel Tax Abolished','Sec 56(2)(viib) removed for all investors.','green')]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### ⚖️ Key Case Law")
        for t,d in [
            ("CIT vs Gopal Purohit (Bombay HC)","Can have separate investment + trading portfolios."),
            ("Unnikrishnan vs ITO (Mumbai ITAT)","ESOPs granted as resident, exercised as NRI → taxable in India."),
            ("HRA to Parents (ITAT)","Rent to parents OK for HRA. Need agreement + bank transfer."),
            ("CBDT Circular 6/2016","Classify shares as investment or trading — must be consistent.")]:
            st.markdown(f'<div class="cd blue"><b>⚖️ {t}</b><br>{d}</div>',unsafe_allow_html=True)
    with_chat(lu,"lu")

# ══════ ABOUT ══════
elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru
### Our Mission
India has 9 Cr+ ITR filers — yet most overpay. ₹3.9L Cr in refunds (FY25) = massive over-deduction. TaxGuru makes the right choice easy.

### How It Works
**🧮 Precise Calculations** — Numbers from a deterministic engine, not AI. Always exact.

**🤖 {A}** — An intelligent agent with 60 tax law entries, CBDT circulars, case law, Budget amendments. Cites sections. Searches the web for latest developments.

**📄 Document Intelligence** — Upload payslip/Form 16 → AI reads financial numbers only.

**🔒 Privacy** — No PAN/Aadhaar/DOB/address/phone/email/bank/PF/employer. Session-only. Close browser = gone.

### Accuracy
60 provisions including CBDT Notification 22/2026. Auto-updates weekly via GitHub Actions.

### For Everyone
Salaried • Business • Professionals • Traders • Investors • Seniors • NRIs

*Informational guidance. Not professional tax advice.*""")
    with_chat(ab,"ab")
