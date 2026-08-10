"""
Configuration & UI Theme Settings for Head Lettuce Research Application.
Defines design tokens, custom CSS for tablet touch optimization, and color palettes.
"""

import datetime

APP_TITLE = "Lettuce Phytochemical & LED Research Portal"
APP_SUBTITLE = "Influence of LED Supplemental Lighting & Soil Chemical Properties on Phytochemical Accumulation in Head Lettuce (Lactuca sativa L.)"
START_DATE = datetime.date(2026, 8, 4)

COLOR_PALETTE = {
    "Control_GM": "#2ecc71",   # Emerald Green
    "LED_GM": "#27ae60",       # Dark Emerald
    "Control_F": "#3498db",    # Blue
    "LED_F (1)": "#9b59b6",   # Purple
    "LED_F (2)": "#8e44ad"    # Dark Purple
}

CUSTOM_TABLET_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Pass-through invisible Streamlit header overlay so clicks hit tab text directly */
    header[data-testid="stHeader"] {
        background: transparent !important;
        pointer-events: none !important;
        z-index: 1 !important;
    }
    
    header[data-testid="stHeader"] button, 
    header[data-testid="stHeader"] a {
        pointer-events: auto !important;
    }

    /* Move main content and tab menu all the way to the top margin */
    .block-container, 
    [data-testid="stMainBlockContainer"],
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0px !important;
        position: relative !important;
        z-index: 10 !important;
    }

    .stTabs {
        margin-top: 0px !important;
        padding-top: 0px !important;
        position: relative !important;
        z-index: 20 !important;
    }
    
    /* Clean Tab Alignment & Perfect Click Target Positioning */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        border-bottom: 2px solid #e2e8f0 !important;
        padding-bottom: 0px !important;
        align-items: center !important;
        position: relative !important;
        z-index: 30 !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: auto !important;
        padding: 10px 16px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        border-radius: 6px 6px 0 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 !important;
        cursor: pointer !important;
        pointer-events: auto !important;
        position: relative !important;
        z-index: 40 !important;
    }
    
    .stTabs [data-baseweb="tab"] p, 
    .stTabs [data-baseweb="tab"] span {
        font-size: 15px !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
        margin: 0 !important;
        padding: 0 !important;
        pointer-events: none !important;
    }
    
    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] {
        bottom: 0px !important;
    }
    
    /* Touch-friendly Emerald Green buttons for sidebar and main page */
    .stButton > button, .stDownloadButton > button {
        min-height: 44px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        background-color: #1b5e20 !important;
        background: #1b5e20 !important;
        color: #ffffff !important;
        border: 1px solid #14532d !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        transition: all 0.2s ease !important;
        padding: 8px 16px !important;
    }
    
    .stButton > button:hover, .stDownloadButton > button:hover {
        background-color: #2e7d32 !important;
        background: #2e7d32 !important;
        color: #ffffff !important;
        border: 1px solid #1b5e20 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
    }

    .stButton > button *, .stDownloadButton > button * {
        color: #ffffff !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Fix Tooltip Icon (?) - Clean transparent hover icon */
    .stTooltipIcon, 
    [data-testid="stTooltipHoverTarget"],
    [data-testid="stHelpIcon"],
    div[data-testid="stTooltipHoverTarget"],
    div[data-testid="stTooltipHoverTarget"] *,
    button[data-testid="stHelpIcon"],
    button[data-testid="stHelpIcon"] * {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        color: #4b5563 !important;
        fill: #4b5563 !important;
    }
    
    .stTooltipIcon svg, [data-testid="stTooltipHoverTarget"] svg, [data-testid="stHelpIcon"] svg {
        fill: #4b5563 !important;
        color: #4b5563 !important;
        background: transparent !important;
        background-color: transparent !important;
    }

    /* Fix Tooltip Popup Box & Thai Font Vertical Squishing */
    div[data-baseweb="popover"],
    div[data-baseweb="tooltip"],
    div[role="tooltip"] {
        z-index: 999999 !important;
    }

    div[data-baseweb="popover"] > div,
    div[data-baseweb="tooltip"] > div,
    div[role="tooltip"] {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.3) !important;
        padding: 10px 14px !important;
        height: auto !important;
        min-height: max-content !important;
        max-width: 320px !important;
        white-space: normal !important;
        word-break: break-word !important;
        overflow: visible !important;
    }
    
    div[data-baseweb="popover"] *,
    div[data-baseweb="tooltip"] *,
    div[role="tooltip"] * {
        color: #f8fafc !important;
        background-color: transparent !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        line-height: 1.6 !important;
        height: auto !important;
        min-height: min-content !important;
        margin: 0 !important;
        padding: 0 !important;
        transform: none !important;
        letter-spacing: normal !important;
    }
    
    /* Tablet Data Editor Grid optimization */
    div[data-testid="stDataEditor"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #c8e6c9;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
</style>
"""
