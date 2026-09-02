"""
Seed script used to build golden_set.jsonl and model_outputs.jsonl.

This is intentionally kept in the repo (not thrown away after one run) so the
sampling strategy is reproducible and auditable — a reviewer can see exactly
how each example was constructed and extend the set by adding new dict
entries below, rather than hand-editing JSONL by hand.

See SAMPLING_RATIONALE.md for the *why* behind the category mix.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# GOLDEN SET
# 24 examples across 6 categories (4 each). Each example has:
#   id, category, prompt, context (optional), reference_answer,
#   expects_schema (bool), schema (optional JSON schema), difficulty, tags
# ---------------------------------------------------------------------------
GOLDEN_SET = []

# --- Category 1: factual_qa (closed-book general knowledge) ---------------
GOLDEN_SET += [
    dict(id="fqa_01", category="factual_qa", difficulty="easy",
         prompt="What is the capital of Australia?",
         context=None,
         reference_answer="Canberra",
         expects_schema=False, schema=None,
         tags=["geography"]),
    dict(id="fqa_02", category="factual_qa", difficulty="easy",
         prompt="Who wrote the novel 'Pride and Prejudice'?",
         context=None,
         reference_answer="Jane Austen",
         expects_schema=False, schema=None,
         tags=["literature"]),
    dict(id="fqa_03", category="factual_qa", difficulty="medium",
         prompt="What year did the Berlin Wall fall?",
         context=None,
         reference_answer="1989",
         expects_schema=False, schema=None,
         tags=["history"]),
    dict(id="fqa_04", category="factual_qa", difficulty="medium",
         prompt="What is the chemical symbol for tungsten?",
         context=None,
         reference_answer="W",
         expects_schema=False, schema=None,
         tags=["science"]),
]

# --- Category 2: context_grounded_qa (answer IS in the provided context) --
GOLDEN_SET += [
    dict(id="cgq_01", category="context_grounded_qa", difficulty="easy",
         prompt="According to the passage, what is the company's refund window?",
         context="Our return policy allows customers to request a full refund "
                 "within 30 days of purchase, provided the item is unused and "
                 "in its original packaging. Refunds are processed within 5-7 "
                 "business days.",
         reference_answer="30 days",
         expects_schema=False, schema=None,
         tags=["support", "faithfulness"]),
    dict(id="cgq_02", category="context_grounded_qa", difficulty="medium",
         prompt="Per the passage, how long do refunds take to process once approved?",
         context="Our return policy allows customers to request a full refund "
                 "within 30 days of purchase, provided the item is unused and "
                 "in its original packaging. Refunds are processed within 5-7 "
                 "business days.",
         reference_answer="5-7 business days",
         expects_schema=False, schema=None,
         tags=["support", "faithfulness"]),
    dict(id="cgq_03", category="context_grounded_qa", difficulty="medium",
         prompt="Based on the passage, what was Q3 revenue?",
         context="The company reported Q3 revenue of $42.3 million, up 12% "
                 "year-over-year, driven primarily by growth in the enterprise "
                 "segment. Operating margin held steady at 18%.",
         reference_answer="$42.3 million",
         expects_schema=False, schema=None,
         tags=["finance", "faithfulness"]),
    dict(id="cgq_04", category="context_grounded_qa", difficulty="hard",
         prompt="Per the passage, what drove the Q3 revenue growth?",
         context="The company reported Q3 revenue of $42.3 million, up 12% "
                 "year-over-year, driven primarily by growth in the enterprise "
                 "segment. Operating margin held steady at 18%.",
         reference_answer="Growth in the enterprise segment",
         expects_schema=False, schema=None,
         tags=["finance", "faithfulness"]),
]

# --- Category 3: hallucination_trap (context does NOT contain the answer) -
# Correct model behavior is to say it doesn't know / isn't stated, NOT to
# invent a plausible-sounding number or fact. These exist specifically to
# stress-test the faithfulness / hallucination grader.
GOLDEN_SET += [
    dict(id="hal_01", category="hallucination_trap", difficulty="hard",
         prompt="According to the passage, who is the company's CEO?",
         context="Our return policy allows customers to request a full refund "
                 "within 30 days of purchase, provided the item is unused and "
                 "in its original packaging. Refunds are processed within 5-7 "
                 "business days.",
         reference_answer="Not stated in the passage",
         expects_schema=False, schema=None,
         tags=["hallucination", "faithfulness"]),
    dict(id="hal_02", category="hallucination_trap", difficulty="hard",
         prompt="Per the passage, what was Q3 net income?",
         context="The company reported Q3 revenue of $42.3 million, up 12% "
                 "year-over-year, driven primarily by growth in the enterprise "
                 "segment. Operating margin held steady at 18%.",
         reference_answer="Not stated in the passage",
         expects_schema=False, schema=None,
         tags=["hallucination", "faithfulness"]),
    dict(id="hal_03", category="hallucination_trap", difficulty="hard",
         prompt="Based on the passage, how many employees does the company have?",
         context="The company reported Q3 revenue of $42.3 million, up 12% "
                 "year-over-year, driven primarily by growth in the enterprise "
                 "segment. Operating margin held steady at 18%.",
         reference_answer="Not stated in the passage",
         expects_schema=False, schema=None,
         tags=["hallucination", "faithfulness"]),
    dict(id="hal_04", category="hallucination_trap", difficulty="hard",
         prompt="According to the passage, what is the phone number for customer support?",
         context="Our return policy allows customers to request a full refund "
                 "within 30 days of purchase, provided the item is unused and "
                 "in its original packaging. Refunds are processed within 5-7 "
                 "business days.",
         reference_answer="Not stated in the passage",
         expects_schema=False, schema=None,
         tags=["hallucination", "faithfulness"]),
]

# --- Category 4: summarization ---------------------------------------------
GOLDEN_SET += [
    dict(id="sum_01", category="summarization", difficulty="medium",
         prompt="Summarize the passage in one sentence.",
         context="The city council voted 5-2 on Tuesday to approve funding for "
                 "a new light-rail extension connecting downtown to the airport. "
                 "Construction is expected to begin in early 2027 and take "
                 "approximately three years. Critics raised concerns about the "
                 "$1.2 billion price tag, while supporters pointed to projected "
                 "reductions in highway congestion.",
         reference_answer="The city council approved a $1.2 billion light-rail "
                           "extension from downtown to the airport, with "
                           "construction starting in 2027 and taking about "
                           "three years, despite cost concerns.",
         expects_schema=False, schema=None,
         tags=["summarization", "completeness"]),
    dict(id="sum_02", category="summarization", difficulty="medium",
         prompt="Summarize the passage in one sentence.",
         context="Researchers at a university lab announced a new battery "
                 "chemistry that retains 92% capacity after 2,000 charge "
                 "cycles, roughly double the lifespan of typical lithium-ion "
                 "cells used in electric vehicles today. The team says "
                 "commercial production is still at least five years away "
                 "pending further safety testing.",
         reference_answer="A university lab developed a new battery chemistry "
                           "with roughly double the cycle life of typical EV "
                           "lithium-ion cells, though commercial production is "
                           "still about five years out.",
         expects_schema=False, schema=None,
         tags=["summarization", "completeness"]),
    dict(id="sum_03", category="summarization", difficulty="hard",
         prompt="Summarize the passage in one sentence.",
         context="The quarterly earnings call revealed mixed results: cloud "
                 "revenue grew 22% year-over-year, beating analyst estimates, "
                 "but the hardware division posted its third consecutive "
                 "quarterly loss, prompting the CFO to announce a restructuring "
                 "plan that will cut 400 hardware jobs by year end.",
         reference_answer="Cloud revenue grew 22% and beat estimates, but the "
                           "hardware division's third straight quarterly loss "
                           "led to a restructuring plan cutting 400 jobs.",
         expects_schema=False, schema=None,
         tags=["summarization", "completeness"]),
    dict(id="sum_04", category="summarization", difficulty="hard",
         prompt="Summarize the passage in one sentence.",
         context="A field trial of the new irrigation system showed a 34% "
                 "reduction in water usage across 120 participating farms, "
                 "with no statistically significant change in crop yield. "
                 "Farmers cited the upfront installation cost as the main "
                 "barrier to wider adoption.",
         reference_answer="A field trial found the new irrigation system cut "
                           "water usage by 34% across 120 farms with no yield "
                           "loss, though installation cost remains a barrier "
                           "to adoption.",
         expects_schema=False, schema=None,
         tags=["summarization", "completeness"]),
]

# --- Category 5: structured_extraction (must output valid JSON per schema) -
CONTACT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": ["string", "null"]},
    },
    "required": ["name", "email"],
}
ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "order_id": {"type": "string"},
        "total": {"type": "number"},
        "items": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["order_id", "total", "items"],
}
GOLDEN_SET += [
    dict(id="ext_01", category="structured_extraction", difficulty="medium",
         prompt="Extract the contact info as JSON with keys name, email, phone.",
         context="Please reach out to Priya Nair at priya.nair@example.com or "
                 "by phone at 555-0142 if you have questions about the invoice.",
         reference_answer=json.dumps({"name": "Priya Nair",
                                       "email": "priya.nair@example.com",
                                       "phone": "555-0142"}),
         expects_schema=True, schema=CONTACT_SCHEMA,
         tags=["extraction", "schema"]),
    dict(id="ext_02", category="structured_extraction", difficulty="medium",
         prompt="Extract the contact info as JSON with keys name, email, phone.",
         context="For support, contact Devon Wright (devon.w@example.com). "
                 "No phone number was provided.",
         reference_answer=json.dumps({"name": "Devon Wright",
                                       "email": "devon.w@example.com",
                                       "phone": None}),
         expects_schema=True, schema=CONTACT_SCHEMA,
         tags=["extraction", "schema"]),
    dict(id="ext_03", category="structured_extraction", difficulty="hard",
         prompt="Extract the order as JSON with keys order_id, total, items.",
         context="Order #A1092 shipped today. Total charged: $58.40 for a "
                 "water bottle and a yoga mat.",
         reference_answer=json.dumps({"order_id": "A1092", "total": 58.40,
                                       "items": ["water bottle", "yoga mat"]}),
         expects_schema=True, schema=ORDER_SCHEMA,
         tags=["extraction", "schema"]),
    dict(id="ext_04", category="structured_extraction", difficulty="hard",
         prompt="Extract the order as JSON with keys order_id, total, items.",
         context="Order #B7734: 3 items (desk lamp, notebook, pen set), total "
                 "$34.99.",
         reference_answer=json.dumps({"order_id": "B7734", "total": 34.99,
                                       "items": ["desk lamp", "notebook", "pen set"]}),
         expects_schema=True, schema=ORDER_SCHEMA,
         tags=["extraction", "schema"]),
]

# --- Category 6: reasoning_math ---------------------------------------------
GOLDEN_SET += [
    dict(id="math_01", category="reasoning_math", difficulty="easy",
         prompt="A train travels 60 miles in 1.5 hours. What is its average "
                "speed in mph?",
         context=None,
         reference_answer="40 mph",
         expects_schema=False, schema=None,
         tags=["math"]),
    dict(id="math_02", category="reasoning_math", difficulty="medium",
         prompt="If a shirt costs $40 and is discounted 25%, then a further "
                "10% off the discounted price, what is the final price?",
         context=None,
         reference_answer="$27",
         expects_schema=False, schema=None,
         tags=["math"]),
    dict(id="math_03", category="reasoning_math", difficulty="medium",
         prompt="A team of 6 people can finish a task in 8 days. How many "
                "days would it take a team of 4 people, working at the same "
                "rate, to finish the same task?",
         context=None,
         reference_answer="12 days",
         expects_schema=False, schema=None,
         tags=["math"]),
    dict(id="math_04", category="reasoning_math", difficulty="hard",
         prompt="Sarah is twice as old as Tom. In 5 years, she will be 1.5 "
                "times as old as Tom. How old is Tom now?",
         context=None,
         reference_answer="10 years old",
         expects_schema=False, schema=None,
         tags=["math"]),
]

# ---------------------------------------------------------------------------
# SIMULATED MODEL OUTPUTS
# What the "system under test" (the LLM being evaluated) produced for each
# golden-set prompt. Deliberately mixed quality — some correct, some
# hallucinated, some malformed JSON, some wrongly-refused — so the harness
# has real failures to catch. In a live setup, model_outputs.jsonl would be
# generated by calling the target model directly (see harness/runner.py).
# ---------------------------------------------------------------------------
MODEL_OUTPUTS = {
    "fqa_01": "Canberra",
    "fqa_02": "Pride and Prejudice was written by Jane Austen in 1813.",
    "fqa_03": "The Berlin Wall fell in 1991.",  # WRONG (should be 1989)
    "fqa_04": "The chemical symbol for tungsten is Tu.",  # WRONG (should be W)

    "cgq_01": "According to the passage, the refund window is 30 days.",
    "cgq_02": "Refunds are processed within 5-7 business days once approved.",
    "cgq_03": "Q3 revenue was $42.3 million.",
    "cgq_04": "Growth was mainly driven by the consumer segment expanding "
              "overseas.",  # WRONG / not faithful (should be enterprise)

    # hallucination traps — hal_02 and hal_04 hallucinate specific numbers
    # that are NOT in the context, to test the faithfulness grader.
    "hal_01": "The passage doesn't mention who the CEO is.",
    "hal_02": "Q3 net income was $8.1 million.",  # HALLUCINATED
    "hal_03": "The passage does not state the number of employees.",
    "hal_04": "You can reach customer support at 1-800-555-0199.",  # HALLUCINATED

    "sum_01": "The city council approved a $1.2 billion light-rail extension "
              "from downtown to the airport, with construction starting in "
              "2027 and taking about three years, despite cost concerns.",
    "sum_02": "A university lab created a battery that lasts about twice as "
              "long as typical EV batteries, but it's still five years from "
              "commercial production.",
    "sum_03": "Cloud revenue grew 22% and beat estimates.",  # INCOMPLETE (drops hardware/layoffs)
    "sum_04": "A new irrigation system cut water use by 34% across 120 farms "
              "with no yield loss, though cost is a barrier to adoption.",

    "ext_01": json.dumps({"name": "Priya Nair", "email": "priya.nair@example.com",
                           "phone": "555-0142"}),
    "ext_02": json.dumps({"name": "Devon Wright", "email": "devon.w@example.com",
                           "phone": None}),
    "ext_03": '{"order_id": "A1092", "total": "58.40", items: [water bottle, yoga mat]}',  # MALFORMED JSON
    "ext_04": json.dumps({"order_id": "B7734", "total": 34.99,
                           "items": ["desk lamp", "notebook", "pen set"]}),

    "math_01": "40 mph",
    "math_02": "$28",  # WRONG (should be $27)
    "math_03": "12 days",
    "math_04": "Tom is 10 years old.",
}

if __name__ == "__main__":
    golden_path = HERE / "golden_set.jsonl"
    with golden_path.open("w") as f:
        for row in GOLDEN_SET:
            f.write(json.dumps(row) + "\n")

    outputs_path = HERE / "model_outputs.jsonl"
    with outputs_path.open("w") as f:
        for row in GOLDEN_SET:
            f.write(json.dumps({"id": row["id"],
                                 "model_output": MODEL_OUTPUTS[row["id"]]}) + "\n")

    print(f"Wrote {len(GOLDEN_SET)} examples to {golden_path}")
    print(f"Wrote {len(MODEL_OUTPUTS)} model outputs to {outputs_path}")
