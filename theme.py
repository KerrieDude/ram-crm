import base64
import os
import streamlit as st

RAM_PINK = "#e832c0"
RAM_DARK = "#1a1a1a"
RAM_GREY = "#e5e5e5"


def _b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def inject_css():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Bangers&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Segoe UI', Arial, sans-serif;
        }}

        h1, h2, h3, .brand-font {{
            font-family: 'Bangers', cursive !important;
            letter-spacing: 0.5px;
        }}

        #MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
        .block-container {{ padding-top: 0.5rem; max-width: 1200px; }}
        section[data-testid="stSidebar"] {{ display: none; }}

        /* Never let any one oversized element force the whole page to scroll sideways --
           this is what was showing up as "huge margins" (really: scrolled-past overflow) */
        html, body {{ max-width: 100vw; overflow-x: hidden; }}
        .main, .block-container {{ overflow-x: hidden; max-width: 100vw; }}
        * {{ word-wrap: break-word; overflow-wrap: break-word; }}

        .ram-topbar {{
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 10px 20px;
            background: {RAM_GREY};
            border-bottom: 1px solid #ddd;
            margin: 0 -1rem 1.2rem -1rem;
        }}
        .ram-topbar img {{ height: 48px; }}
        .ram-topbar .ram-title {{
            font-family: 'Bangers', cursive;
            font-size: 2rem;
            color: {RAM_DARK};
            letter-spacing: 0.5px;
            flex: 1;
        }}
        .ram-topbar .ram-user {{
            font-size: 0.85rem;
            color: #555;
            text-align: right;
        }}

        /* Nav tabs styled like the site's pink pill nav */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 6px;
            border-bottom: 2px solid {RAM_GREY};
        }}
        .stTabs [data-baseweb="tab"] {{
            font-family: 'Bangers', cursive;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
            color: {RAM_DARK};
            padding: 8px 18px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {RAM_PINK} !important;
            border-bottom: 3px solid {RAM_PINK} !important;
        }}
        .stTabs [data-baseweb="tab"]:hover {{ color: {RAM_PINK}; }}

        div.stButton > button, div.stFormSubmitButton > button {{
            background: {RAM_PINK};
            color: #fff;
            border: none;
            border-radius: 30px;
            font-weight: 700;
            padding: 6px 20px;
        }}
        div.stButton > button:hover, div.stFormSubmitButton > button:hover {{
            background: #c228a8;
            color: #fff;
        }}

        /* Tablet / phone responsiveness */
        .stTabs [data-baseweb="tab-list"] {{
            overflow-x: auto;
            flex-wrap: nowrap;
            -webkit-overflow-scrolling: touch;
        }}
        div.stButton > button, div.stFormSubmitButton > button {{
            min-height: 44px;
        }}
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input,
        div[data-baseweb="select"] {{
            min-height: 40px;
        }}

        /* Camera capture is phone/tablet only -- desktop just gets the uploader */
        @media (min-width: 1025px) {{
            div[class*="st-key-"][class*="_cam_btn"],
            div[class*="st-key-"][class*="_camera"] {{
                display: none !important;
            }}
        }}

        @media (max-width: 768px) {{
            .block-container {{ padding-left: 0.6rem; padding-right: 0.6rem; }}
            .ram-topbar {{ flex-wrap: wrap; padding: 8px 12px; margin: 0 -0.6rem 1rem -0.6rem; }}
            .ram-topbar img {{ height: 36px; }}
            .ram-topbar .ram-title {{ font-size: 1.3rem; }}
            .ram-topbar .ram-user {{ width: 100%; text-align: left; font-size: 0.75rem; }}
            .stTabs [data-baseweb="tab"] {{ font-size: 0.95rem; padding: 6px 12px; }}
        }}

        /* Top nav (pills) -- horizontally scrollable so it never pushes the page wide */
        div[data-testid="stPills"] {{
            overflow-x: auto;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch;
        }}
        div[data-testid="stPills"] * {{
            white-space: nowrap;
        }}

        /* Dashboard's left/right split stacks vertically on narrow screens */
        @media (max-width: 900px) {{
            .st-key-dash_layout > div[data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
            }}
            .st-key-dash_layout > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                width: 100% !important;
            }}
        }}

        /* Daily Run: compact, spreadsheet-like input grid on laptop/desktop */
        .st-key-daily_run_grid div[data-testid="stVerticalBlock"] {{
            gap: 0.35rem !important;
        }}
        .st-key-daily_run_grid div[data-testid="stHorizontalBlock"] {{
            gap: 0.5rem !important;
        }}
        .st-key-daily_run_grid div[data-testid="stTextInput"] input {{
            padding: 4px 8px !important;
            min-height: 32px !important;
        }}
        .st-key-daily_run_grid label {{
            font-size: 0.78rem !important;
            margin-bottom: 0 !important;
        }}

        /* On phone/tablet the same grid switches to a single, roomier input column */
        @media (max-width: 768px) {{
            .st-key-daily_run_grid div[data-testid="stHorizontalBlock"] {{
                flex-direction: column !important;
            }}
            .st-key-daily_run_grid div[data-testid="column"] {{
                width: 100% !important;
            }}
            .st-key-daily_run_grid div[data-testid="stTextInput"] input {{
                min-height: 40px !important;
                font-size: 1rem !important;
            }}
        }}

        .st-key-ticket_box {{
            border: 1px dashed {RAM_PINK};
            border-radius: 8px;
            padding: 0.8rem 1rem;
            background: #1a1a1a;
        }}

        /* Invoice / Billing sheet */
        .st-key-invoice_sheet {{
            border: 1px solid #444;
            border-radius: 10px;
            padding: 1.2rem;
            background: #141414;
        }}
        .inv-title {{
            font-family: 'Bangers', cursive;
            font-size: 2.5rem;
            color: {RAM_PINK};
        }}
        .inv-company {{
            text-align: right;
            color: {RAM_PINK};
            font-size: 0.85rem;
        }}

        /* Calendar day-picker grid: keep 7 columns tight enough to never overflow a phone */
        .st-key-cal_grid div[data-testid="stHorizontalBlock"] {{
            gap: 4px !important;
        }}
        .st-key-cal_grid div[data-testid="column"] {{
            min-width: 0 !important;
            width: auto !important;
        }}
        .st-key-cal_grid div.stButton > button {{
            padding: 2px 0 !important;
            min-height: 36px !important;
            font-size: 0.75rem !important;
            line-height: 1.1 !important;
            white-space: pre-line !important;
            border-radius: 8px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar(user):
    logo_path = "assets/ram_mascot.png"
    logo_html = ""
    if os.path.exists(logo_path):
        logo_html = f'<img src="data:image/png;base64,{_b64(logo_path)}" alt="RAM">'

    sign_out_label = f"Signed in as {user['display_name']} ({user['role']})"
    st.markdown(
        f"""
        <div class="ram-topbar">
            {logo_html}
            <div class="ram-title">Run Around Melissa &middot; CRM</div>
            <div class="ram-user">{sign_out_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
