"""
EvoDeck Mapping Rules

This file translates TCGdex data into EvoDeck's
collector-friendly organization.
"""


def map_set_id(set_id, card_number):
    """
    Given a TCGdex set ID and card number,
    return the EvoDeck set ID.
    """

    #
    # Astral Radiance Trainer Gallery
    #

    if (
        set_id == "sword_and_shield_astral_radiance"
        and card_number.startswith("TG")
    ):
        return "sword_and_shield_astral_radiance_trainer_gallery"

    #
    # Celebrations Classic Collection
    #

    if (
        set_id == "sword_and_shield_celebrations"
        and "A" in card_number
    ):
        return "sword_and_shield_celebrations_classic_collection"

    #
    # Otherwise...
    #

    return set_id