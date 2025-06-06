#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple test file to check FastAPI connection
"""

import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Simple test that doesn't require async
def test_simple():
    """Simple test to verify pytest is working"""
    logger.info("Running simple test")
    assert True

# Another simple test with minimal imports
def test_imports():
    """Test basic imports work"""
    import httpx
    logger.info("Successfully imported httpx")
    assert True

if __name__ == "__main__":
    pytest.main(["-v", __file__])
