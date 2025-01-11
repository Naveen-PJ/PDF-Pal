import openai
from langchain import Conversation

class ChatEngine:
    def __init__(self, api_key, pdf_text):
        openai.api_key = api_key
        self.conversation = Conversation()
        self.pdf_text = pdf_text

    def get_response(self, user_input):
        self.conversation.add_user_input(user_input)
        response = openai.Completion.create(
            engine="davinci",
            prompt=self.conversation.get_prompt() + "\n\n" + self.pdf_text,
            max_tokens=150
        )
        answer = response.choices[0].text.strip()
        self.conversation.add_ai_response(answer)
        return answer
