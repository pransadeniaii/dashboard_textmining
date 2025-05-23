# -*- coding: utf-8 -*-
"""Dashboard Code

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1mhYyAU3Kw9wKr9lOShfy2GJN1PSO_ZnB

Internal dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import ast
import re

from sklearn.metrics.pairwise import cosine_similarity

# Loading the final data with embeddings
df = pd.read_pickle("activities_with_embeddings.pkl")

# -- Clean up age_group field
def simplify_age(age):
    if pd.isna(age):
        return "No specific category"
    match = re.search(r"\d+", str(age))
    return match.group() + "+" if match else "No specific category"

df["age_group"] = df["age_group"].apply(simplify_age)

# Get full chapter titles from first few lines in the chapter_summary field
def extract_chapter_title(summary, chapter_key):
    if not isinstance(summary, str):
        return "Untitled"

    if chapter_key == "Chapter 4":
        return "Gender and sexual equality"

    # Try: "CHAPTER 6 Sex"
    match = re.search(r"CHAPTER\s+\d+\s+(.+)", summary, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try: "6 Sex" (page heading without "CHAPTER")
    match = re.search(r"^\d+\s+([A-Za-z].+)$", summary, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Fallback: Use most likely first non-"Introduction" line
    for line in summary.splitlines():
        clean = line.strip()
        if clean and clean.lower() not in ["introduction", "chapter summary"]:
            return clean
    return "Untitled"

chapter_titles = {}
for chapter in df["chapter"].dropna().unique():
    chapter_summary = df[df["chapter"] == chapter]["chapter_summary"].dropna().values
    if chapter_summary.size > 0:
        extracted_title = extract_chapter_title(chapter_summary[0], chapter)
        if extracted_title:
            chapter_titles[chapter] = extracted_title  # ⬅️ this is the change
        else:
            chapter_titles[chapter] = "Untitled"
    else:
        chapter_titles[chapter] = "Untitled"



# -- Convert instruction strings that look like lists into bullet points
def format_instructions(instr):
    if isinstance(instr, str):
        try:
            parsed = ast.literal_eval(instr)
            if isinstance(parsed, list):
                return "\n".join([f"- {line}" for line in parsed])
        except:
            pass
    return instr

def clean_chapter_summary(text, chapter_title):
    if not isinstance(text, str):
        return ""

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Remove the word "equality" if it's the first word in Chapter 4
        if chapter_title == "Gender and sexual equality" and stripped.lower() == "equality":
            continue

        # Remove lines that match the chapter title exactly (start or end)
        if stripped == chapter_title:
            continue

        # Remove lines like "Sexual health 261" or "261 Sexual health"
        if chapter_title.lower() in stripped.lower() and re.search(r"\d", stripped):
            continue

        # Remove CHAPTER header
        if re.search(r"CHAPTER\s+\d+", stripped, flags=re.IGNORECASE):
            continue

        # Remove lines like "Chapter summary"
        if "Chapter summary" in stripped:
            continue

        # Remove single page numbers
        if re.match(r"^\d+$", stripped):
            continue

        cleaned_lines.append(stripped)

    cleaned_text = "\n\n".join([para for para in "\n".join(cleaned_lines).split("\n\n") if para.strip()])
    return cleaned_text.strip()


df["instructions"] = df["instructions"].apply(format_instructions)

# Convert string tags to list
df["pyari_curriculum_tags"] = df["pyari_curriculum_tags"].fillna("").apply(lambda x: [tag.strip() for tag in x.split(",") if tag])

# Sidebar filters
st.sidebar.title("🔍 Filter Activities")

age_options = sorted(df["age_group"].unique())
selected_age = st.sidebar.selectbox("Filter by Age Group", ["All"] + age_options)

all_tags = sorted({tag for sublist in df["pyari_curriculum_tags"] for tag in sublist})
selected_tags = st.sidebar.multiselect("Filter by Tags", all_tags)

search_query = st.sidebar.text_input("Search by keyword", "")

st.sidebar.markdown("### ℹ️ About This Project")

st.sidebar.markdown("""
This internal dashboard was developed as part of a **Text Mining** course at **Wesleyan University**. It is based on the book:

