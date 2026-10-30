"""Estilo compatible con los temas claro y oscuro de Streamlit."""
CSS = """
<style>
.block-container {max-width:1200px;padding-top:2.5rem;padding-bottom:2.2rem;}
[data-testid="stSidebar"] {border-right:1px solid #8495a522;}
[data-testid="stSidebar"] .block-container {padding-top:1.8rem;}
.brand {display:grid;grid-template-columns:44px 1fr;align-items:center;gap:6px 12px;margin:4px 0 24px;}
.brand-mark {background:#15354c;border:1px solid #25879a;color:#fff;border-radius:10px;padding:8px;display:flex;align-items:center;justify-content:center;}
.brand-name {font-size:23px;font-weight:700;letter-spacing:.02em;line-height:1.15;}
.brand-sub {grid-column:1 / -1;font-size:12px;opacity:.7;line-height:1.5;margin-top:4px;}
.page-label {color:#288b9c;font-size:12px;font-weight:700;letter-spacing:.13em;text-transform:uppercase;margin-bottom:8px;}
h1 {font-size:2rem!important;letter-spacing:-.025em;line-height:1.2!important;}
h2 {font-size:1.4rem!important;letter-spacing:-.015em;}
h3 {font-size:1.13rem!important;}
.subtitle {opacity:.68;margin-top:-8px;margin-bottom:22px;line-height:1.6;}
.status-strip {display:flex;flex-wrap:wrap;gap:10px;margin:0 0 26px;padding:14px 18px;border:1px solid #8193a333;border-radius:10px;font-size:13px;}
.status-strip span {padding-right:12px;border-right:1px solid #8193a344;}
.status-strip span:last-child {border:0;}
.guide-card {border:1px solid #8193a333;border-radius:12px;padding:19px 21px;height:100%;margin-bottom:12px;}
.guide-title {font-size:15px;font-weight:650;margin:0 0 6px;}
.guide-copy {font-size:14px;opacity:.7;margin:0;line-height:1.6;}
.st-key-navigation [role="radiogroup"] {gap:5px;}
.st-key-navigation label {border:1px solid transparent;border-radius:8px;padding:10px 8px;width:100%;}
.st-key-navigation label:has(input:checked) {background:#21889b1c;border-color:#21889b50;}
.st-key-navigation label p {font-size:14px;font-weight:500;}
[data-testid="stMetric"] {border:1px solid #8193a32b;border-radius:10px;padding:13px 16px;}
[data-testid="stMetricValue"] {font-size:1.6rem;}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
.stButton button, .stDownloadButton button {min-height:2.6rem;border-radius:8px;}
[data-testid="stDataFrame"] {border-radius:8px;}
.stCaption {line-height:1.55;}
@media(max-width:700px) {
 .block-container {padding-top:1.3rem;padding-left:1rem;padding-right:1rem;}
 h1 {font-size:1.65rem!important;}
 .status-strip {gap:7px;padding:10px 12px;font-size:12px;}
}
</style>
"""
