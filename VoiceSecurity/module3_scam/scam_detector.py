import re


# Scam-related keywords and phrases
SCAM_PATTERNS = {

    "otp_request": [
        r"\botp\b",
        r"one time password",
        r"verification code",
        r"verification otp",
        r"code you received"
    ],

    "money_request": [
        r"send money",
        r"transfer money",
        r"make a payment",
        r"pay now",
        r"send.*money",
        r"bank transfer",
        r"account.*transfer"
    ],

    "credential_request": [
        r"password",
        r"pin",
        r"passcode",
        r"login details",
        r"username",
        r"cvv",
        r"card number"
    ],

    "sensitive_information": [
        r"account number",
        r"bank details",
        r"personal details",
        r"credit card",
        r"debit card",
        r"aadhaar",
        r"pan card"
    ],

    "urgency": [
        r"urgent",
        r"immediately",
        r"right now",
        r"act now",
        r"within.*minutes",
        r"don't delay",
        r"do not delay",
        r"as soon as possible"
    ],

   "authority_impersonation": [
    r"i am from the bank",
    r"i am calling from the bank",
    r"i am calling from your bank",
    r"calling from your bank",
    r"from your bank",
    r"bank officer",
    r"police officer",
    r"government officer",
    r"cyber crime",
    r"income tax department",
    r"customer care"
],
    "secrecy_pressure": [
        r"don't tell anyone",
        r"do not tell anyone",
        r"keep this secret",
        r"don't inform anyone",
        r"do not inform anyone"
    ],

    "reward_or_prize": [
        r"you have won",
        r"you won",
        r"lottery",
        r"prize",
        r"reward",
        r"cashback",
        r"lucky winner"
    ]
}


# Weight of each indicator
INDICATOR_WEIGHTS = {
    "otp_request": 0.30,
    "money_request": 0.25,
    "credential_request": 0.25,
    "sensitive_information": 0.20,
    "urgency": 0.15,
    "authority_impersonation": 0.15,
    "secrecy_pressure": 0.15,
    "reward_or_prize": 0.15
}


def detect_scam(text):
    """
    Analyze transcript text and return scam score + indicators.
    """

    if not text:
        return {
            "scam_score": 0.0,
            "indicators": []
        }

    text = text.lower()

    indicators = []

    for category, patterns in SCAM_PATTERNS.items():

        for pattern in patterns:

            if re.search(pattern, text):

                if category not in indicators:
                    indicators.append(category)

                break

    # Calculate score
    score = 0.0

    for indicator in indicators:
        score += INDICATOR_WEIGHTS[indicator]

    # Keep score between 0 and 1
    score = min(score, 1.0)

    return {
        "scam_score": round(score, 4),
        "indicators": indicators
    }


if __name__ == "__main__":

    test_text = (
        "Please tell me the OTP you received. "
        "You need to send the money immediately."
    )

    result = detect_scam(test_text)

    print("\nScam Detection Result")
    print("---------------------")
    print("Text:", test_text)
    print("Scam Score:", result["scam_score"])
    print("Indicators:", result["indicators"])