**_Great Relationships and Sex Education: 200+ Activities for Educators Working with Young People_**  
© 2020 Alice Hoyle and Ester McGeeney  
Published by Routledge, an imprint of Taylor & Francis Group.

All rights belong to the original authors and publishers. This dashboard is for internal academic use only and does not distribute or reproduce any part of the original material beyond its intended scope.

[Link to the book](https://www.routledge.com/9780815393634)
""")

# Apply filters
filtered_df = df.copy()

if selected_age != "All":
    filtered_df = filtered_df[filtered_df["age_group"] == selected_age]

if selected_tags:
    filtered_df = filtered_df[filtered_df["pyari_curriculum_tags"].apply(lambda tags: any(tag in tags for tag in selected_tags))]

if search_query:
    filtered_df = filtered_df[
        filtered_df["title"].str.contains(search_query, case=False, na=False) |
        filtered_df["purpose"].str.contains(search_query, case=False, na=False) |
        filtered_df["instructions"].str.contains(search_query, case=False, na=False)
    ]

# Show filtered activities if any filter is applied
if selected_age != "All" or selected_tags or search_query:
    st.title("🎯 Filtered Activities")

    if filtered_df.empty:
        st.markdown("No activities match your filters.")
    else:
        for _, row in filtered_df.iterrows():
            st.subheader(row["title"])
            st.markdown(f"**Purpose:** {row['purpose']}")
            st.markdown(f"**Age Group:** {row['age_group']}")
            st.markdown(f"**Tags:** {', '.join(row['pyari_curriculum_tags'])}")

            with st.expander("📖 Instructions"):
                st.markdown(row["instructions"])

            with st.expander("✨ See similar activities"):
                emb_matrix = np.stack(df["embedding"].values)
                target = np.array(row["embedding"]).reshape(1, -1)
                sims = cosine_similarity(target, emb_matrix)[0]
                top_indices = sims.argsort()[::-1][1:4]
                for i in top_indices:
                    sim_row = df.iloc[i]
                    st.markdown(f"**→ {sim_row['title']}** — _{sim_row['purpose']}_")
else:
    st.title("Pyari Curriculum Activities")

    # Get unique chapters
    chapters = list(chapter_titles.values())
    title_to_chapter = {v: k for k, v in chapter_titles.items()}
    selected_chapter_title = st.selectbox("📚 Choose a Chapter", sorted(chapters))
    selected_chapter = title_to_chapter[selected_chapter_title]

    # Filter for the selected chapter
    chapter_activities = df[df["chapter"] == selected_chapter]
    chapter_title = chapter_titles[selected_chapter]
    raw_summary = chapter_activities["chapter_summary"].dropna().unique()

    if raw_summary.any():
        cleaned_summary = clean_chapter_summary(raw_summary[0], chapter_title)

        st.markdown(f"## 📘 {chapter_title}")
        for para in cleaned_summary.split("\n\n"):
            st.markdown(para.strip())

    # Show sections in the selected chapter
    sections = chapter_activities["section"].dropna().unique()
    selected_section = st.selectbox("📂 Choose a Section", sorted(sections))

    # Filter to selected section
    section_activities = chapter_activities[chapter_activities["section"] == selected_section]

    # Display activities in selected section
    st.markdown("### 🎯 Activities")

    for idx, row in section_activities.iterrows():
        st.subheader(row["title"])
        st.markdown(f"**Purpose:** {row['purpose']}")
        st.markdown(f"**Age Group:** {row['age_group']}")
        st.markdown(f"**Tags:** {', '.join(row['pyari_curriculum_tags']) if isinstance(row['pyari_curriculum_tags'], list) else row['pyari_curriculum_tags']}")
        
        with st.expander("📖 Instructions"):
            st.markdown(row["instructions"])
        
        with st.expander("✨ See similar activities"):
            emb_matrix = np.stack(df["embedding"].values)
            target = np.array(row["embedding"]).reshape(1, -1)
            sims = cosine_similarity(target, emb_matrix)[0]
            top_indices = sims.argsort()[::-1][1:4]
            for i in top_indices:
                sim_row = df.iloc[i]
                st.markdown(f"**→ {sim_row['title']}** — _{sim_row['purpose']}_")

