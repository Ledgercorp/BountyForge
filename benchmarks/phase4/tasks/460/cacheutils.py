# Copyright (c) 2013, Mahmoud Hashemi
# Adapted excerpt from boltons 26.1.0; see ../LICENSE.upstream
class ThresholdCounter:
    """Fixture shim: only iteritems and most_common from the upstream method."""
    def __init__(self, values):
        self.values = dict(values)

    def iteritems(self):
        return iter(self.values.items())

    def most_common(self, n=None):
        """Get the top *n* keys and counts as tuples. If *n* is omitted,
        returns all the pairs.
        """
        if not n or n <= 0:
            return []
        ret = sorted(self.iteritems(), key=lambda x: x[1], reverse=True)
        if n is None or n >= len(ret):
            return ret
        return ret[:n]