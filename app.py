import streamlit as st
import pandas as pd
from serpapi import GoogleSearch
from openai import OpenAI
import time
import os


# -------- CONFIG --------
st.set_page_config(page_title="Artemis AI - Lead Intelligence", layout="wide")

# Use secrets (for deployment)
SERP_API_KEY = st.secrets["SERP_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

client = OpenAI(api_key=OPENAI_API_KEY)


# -------- STYLING --------
st.markdown("""
<style>
h1 {
    text-align: center;
    font-size: 3rem;
}
.subtext {
    text-align: center;
    color: #9ca3af;
    margin-bottom: 2rem;
}
</style>
""", unsafe_allow_html=True)


# -------- HEADER --------
st.markdown("<h1>🚀 Artemis AI</h1>", unsafe_allow_html=True)
st.markdown(
    "<div class='subtext'>AI-powered lead intelligence platform to discover, evaluate, and prioritise high-value prospects</div>",
    unsafe_allow_html=True
)


# -------- SIDEBAR --------
with st.sidebar:
    st.header("⚙️ Controls")

    num_companies = st.slider("Companies", 1, 15, 5)
    num_people = st.slider("People per company", 1, 5, 3)

    st.markdown("---")
    st.markdown("### Filter")
    filter_score = st.selectbox("Lead Score", ["All", "🔥 High", "⚡ Medium", "🟢 Low"])

    st.markdown("---")
    st.markdown("### About")
    st.write("Artemis AI helps identify decision-makers and prioritise leads using AI insights.")


# -------- FUNCTIONS --------
@st.cache_data
def get_companies(api_key, query):
    params = {
        "q": f"site:ycombinator.com/companies {query}",
        "api_key": api_key,
        "num": 20
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    companies = []
    seen = set()

    for r in results.get("organic_results", []):
        title = r.get("title", "")
        link = r.get("link", "")

        if link in seen:
            continue
        seen.add(link)

        if "industry" in link or "overview" in link:
            continue

        name = title.split(":")[0].strip()

        if name:
            companies.append({
                "Company Name": name,
                "Website": link
            })

    return companies[:num_companies]


@st.cache_data
def get_people(company, api_key):
    params = {
        "q": f"{company} founder CTO LinkedIn",
        "api_key": api_key,
        "num": 20
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    people = []
    seen = set()

    for r in results.get("organic_results", []):
        title = r.get("title", "")
        link = r.get("link", "")

        if "linkedin.com/in/" not in link:
            continue

        if link in seen:
            continue
        seen.add(link)

        parts = title.split(" - ")
        name = parts[0].strip()
        role = parts[1].strip() if len(parts) > 1 else ""

        if not any(x in role.lower() for x in ["founder", "ceo", "cto"]):
            continue

        role = role.split("|")[0].split("@")[0].strip()

        people.append({
            "Person": name,
            "Role": role,
            "LinkedIn": link
        })

    return people[:num_people]


def analyze(company):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"What does {company} do in one line?"}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return f"{company} is an AI-related company"


def score_lead(role, insight):
    role = role.lower()
    insight = insight.lower()

    score = 0

    if "ceo" in role or "founder" in role:
        score += 3
    elif "cto" in role:
        score += 2
    else:
        score += 1

    if "ai" in insight or "platform" in insight:
        score += 2
    elif "tool" in insight or "software" in insight:
        score += 1

    if score >= 4:
        return "🔥 High"
    elif score >= 3:
        return "⚡ Medium"
    else:
        return "🟢 Low"


# -------- INPUT --------
query = st.text_input("🔍 Enter industry (e.g., AI, fintech, SaaS)")


# -------- MAIN --------
if st.button("✨ Generate Leads"):
    if query:

        data = []

        with st.spinner("🔎 Finding leads..."):
            companies = get_companies(SERP_API_KEY, query)

            for c in companies:
                name = c["Company Name"]
                website = c["Website"]

                st.write(f"Processing **{name}**...")

                people = get_people(name, SERP_API_KEY)
                insight = analyze(name)

                time.sleep(1)

                for p in people:
                    score = score_lead(p["Role"], insight)

                    data.append({
                        "Company": name,
                        "Website": website,
                        "Person": p["Person"],
                        "Role": p["Role"],
                        "LinkedIn": p["LinkedIn"],
                        "Insight": insight,
                        "Score": score
                    })

        df = pd.DataFrame(data).drop_duplicates()

        # -------- CLEAN NAMES --------
        df = df.rename(columns={
            "Person": "Name",
            "LinkedIn": "Profile",
            "Insight": "Company Insight"
        })

        # -------- SORTING --------
        score_order = {"🔥 High": 3, "⚡ Medium": 2, "🟢 Low": 1}
        df["ScoreValue"] = df["Score"].map(score_order)
        df = df.sort_values(by="ScoreValue", ascending=False).drop(columns=["ScoreValue"])

        # -------- FILTER --------
        if filter_score != "All":
            df = df[df["Score"] == filter_score]

        # -------- METRICS --------
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        col1.metric("Companies", df["Company"].nunique())
        col2.metric("Total Leads", len(df))
        col3.metric("Avg/Company", round(len(df)/max(df["Company"].nunique(), 1), 1))

        st.markdown("---")

        # -------- TOP LEADS --------
        st.subheader("🔥 Top Leads")
        st.dataframe(df[df["Score"] == "🔥 High"], use_container_width=True)

        # -------- ALL RESULTS --------
        st.subheader("📊 All Results")

        df["Profile"] = df["Profile"].apply(lambda x: f"[Profile]({x})")

        st.dataframe(df, use_container_width=True)

        st.success("✅ Leads generated successfully!")

        st.download_button(
            "⬇ Download Leads",
            df.to_csv(index=False),
            "artemis_leads.csv",
            mime="text/csv"
        )

    else:
        st.warning("Please enter an industry.")


# -------- FOOTER --------
st.markdown("---")
st.markdown("Built by Sanjay Sriram • Artemis AI")