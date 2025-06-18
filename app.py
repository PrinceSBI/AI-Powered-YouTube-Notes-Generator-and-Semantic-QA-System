# app.py

import streamlit as st  # Streamlit for building the web interface
from Files import youtube_database  # Our custom class with logic for transcripts, notes, and database
from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound  # Handle transcript-related errors

# Configure Streamlit page (title and layout)
st.set_page_config(page_title="📽️ YouTube Notes Generator", layout="centered")

# Instantiate the backend processing class
yt = youtube_database()

# --------------------------
# UI: Header
# --------------------------
st.title("📌 YouTube Notes Generator & QA")
st.markdown(
    "This app extracts transcript from a YouTube video, generates key notes using Gemini AI, "
    "and stores it in a searchable database. You can later query the database using questions."
)

# --------------------------
# Sidebar: Input for YouTube video
# --------------------------
st.sidebar.header("📽️ Process a New Video")

# Input: YouTube video ID (e.g., dQw4w9WgXcQ)
video_id = st.sidebar.text_input("Enter YouTube Video ID (e.g. `dQw4w9WgXcQ`)")

# Input: Custom name for saving the transcript and notes files
video_name = st.sidebar.text_input("Enter a name for this video", value="example_video")

# Button to start transcript + note generation
if st.sidebar.button("Generate Notes"):
    try:
        # STEP 1: Fetch transcript from YouTube
        with st.spinner("Fetching transcript..."):
            transcript = yt.video_to_transcript(video_id, video_name)
        st.success("Transcript fetched successfully!")

        # STEP 2: Generate notes using Gemini API
        with st.spinner("Generating notes with Gemini..."):
            notes = yt.response_generator(transcript, video_name)
        st.success("Notes generated!")

        # STEP 3: Save notes to vector DB (ChromaDB)
        with st.spinner("Saving to ChromaDB..."):
            yt.save_to_chromaDB(video_id, video_name)
        st.success("Saved to ChromaDB.")

        # Show the generated notes in the main UI
        st.subheader("Generated Notes:")
        st.text_area("Notes", notes, height=300)

    # Handle cases where transcripts are unavailable (e.g., disabled or auto-generated only)
    except (TranscriptsDisabled, NoTranscriptFound):
        st.error("Transcript not available for this video.")

    # Catch-all for unexpected issues
    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")

# --------------------------
# Sidebar: Query the notes database
# --------------------------
st.sidebar.markdown("---")  # Visual separator
st.sidebar.header("🔍 Search")

# Input: Question for querying notes (e.g., What is React?)
query = st.sidebar.text_input("Ask a question (e.g. 'What is React?')")

# Button to run the search
if st.sidebar.button("Search Notes"):
    if not query.strip():
        # User didn't enter a valid question
        st.warning("Please enter a valid question.")
    else:
        try:
            # Perform search on stored notes using ChromaDB and Gemini
            with st.spinner("Searching..."):
                result = yt.search(query)

            # Display result
            st.success("Answer generated!")
            st.subheader("Answer")
            st.write(result["response"])

            # Display related videos that the answer came from
            st.markdown("**Related Videos:**")
            for url in result["links"]:
                st.markdown(f"- [Watch Video]({url})")

        # Catch search-related errors
        except Exception as e:
            st.error(f"Search failed: {str(e)}")
