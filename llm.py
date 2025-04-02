from dotenv import dotenv_values
from openai import OpenAI
import mlflow


config = dotenv_values(".env")  # config = {"USER": "foo", "EMAIL": "foo@example.org"}
client = OpenAI(api_key=config["OPENAI_API_KEY"])


# Set MLflow tracking URI
mlflow.set_tracking_uri("http://localhost:8080")

# Example of loading and using the prompt
prompt = mlflow.load_prompt("prompts:/TestPrompt/1")
response = client.chat.completions.create(
    messages=[{
        "role": "user",
        "content": prompt.format(),
    }],
    model="gpt-4o-mini",
)

print(response.choices[0].message.content)