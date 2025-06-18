# Updated Files.py

import os
import logging
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()   # Used to get in the .env file to access the environment variable

# Logging setup
if not os.path.exists("logs"):
    os.makedirs("logs")
logging.basicConfig(filename="logs/app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class youtube_database:
    def __init__(self):

        # Load Gemini API key from .env file
        self.GEMINI_API_KEY = os.getenv('GIMINI_API_KEY')
        if not self.GEMINI_API_KEY:
            raise ValueError("Missing GIMINI_API_KEY in environment variables.")
        genai.configure(api_key=self.GEMINI_API_KEY)

        # Instantiate Gemini model
        # Model choices: https://ai.google.dev/gemini-api/docs/models/gemini
        self.genai_model = genai.GenerativeModel('models/gemini-1.5-flash')
        # Select an embedding function. Convert Texts to numbers
        # Embedding Function choices:https://docs.trychroma.com/guides/embeddings#custom-embedding-functions
        self.gemini_ef  = embedding_functions.GoogleGenerativeAiEmbeddingFunction(api_key=self.GEMINI_API_KEY)

        # Load the vector database, if it exists, otherwise create new on first run
        self.chroma_client = chromadb.PersistentClient(path="my_youtube_vectordb")
        # Load collection, if it exists, otherwise create new on first run. Specify the model that we want to use to do the embedding.
        self.chroma_collection = self.chroma_client.get_or_create_collection(name='yt_notes', embedding_function=self.gemini_ef)

        # Adjust prompt as needed (To generate transcript)
        self.prompt = "Extract the key ideas from this transcript in bullet points:\n\n"

    def video_to_transcript(self, link, name):
        try:
            file_path = f'./results/{name}_transcript.txt'
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read()

            transcript = YouTubeTranscriptApi.get_transcript(link, languages=['en', 'en-US', 'en-GB'])
            # transcript = TextFormatter().format_transcript(transcript)
            text = "\n".join([i['text'] for i in transcript])

            os.makedirs('./results/', exist_ok=True)
            with open(file_path, "w") as f:
                f.write(text)

            return text
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            logging.error(f"No transcript available for {link}: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"Error fetching transcript for {link}: {str(e)}")
            raise

    def response_generator(self, transcript, name):
        try:
            file_path = f'./results/{name}_notes.txt'
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read()

            # https://ai.google.dev/api/generate-content
            response = self.genai_model.generate_content(self.prompt + transcript, stream=False)

            with open(file_path, "w") as f:
                f.write(response.text)

            return response.text
        except Exception as e:
            logging.error(f"Gemini failed for {name}: {str(e)}")
            raise

    def save_to_chromaDB(self, link, name):
        try:
            with open(f'./results/{name}_notes.txt', 'r') as f:
                notes = f.read()

            # Insert, if record doesn't exist, otherwise update existing record
            # https://docs.trychroma.com/reference/py-collection#upsert
            self.chroma_collection.upsert(
                documents=[notes],
                ids=[link],
                metadatas=[{"url": f"https://youtu.be/{link}"}]
            )

            # # Validation
            # result = self.chroma_collection.get(yt_video_id, include=['documents', 'metadatas'])
            # result
        except Exception as e:
            logging.error(f"Error saving to ChromaDB for {link}: {str(e)}")
            raise

    def search(self, query_text, n_results=5):
        try:
            # https://docs.trychroma.com/reference/py-collection#query
            results = self.chroma_collection.query(
                query_texts=[query_text],
                n_results=n_results,
                include=['documents', 'distances', 'metadatas'],
            )

            for i in range(len(results['ids'][0])):
                id = results["ids"][0][i]
                document = results['documents'][0][i]

                print("************************************************************************")
                print(f"{i+1}.  https://youtu.be/{id}")
                print("************************************************************************")
                # print(document)

            response_prompt = (
                "Answer the following QUESTION using DOCUMENT as context.\n"
                f"QUESTION: {query_text}\n"
                f"DOCUMENT: {results['documents'][0][0]}"
            )
            response = self.genai_model.generate_content(response_prompt, stream=False)

            return {
                "response": response.text,
                "links": [f"https://youtu.be/{id}" for id in results['ids'][0]]
            }
        except Exception as e:
            logging.error(f"Search failed for query '{query_text}': {str(e)}")
            raise
