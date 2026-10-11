from product_extractor import extract_field_answer


text = "the manufacturer's name is emzor."

result = extract_field_answer(
    text,
    "manufacturer",
)

print("Extracted:", result)