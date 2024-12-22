import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable
import logging

# Load environment variables
load_dotenv()

# Configure Google Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Define the prompt for summary generation
prompt = """You are a YouTube video summarizer. You will take the transcript text
and summarize the entire video, providing the important points in a summary within 250 words.
Please summarize the following text: """

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Function to extract transcript details
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine transcript text
        transcript = " ".join([entry["text"] for entry in transcript_data])
        return transcript

    except TranscriptsDisabled:
        st.error("Transcripts are disabled for this video. Please try another video.")
        logging.error("Transcripts are disabled for video ID: %s", youtube_video_url.split("=")[1])
    except VideoUnavailable:
        st.error("The video is unavailable or does not exist. Please check the link.")
        logging.error("Video unavailable for URL: %s", youtube_video_url)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        logging.error("Unexpected error: %s", e)

    return None

# Function to generate summary using Gemini
def generate_gemini_content(transcript_text, prompt):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt + transcript_text)
        return response.text
    except Exception as e:
        st.error("An error occurred while generating the summary. Please try again.")
        logging.error("Error in Gemini content generation: %s", e)
        return None

# Streamlit App
st.title("YouTube Transcript to Detailed Notes Converter")
youtube_link = st.text_input("Enter YouTube Video Link:")

if youtube_link:
    try:
        video_id = youtube_link.split("=")[1]
        st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)
    except IndexError:
        st.error("Invalid YouTube link. Please provide a valid URL.")

if st.button("Get Detailed Notes"):
    transcript_text = extract_transcript_details(youtube_link)

    if transcript_text:
        summary = generate_gemini_content(transcript_text, prompt)
        if summary:
            st.markdown("## Detailed Notes:")
            st.write(summary)
