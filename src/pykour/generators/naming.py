"""Naming utilities for code generation."""

from __future__ import annotations

# Common irregular plurals
IRREGULAR_PLURALS: dict[str, str] = {
    "person": "people",
    "child": "children",
    "man": "men",
    "woman": "women",
    "foot": "feet",
    "tooth": "teeth",
    "goose": "geese",
    "mouse": "mice",
    "ox": "oxen",
    "leaf": "leaves",
    "life": "lives",
    "knife": "knives",
    "wife": "wives",
    "half": "halves",
    "self": "selves",
    "elf": "elves",
    "loaf": "loaves",
    "potato": "potatoes",
    "tomato": "tomatoes",
    "hero": "heroes",
    "echo": "echoes",
    "cactus": "cacti",
    "focus": "foci",
    "fungus": "fungi",
    "nucleus": "nuclei",
    "syllabus": "syllabi",
    "analysis": "analyses",
    "basis": "bases",
    "crisis": "crises",
    "diagnosis": "diagnoses",
    "hypothesis": "hypotheses",
    "oasis": "oases",
    "parenthesis": "parentheses",
    "thesis": "theses",
    "criterion": "criteria",
    "phenomenon": "phenomena",
    "datum": "data",
    "medium": "media",
    "index": "indices",
    "appendix": "appendices",
    "matrix": "matrices",
    "vertex": "vertices",
}

# Reverse mapping for singularize
IRREGULAR_SINGULARS: dict[str, str] = {v: k for k, v in IRREGULAR_PLURALS.items()}

# Uncountable words (same in singular and plural)
UNCOUNTABLE: set[str] = {
    "equipment",
    "information",
    "rice",
    "money",
    "species",
    "series",
    "fish",
    "sheep",
    "deer",
    "aircraft",
    "news",
    "advice",
    "furniture",
    "luggage",
    "traffic",
    "software",
    "hardware",
    "data",
    "metadata",
    "feedback",
    "status",
}


def pluralize(word: str) -> str:
    """Convert a singular word to plural form.

    Args:
        word: Singular word to pluralize.

    Returns:
        Plural form of the word.

    Examples:
        >>> pluralize("user")
        "users"
        >>> pluralize("category")
        "categories"
        >>> pluralize("person")
        "people"
    """
    if not word:
        return word

    lower_word = word.lower()

    # Check uncountable
    if lower_word in UNCOUNTABLE:
        return word

    # Check irregular
    if lower_word in IRREGULAR_PLURALS:
        plural = IRREGULAR_PLURALS[lower_word]
        # Preserve original case
        if word[0].isupper():
            return plural.capitalize()
        return plural

    # Apply standard rules
    if lower_word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    elif lower_word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    elif lower_word.endswith("f"):
        return word[:-1] + "ves"
    elif lower_word.endswith("fe"):
        return word[:-2] + "ves"
    elif lower_word.endswith("o") and word[-2] not in "aeiou":
        return word + "es"
    else:
        return word + "s"


def singularize(word: str) -> str:
    """Convert a plural word to singular form.

    Args:
        word: Plural word to singularize.

    Returns:
        Singular form of the word.

    Examples:
        >>> singularize("users")
        "user"
        >>> singularize("categories")
        "category"
        >>> singularize("people")
        "person"
    """
    if not word:
        return word

    lower_word = word.lower()

    # Check uncountable
    if lower_word in UNCOUNTABLE:
        return word

    # Check irregular (reverse lookup)
    if lower_word in IRREGULAR_SINGULARS:
        singular = IRREGULAR_SINGULARS[lower_word]
        # Preserve original case
        if word[0].isupper():
            return singular.capitalize()
        return singular

    # Apply standard rules (reverse)
    if lower_word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
    elif lower_word.endswith("ves"):
        # Could be -f or -fe
        base = word[:-3]
        if base + "f" in IRREGULAR_PLURALS or (base + "fe") in IRREGULAR_PLURALS:
            return word[:-3] + "f"
        return word[:-3] + "fe"
    elif lower_word.endswith("es"):
        # Check if removing 'es' gives valid word
        if lower_word.endswith(("ses", "xes", "zes", "ches", "shes")):
            return word[:-2]
        elif lower_word.endswith("oes"):
            return word[:-2]
        return word[:-1]  # Just remove 's'
    elif lower_word.endswith("s") and not lower_word.endswith("ss"):
        return word[:-1]
    else:
        return word


def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase.

    Args:
        snake_str: String in snake_case.

    Returns:
        String in camelCase.

    Examples:
        >>> snake_to_camel("user_name")
        "userName"
        >>> snake_to_camel("get_user_by_id")
        "getUserById"
    """
    if not snake_str:
        return snake_str

    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def snake_to_pascal(snake_str: str) -> str:
    """Convert snake_case to PascalCase.

    Args:
        snake_str: String in snake_case.

    Returns:
        String in PascalCase.

    Examples:
        >>> snake_to_pascal("user_name")
        "UserName"
        >>> snake_to_pascal("user_table")
        "UserTable"
    """
    if not snake_str:
        return snake_str

    return "".join(word.capitalize() for word in snake_str.split("_"))


def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase or PascalCase to snake_case.

    Args:
        camel_str: String in camelCase or PascalCase.

    Returns:
        String in snake_case.

    Examples:
        >>> camel_to_snake("userName")
        "user_name"
        >>> camel_to_snake("UserTable")
        "user_table"
    """
    if not camel_str:
        return camel_str

    result = []
    for i, char in enumerate(camel_str):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)
