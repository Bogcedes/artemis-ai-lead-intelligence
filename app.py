import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
from openai import OpenAI
import time

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Artemis AI", page_icon="🚀", layout="wide")

SERP_API_KEY = st.secrets["SERP_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)

# ---------------- HEADER ----------------
st.markdown("""
    <h1 style='text-align: center;'>🚀 Artemis AI</h1>
    <p style='text-align: center; color: gray; font-size:16px;'>
    AI-powered lead intelligence platform to discover, evaluate, and prioritise high-value prospects
    </p>
""", unsafe_allow_html=True)

st.markdown("---")

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("⚙️ Controls")

    num_companies = st.slider("Companies", 1, 10, 5)
    people_per_company = st.slider("People per company", 1, 5, 3)

    st.markdown("---")

    st.subheader("ℹ️ About Artemis AI")
    st.markdown("""
    Artemis AI is a lightweight lead intelligence engine that:
    
    - 🔍 Discovers startups via YC + Google
    - 👤 Identifies decision-makers
    - 🧠 Generates AI-powered insights
    - 📊 Helps prioritise high-value leads
    
    Built for modern outbound & research workflows.
    """)

# ---------------- INPUT SECTION ----------------
st.subheader("🔍 Target Configuration")

col1, col2 = st.columns(2)

# Industry
with col1:
    industry_options = [
        "AI", "Fintech", "SaaS", "Cybersecurity",
        "DevTools", "Data Analytics", "Other"
    ]

    selected_industry = st.selectbox("Select Industry", industry_options)

    if selected_industry == "Other":
        industry = st.text_input("Custom Industry")
    else:
        industry = selected_industry

# Region
with col2:
    region_options = [
        "Global", "United States", "India",
        "Europe", "United Kingdom", "Asia"
    ]

    region = st.selectbox("🌍 Target Region", region_options)

st.markdown("")

# ---------------- FUNCTIONS ----------------

def get_companies(industry, region, limit):

    if region == "Global":
        query = f"site:ycombinator.com/companies {industry}"
    else:
        query = f"site:ycombinator.com/companies {industry} {region}"

    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "num": limit * 4
    }

    results = GoogleSearch(params).get_dict()

    companies = []
    seen = set()

    for r in results.get("organic_results", []):
        link = r.get("link", "")
        title = r.get("title", "")

        if (
            "/companies/" in link
            and "industry" not in link
            and "location" not in link
            and link.count("/") <= 5
        ):
            name = title.split(":")[0].strip()

            if name and name not in seen:
                seen.add(name)
                companies.append({
                    "Company": name,
                    "Website": link
                })

        if len(companies) >= limit:
            break

    return companies


def get_people(company):
    query = f"{company} founder CTO CEO LinkedIn"

    params = {
        "q": query,
        "api_key": SERP_API_KEY
    }

    results = GoogleSearch(params).get_dict()

    people = []

    for r in results.get("organic_results", []):
        link = r.get("link", "")
        title = r.get("title", "")

        if "linkedin.com/in/" in link:
            parts = title.split("-")

            if len(parts) >= 2:
                name = parts[0].strip()
                role = parts[-1].strip()

                if len(role) < 60:
                    people.append({
                        "Person": name,
                        "Role": role,
                        "LinkedIn": link
                    })

    return people


def analyze_company(company):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"Explain what {company} does in one short professional sentence."
                }
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return f"{company} operates in {industry}"


# ---------------- MAIN ----------------
if st.button("✨ Generate Leads"):

    if not industry:
        st.warning("Please enter/select an industry")
        st.stop()

    progress = st.progress(0)
    status = st.empty()

    companies = get_companies(industry, region, num_companies)

    all_data = []

    for i, company in enumerate(companies):

        status.info(f"🔍 Analyzing {company['Company']}...")

        people = get_people(company["Company"])
        insight = analyze_company(company["Company"])
        time.sleep(1)

        for person in people[:people_per_company]:
            all_data.append({
                "Company": company["Company"],
                "Website": company["Website"],
                "Person": person["Person"],
                "Role": person["Role"],
                "LinkedIn": person["LinkedIn"],
                "Insight": insight
            })

        progress.progress((i + 1) / len(companies))

    status.success("✅ Leads generated successfully!")
    progress.empty()

    df = pd.DataFrame(all_data)

    if not df.empty:

        df = df.drop_duplicates(subset=["Company", "Person"])
        df.index = df.index + 1

        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Companies", df["Company"].nunique())
        col2.metric("Total Leads", len(df))
        col3.metric("Avg/Company", round(len(df) / df["Company"].nunique(), 1))

        st.markdown("## 🔥 Top Leads")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False)

        st.download_button(
            "⬇️ Download Leads",
            csv,
            "artemis_leads.csv",
            "text/csv"
        )

    else:
        st.error("No leads found. Try another query.")


# ---------------- FOOTER ----------------
st.markdown("---")

st.markdown("""
<div style='text-align: center; color: gray; font-size: 13px;'>
    Built with ❤️ by Sanjay • Artemis AI © 2026<br>
    <span style='font-size:12px;'>Lead intelligence for the next generation of builders</span>
</div>
""", unsafe_allow_html=True)
