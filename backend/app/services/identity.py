import random

# Public, non-identifying handle assigned at signup — this is what other
# users see on the shared map, never the account's real name.
_ADJECTIVES = [
    "quiet", "amber", "brisk", "cedar", "copper", "dusky", "feral", "gentle",
    "hollow", "idle", "jagged", "keen", "lucid", "mellow", "nimble", "olive",
    "plucky", "quartz", "rustic", "sable", "tidal", "umber", "vivid", "wry",
]
_NOUNS = [
    "falcon", "harbor", "lantern", "meadow", "otter", "pilgrim", "quarry",
    "ridge", "sparrow", "thicket", "unicorn", "vessel", "willow", "yarrow",
    "zephyr", "badger", "cove", "drift", "ember", "fern",
]


def generate_username() -> str:
    return f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}-{random.randint(10, 99)}"
