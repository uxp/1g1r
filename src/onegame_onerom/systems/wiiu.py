from . import NullProcessor

class WiiUProcessor(NullProcessor):
    """Wii U disk images. Not sure the best way to convert these from ISO format to
    WUA (Wii U Archive) format which bundles the base game, updates, and DLC patches
    using Cemu automatically. By using this, we're essentially declaring the system
    as tracked but manually managed.
    """
    file_pattern = "*.wu[x|a]"
    pass
