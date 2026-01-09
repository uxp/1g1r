from . import NullProcessor

class SwitchProcessor(NullProcessor):
    """Switch images. By using this, we're essentially declaring the system
    as tracked but manually managed. See also the WiiU system.
    """
    file_pattern = "*.(ns[p|z]|xci)"
