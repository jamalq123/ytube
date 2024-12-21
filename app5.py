import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from googleapiclient.discovery import build
import spacy
from textblob import TextBlob

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# YouTube API key
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# NLP Model for Keyword Extraction
nlp = spacy.load("en_core_web_sm")

# Prompt for Google Gemini Pro
prompt = """You are a YouTube video summarizer. You will take the transcript text
and summarize the entire video, providing the important summary in points
within 250 words. Please provide the summary of the text given here: """

# Function to extract transcript from YouTube
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        transcript = " ".join([entry["text"] for entry in transcript_text])
        return transcript
    except NoTranscriptFound:
        try:
            # Try fetching auto-generated transcripts
            transcript_text = YouTubeTranscriptApi.get_transcript(video_id)
            transcript = " ".join([entry["text"] for entry in transcript_text])
            return transcript
        except Exception:
            st.warning("No transcript available in any language for this video.")
            return None
    except TranscriptsDisabled:
        st.warning("Subtitles are disabled for this video.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching the transcript: {e}")
        return None

# Function to generate summary using Google Gemini Pro
def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt + transcript_text)
    return response.text

# Function for Keyword Extraction
def extract_keywords(text, num_keywords=10):
    doc = nlp(text)
    keywords = [token.text for token in doc if token.is_alpha and not token.is_stop]
    return list(set(keywords))[:num_keywords]

# Function for Sentiment Analysis
def analyze_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # Range: [-1.0, 1.0]
    subjectivity = blob.sentiment.subjectivity  # Range: [0.0, 1.0]
    sentiment = "Positive" if polarity > 0 else "Negative" if polarity < 0 else "Neutral"
    return sentiment, polarity, subjectivity

# Function to fetch video details
def get_video_details(video_id):
    request = youtube.videos().list(part="snippet,statistics", id=video_id)
    response = request.execute()

    if not response["items"]:
        return None

    details = response["items"][0]
    stats = details["statistics"]
    snippet = details["snippet"]

    return {
        "title": snippet["title"],
        "channel_title": snippet["channelTitle"],
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "dislikes": int(stats.get("dislikeCount", 0)),  # May not always be available
        "comments": int(stats.get("commentCount", 0)),
        "channel_id": snippet["channelId"]
    }

# Function to fetch video comments and sentiment analysis
def get_video_comments_with_sentiments(video_id):
    sentiments = {"Positive": [], "Negative": [], "Neutral": []}

    request = youtube.commentThreads().list(part="snippet", videoId=video_id, maxResults=100)
    response = request.execute()

    for item in response["items"]:
        comment = item["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
        sentiment, _, _ = analyze_sentiment(comment)
        sentiments[sentiment].append(comment)

    return sentiments

# Streamlit UI
st.title("YouTube Video Analysis Tool")

youtube_link = st.text_input("Enter YouTube Video Link:")

if youtube_link:
    video_id = youtube_link.split("=")[1]
    st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)

if st.button("Analyze Video"):
    try:
        # Extract transcript
        transcript_text = extract_transcript_details(youtube_link)

        if not transcript_text:
            st.warning("Transcript-based analysis skipped due to unavailable subtitles.")
        else:
            # Generate summary
            summary = generate_gemini_content(transcript_text, prompt)

            # Extract keywords
            keywords = extract_keywords(transcript_text)

            st.markdown("## Summary:")
            st.write(summary)

            st.markdown("### Keywords:")
            st.write(", ".join(keywords))

        # Fetch video details
        video_details = get_video_details(video_id)

        # Fetch comments and analyze sentiment
        comments_by_sentiment = get_video_comments_with_sentiments(video_id)

        # Display results
        st.markdown("## Video Details:")
        st.write(f"**Title:** {video_details['title']}")
        st.write(f"**Channel:** {video_details['channel_title']}")
        st.write(f"**Views:** {video_details['views']}")
        st.write(f"**Likes:** {video_details['likes']}")
        st.write(f"**Dislikes:** {video_details['dislikes']}")
        st.write(f"**Comments:** {video_details['comments']}")

        st.markdown("### Comment Sentiment Analysis:")
        st.write(f"**Positive Comments:** {len(comments_by_sentiment['Positive'])}")
        st.write(f"**Negative Comments:** {len(comments_by_sentiment['Negative'])}")
        st.write(f"**Neutral Comments:** {len(comments_by_sentiment['Neutral'])}")

        st.markdown("### Negative Comments:")
        if comments_by_sentiment["Negative"]:
            for idx, comment in enumerate(comments_by_sentiment["Negative"], start=1):
                st.write(f"{idx}. {comment}")
        else:
            st.write("No negative comments found.")
    except Exception as e:
        st.error(f"An error occurred: {e}")
