from conversation import get_next_question


product_state = {
    "product_name": "Panadol Extra",
    "nafdac_number": "A4-1409",
    "manufacturer": None,
    "batch_number": None,
    "expiry_date": None,
}


next_question = get_next_question(product_state)

print(next_question)