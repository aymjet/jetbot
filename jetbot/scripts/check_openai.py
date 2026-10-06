import os
from openai import OpenAI

client = OpenAI()

response = client.responses.create(
    model=os.environ.get("OPENAI_MODEL", "gpt-6-astra"),
    input="こんにちは。jetbotです。日本語で短く返事してください。"
)

print(response.output_text)

