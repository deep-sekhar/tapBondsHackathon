from google import genai

# Initialize the client
client = genai.Client(api_key="AIzaSyAtz_y7V9H9zbJI1LtrkpOK89oMzRn05-0")

# Generate content
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Explain how AI works",
)

# Print the response
print(response.text)
