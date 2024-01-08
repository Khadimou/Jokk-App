# myapp/utils.py
import os

from bs4 import BeautifulSoup
import requests
import pdfkit

from openai import OpenAI
import logging

from smart_mentor.models import OpenAIAssistant

# Set up a logger
logger = logging.getLogger(__name__)
client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))

tools_list = [{
    "type": "function",
    "function": {

        "name": "upload_to_openai",
        "description": "Assistant capable of answering questions based on provided data.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The filepath"
                }
            },
            "required": ["symbol"]
        }
    }
}]

def scrape_website(url):
    """Scrape text from a website URL."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    return soup.get_text()

def text_to_pdf(text, filename):
    path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
    config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)
    pdfkit.from_string(text, filename, configuration=config)
    return filename

def upload_to_openai(filepath):
    """Upload a file to OpenAI and return its file ID."""
    with open(filepath, "rb") as file:
        response = client.files.create(file=file, purpose="assistants")
    return response.id

def create_assistant(user,file_id, name, description="Assistant capable of answering questions based on provided data.", model="gpt-4-1106-preview"):

    assistant = client.beta.assistants.create(
        name=name,
        description=description,
        model=model,
        tools=[{"type": "retrieval"}],
        file_ids=[file_id]
    )
    # Save to database
    OpenAIAssistant.objects.create(
        user=user,
        assistant_id=assistant.id,
        file_id=file_id,
        name=name,
        description=description,
        model=model
    )
    return assistant.id

def generate_questions(fields, degree):
    try:
        # Logique de génération des questions...
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": f"Give me 10 questions about {fields} to assess the skills of someone in this {fields} for {degree} level"},
            ]
        )
        # Extraire le texte de la première réponse
        response_text = response.choices[0].message.content

        # Séparer les questions en utilisant le saut de ligne comme séparateur
        questions = [question.strip() for question in response_text.split('\n') if question.strip()]

        # Retourner les 10 premières questions (ou moins si moins de 10 sont générées)
        return questions[:10]

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

    return questions


def evaluate( provided_answers):
    evaluation_results = {}

    for question, provided_answer in provided_answers.items():
        try:
            # Formulate the API request
            system_message = (
                f"Please evaluate the following answer to determine if it is correct. "
                f"Question: '{question}'. Provided answer: '{provided_answer}'. "
                f"Respond with 'correct' if the answer is accurate and complete, or 'incorrect' if it is not."
            )

            response = client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=[{"role": "system", "content": system_message}]
            )


            # Extract the evaluation result from the response
            evaluation_text = response.choices[0].message.content.strip()

            # Determine if the response indicates a correct answer
            if "correct" in evaluation_text.lower():
                evaluation_results[question] = "correct"
            else:
                evaluation_results[question] = "incorrect"

        except Exception as e:
            print(f"An error occurred while evaluating the answer for '{question}': {e}")
            evaluation_results[question] = "error"

    return evaluation_results


def create_chat_thread(file_id):
    """Create a chat thread and return its ID."""
    response = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "",
                "file_ids": [file_id]
            }
        ]
    )
    print("Thread creation response:", response)
    return response.id

def process_message_with_citations(thread_id,message_id):
    # Retrieve the message object
    message = client.beta.threads.messages.retrieve(
        thread_id=thread_id,
        message_id=message_id
    )

    # Extract the message content
    message_content = message.content[0].text
    print(message_content)
    annotations = message_content.annotations
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(annotation.text, f' [{index}]')

        # Gather citations based on annotation attributes
        if (file_citation := getattr(annotation, 'file_citation', None)):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            cited_file = client.files.retrieve(file_path.file_id)
            citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
            # Note: File download functionality not implemented above for brevity

    # Add footnotes to the end of the message before displaying to user
    message_content.value += '\n' + '\n'.join(citations)

    return message_content.value

def transcribe_file(path_video):

    with open(path_video, "rb") as file:
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1",
            file=file
        )


    # Accessing the transcription text directly from the response object
    try:
        transcription_text = transcript_response.text
    except AttributeError:
        # Handle cases where the text attribute might not exist
        transcription_text = "Transcription not available."

    return transcription_text
