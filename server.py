from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from duckduckgo_search import DDGS

app = Flask(__name__)
CORS(app)

client = Groq(api_key=" groq_api_key")

chat_history = [
    {"role": "system", "content": "You are Jarvis, a smart AI assistant."}
]

def search_web(query):

    results = []

    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=3):
            results.append(r["body"])

    return " ".join(results)


@app.route("/ask", methods=["POST"])
def ask():
    try:

        data = request.json
        question = data["question"]

        print("User:", question)

        # 🌐 Search internet
        web_results = search_web(question)

        context = f"""
        User question: {question}

        Internet results:
        {web_results}
        """

        chat_history.append({"role": "user", "content": context})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_history
        )

        answer = completion.choices[0].message.content

        chat_history.append({"role": "assistant", "content": answer})

        print("Jarvis:", answer)

        return jsonify({"answer": answer})

    except Exception as e:

        print("ERROR:", e)

        return jsonify({"answer": "Jarvis encountered an error."})


if __name__ == "__main__":
    app.run(port=5000)