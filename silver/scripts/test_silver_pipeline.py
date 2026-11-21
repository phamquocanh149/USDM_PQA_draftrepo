#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit and Integration Tests for USDM Silver Pipeline
===================================================
Tests topology repair, schema enforcement, and edge cases.
"""

import unittest
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Point, Polygon
from usdm_bronze_to_silver import GeometryCleaner, DM_NAME_MAP, PipelineConfig


class TestGeometryCleaner(unittest.TestCase):
    def test_clean_valid_polygon(self):
        """A valid simple polygon should remain unchanged and not marked as repaired."""
        poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
        cleaned, repaired = GeometryCleaner.clean_geometry(poly)
        self.assertIsNotNone(cleaned)
        self.assertTrue(cleaned.is_valid)
        self.assertFalse(repaired)
        self.assertEqual(cleaned.geom_type, "Polygon")

    def test_clean_self_intersecting_bowtie_polygon(self):
        """A self-intersecting bowtie polygon must be repaired by make_valid."""
        bowtie = Polygon([(0, 0), (2, 2), (2, 0), (0, 2), (0, 0)])
        self.assertFalse(bowtie.is_valid)
        cleaned, repaired = GeometryCleaner.clean_geometry(bowtie)
        self.assertIsNotNone(cleaned)
        self.assertTrue(cleaned.is_valid)
        self.assertTrue(repaired)
        self.assertIn(cleaned.geom_type, ["MultiPolygon", "Polygon"])

    def test_clean_empty_or_none_geometry(self):
        """None or empty geometries should return None."""
        cleaned, repaired = GeometryCleaner.clean_geometry(None)
        self.assertIsNone(cleaned)
        self.assertFalse(repaired)

        empty_poly = Polygon()
        cleaned, repaired = GeometryCleaner.clean_geometry(empty_poly)
        self.assertIsNone(cleaned)

    def test_clean_geometry_collection_extraction(self):
        """GeometryCollection containing points/lines and polygons should retain only polygons."""
        poly = Polygon([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
        line = LineString([(3, 3), (4, 4)])
        point = Point(5, 5)
        gc = GeometryCollection([poly, line, point])
        cleaned, repaired = GeometryCleaner.clean_geometry(gc)
        self.assertIsNotNone(cleaned)
        self.assertTrue(cleaned.is_valid)
        self.assertIn(cleaned.geom_type, ["Polygon", "MultiPolygon"])
        self.assertTrue(repaired)


class TestDomainRules(unittest.TestCase):
    def test_dm_name_mapping(self):
        """Check all DM levels 0-4 have exact official USDM category names."""
        expected = {
            0: "Abnormally Dry",
            1: "Moderate Drought",
            2: "Severe Drought",
            3: "Extreme Drought",
            4: "Exceptional Drought",
        }
        self.assertEqual(DM_NAME_MAP, expected)


if __name__ == "__main__":
    unittest.main()
