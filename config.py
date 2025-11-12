import streamlit as st

# List of colleges with icons
COLLEGES = [
    {"name": "Mukesh Patel School of Technology Management & Engineering", "icon": "🖥️"},
    {"name": "School of Business Management", "icon": "💼"},
    {"name": "Pravin Dalal School of Entrepreneurship & Family Business Management", "icon": "🚀"},
    {"name": "Anil Surendra Modi School of Commerce", "icon": "📊"},
    {"name": "School of Commerce", "icon": "💰"},
    {"name": "Kirit P. Mehta School of Law", "icon": "⚖️"},
    {"name": "School of Law", "icon": "📜"},
    {"name": "Shobhaben Pratapbhai Patel School of Pharmacy & Technology Management", "icon": "💊"},
    {"name": "School of Pharmacy & Technology Management", "icon": "🧪"},
    {"name": "Sunandan Divatia School of Science", "icon": "🔬"},
    {"name": "School of Science", "icon": "🧬"},
    {"name": "Sarla Anil Modi School of Economics", "icon": "📈"},
    {"name": "Balwant Sheth School of Architecture", "icon": "🏛️"},
    {"name": "School of Design", "icon": "🎨"},
    {"name": "Jyoti Dalal School of Liberal Arts", "icon": "📚"},
    {"name": "School of Performing Arts", "icon": "🎭"},
    {"name": "School of Hospitality Management", "icon": "🏨"},
    {"name": "School of Mathematics, Applied Statistics & Analytics", "icon": "🔢"},
    {"name": "School of Branding and Advertising", "icon": "📢"},
    {"name": "School of Agricultural Sciences & Technology", "icon": "🌾"},
    {"name": "Centre of Distance and Online Education", "icon": "💻"},
    {"name": "School of Aviation", "icon": "✈️"}
]

# Branch full forms mapping
BRANCH_FULL_FORM = {
    "B TECH": "BACHELOR OF TECHNOLOGY",
    "B TECH INTG": "BACHELOR OF TECHNOLOGY SIX YEAR INTEGRATED PROGRAM",
    "M TECH": "MASTER OF TECHNOLOGY",
    "MBA TECH": "MASTER OF BUSINESS ADMINISTRATION IN TECHNOLOGY MANAGEMENT",
    "MCA": "MASTER OF COMPUTER APPLICATIONS",
    "DIPLOMA": "DIPLOMA IN ENGINEERING"
}

# Logo path
LOGO_PATH = "logo.png"


def setup_page_config():
    """Setup Streamlit page configuration"""
    st.set_page_config(
        page_title="Exam Timetable Generator",
        page_icon="📅",
        layout="wide",
        initial_sidebar_state="expanded"
    )


def apply_custom_css():
    """Apply custom CSS styling"""
    st.markdown("""
    <style>
        /* Base styles */
        .main-header {
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }

        .main-header h1 {
            color: white;
            text-align: center;
            margin: 0;
            font-size: 2.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .main-header p {
            color: #FFF;
            text-align: center;
            margin: 0.5rem 0 0 0;
            font-size: 1.2rem;
            opacity: 0.9;
        }

        .stats-section {
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
        }

        .metric-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
            border-radius: 8px;
            color: white;
            text-align: center;
            margin: 0.5rem;
            transition: transform 0.2s;
        }

        .metric-card:hover {
            transform: scale(1.05);
        }

        .metric-card h3 {
            margin: 0;
            font-size: 1.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .metric-card p {
            margin: 0.3rem 0 0 0;
            font-size: 1rem;
            opacity: 0.9;
        }

        .stButton>button {
            transition: all 0.3s ease;
            border-radius: 5px;
            border: 1px solid transparent;
        }

        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            border: 1px solid #951C1C;
            background-color: #C73E1D;
            color: white;
        }

        .stDownloadButton>button {
            transition: all 0.3s ease;
            border-radius: 5px;
            border: 1px solid transparent;
        }

        .stDownloadButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            border: 1px solid #951C1C;
            background-color: #C73E1D;
            color: white;
        }

        /* Light mode styles */
        @media (prefers-color-scheme: light) {
            .main-header {
                background: linear-gradient(90deg, #951C1C, #C73E1D);
            }

            .upload-section {
                background: #f8f9fa;
                padding: 2rem;
                border-radius: 10px;
                border: 2px dashed #951C1C;
                margin: 1rem 0;
            }

            .results-section {
                background: #ffffff;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin: 1rem 0;
            }

            .stats-section {
                background: #f8f9fa;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            .status-success {
                background: #d4edda;
                color: #155724;
                padding: 1rem;
                border-radius: 5px;
                border-left: 4px solid #28a745;
            }

            .status-error {
                background: #f8d7da;
                color: #721c24;
                padding: 1rem;
                border-radius: 5px;
                border-left: 4px solid #dc3545;
            }

            .status-info {
                background: #d1ecf1;
                color: #0c5460;
                padding: 1rem;
                border-radius: 5px;
                border-left: 4px solid #17a2b8;
            }

            .feature-card {
                background: white;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin: 1rem 0;
                border-left: 4px solid #951C1C;
            }

            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }

            .footer {
                text-align: center;
                color: #666;
                padding: 2rem;
            }
        }

        /* Dark mode styles */
        @media (prefers-color-scheme: dark) {
            .main-header {
                background: linear-gradient(90deg, #701515, #A23217);
            }

            .upload-section {
                background: #333;
                padding: 2rem;
                border-radius: 10px;
                border: 2px dashed #A23217;
                margin: 1rem 0;
            }

            .results-section {
                background: #222;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                margin: 1rem 0;
            }

            .stats-section {
                background: #333;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            }

            .status-success {
                background: #2d4b2d;
                color: #e6f4ea;
                padding: 1rem;
                border-radius: 5px;
                border-left: 4px solid #4caf50;
            }

            .status-error {
                background: #4b2d2d;
                color: #f8d7da;
                padding: 1rem;
                border-radius: 5px;
                border-left: 4px solid #f44336;
            }

            .status-info {
                background: #2d4b4b;
                color: #d1ecf1;
                padding: 1rem;
                border-radius: 5px;
                border-left: 4px solid #00bcd4;
            }

            .feature-card {
                background: #333;
                padding: 1.5rem;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                margin: 1rem 0;
                border-left: 4px solid #A23217;
            }

            .metric-card {
                background: linear-gradient(135deg, #4a5db0 0%, #5a3e8a 100%);
            }

            .footer {
                text-align: center;
                color: #ccc;
                padding: 2rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)
