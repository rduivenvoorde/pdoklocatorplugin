# -*- coding: utf-8 -*-
"""
 This script initializes the plugin, making it known to QGIS.
"""

def classFactory(iface):
  from .plugin import GeocoderLocator
  return GeocoderLocator(iface)


