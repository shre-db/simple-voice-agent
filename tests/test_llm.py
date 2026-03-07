from app.llm import generate_answer

question = "Why is my transfer late?"

context = """
Wise provides an estimated delivery time when you create a transfer. Delays can occur if the payment method takes longer, if security checks are required, if banks are closed on weekends or holidays, or if there are mistakes in the recipient's account details.
"""

response = generate_answer(question, context)

print(response)