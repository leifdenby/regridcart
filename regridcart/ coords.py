"""
common interface for getting lat/lon coordinates for a dataset whether these
are given directly as variables or must be calculated from the projection
information
"""

def has_latlon_coords(da):
    pass

def using_crs(da):
    pass

def is_cartesian(da):
    pass
