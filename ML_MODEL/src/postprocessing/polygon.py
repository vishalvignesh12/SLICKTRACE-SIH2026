"""
Converts labeled regions into polygons + centroid + area, in pixel space by
default and in geographic space when a rasterio transform is available
(PRD §45: ML output must supply centroid + polygon + timestamp to the
AIS-correlation stage).
"""
from __future__ import annotations

from typing import Optional, Any

import numpy as np
from shapely.geometry import Polygon, mapping, shape
from skimage import measure

try:
    import rasterio
    import rasterio.warp
    from rasterio.transform import Affine
    _HAS_RASTERIO = True
except ImportError:
    _HAS_RASTERIO = False


def mask_to_polygons(
    binary_mask: np.ndarray,
    transform: Optional["Affine"] = None,
    crs: Optional[Any] = None,
) -> list[dict]:
    """
    Returns a list of dicts, one per connected oil region:
      {
        polygon_geojson_pixel, centroid_px, area_px2,
        polygon_geojson_geo (guaranteed EPSG:4326 lon/lat if transform/crs given),
        centroid_geo ((lon, lat) in EPSG:4326),
        area_m2_approx (approximate area in square meters)
      }
    """
    contours = measure.find_contours(binary_mask.astype(float), level=0.5)
    results = []

    for contour in contours:
        # contour is (row, col) pairs; convert to (x, y) = (col, row)
        coords = [(c, r) for r, c in contour]
        if len(coords) < 3:
            continue
        poly = Polygon(coords)
        if not poly.is_valid or poly.area == 0:
            poly = poly.buffer(0)
            if poly.is_empty:
                continue

        centroid_px = (float(poly.centroid.x), float(poly.centroid.y))
        area_px = float(poly.area)
        entry = {
            "polygon_geojson_pixel": mapping(poly),
            "centroid_px": centroid_px,
            "area_px2": area_px,
        }

        if transform is not None and _HAS_RASTERIO:
            geo_coords = [transform * (x, y) for x, y in poly.exterior.coords]
            geo_poly = Polygon(geo_coords)

            if crs is not None:
                is_4326 = False
                try:
                    if hasattr(crs, "to_epsg") and crs.to_epsg() == 4326:
                        is_4326 = True
                    elif str(crs).upper() in ("EPSG:4326", "OGC:CRS84", "WGS 84"):
                        is_4326 = True
                except Exception:
                    pass

                if is_4326:
                    poly_4326 = geo_poly
                    entry["polygon_geojson_geo"] = mapping(poly_4326)
                    entry["centroid_geo"] = (float(poly_4326.centroid.x), float(poly_4326.centroid.y))
                    # Geodesic approximate area for EPSG:4326 in degrees
                    lat_rad = np.radians(poly_4326.centroid.y)
                    m_per_deg_lat = 111132.92 - 559.82 * np.cos(2 * lat_rad) + 1.17 * np.cos(4 * lat_rad)
                    m_per_deg_lon = 111412.84 * np.cos(lat_rad) - 93.5 * np.cos(3 * lat_rad)
                    entry["area_m2_approx"] = float(poly_4326.area * m_per_deg_lat * m_per_deg_lon)
                else:
                    # Projected CRS (e.g. UTM meters)
                    projected_area_m2 = float(geo_poly.area)
                    try:
                        geojson_4326 = rasterio.warp.transform_geom(
                            src_crs=crs,
                            dst_crs="EPSG:4326",
                            geom=mapping(geo_poly)
                        )
                        poly_4326 = shape(geojson_4326)
                        entry["polygon_geojson_geo"] = geojson_4326
                        entry["centroid_geo"] = (float(poly_4326.centroid.x), float(poly_4326.centroid.y))
                        entry["area_m2_approx"] = projected_area_m2
                    except Exception:
                        entry["polygon_geojson_geo"] = mapping(geo_poly)
                        entry["centroid_geo"] = (float(geo_poly.centroid.x), float(geo_poly.centroid.y))
                        entry["area_m2_approx"] = projected_area_m2
            else:
                entry["polygon_geojson_geo"] = mapping(geo_poly)
                entry["centroid_geo"] = (float(geo_poly.centroid.x), float(geo_poly.centroid.y))
                entry["area_m2_approx"] = float(geo_poly.area)

        results.append(entry)

    return results
