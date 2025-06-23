#!/usr/bin/env python3
"""
Standalone test for tactics2d.map.parser.OSMParser based on official documentation.
"""
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project's backend/app directory to the Python path to ensure imports work
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from app.utils.tactics2d_wrapper import TACTICS2D_AVAILABLE
    if TACTICS2D_AVAILABLE:
        from tactics2d.map.parser import OSMParser
    else:
        raise ImportError("Tactics2D is not available.")
except ImportError as e:
    logger.error(f"Failed to import tactics2d components: {e}")
    sys.exit(1)

def test_official_osm_parser():
    """
    Tests the OSMParser by following the provided API documentation precisely.
    1. Instantiates the parser.
    2. Calls the .parse() method on the target OSM file.
    3. Reports on the output.
    """
    osm_file_path = Path(__file__).parent / "data" / "highD_map" / "highD_2.osm"
    
    if not osm_file_path.exists():
        logger.error(f"CRITICAL: OSM file does not exist at the expected path: {osm_file_path}")
        return

    logger.info(f"Starting test with OSM file: {osm_file_path}")

    try:
        # 1. Create OSMParser instance as per the documentation
        parser = OSMParser()
        logger.info("OSMParser instance created successfully.")

        # 2. Parse the OSM file
        logger.info("Calling parser.parse()...")
        # This is the core operation we are re-evaluating.
        map_data = parser.parse(str(osm_file_path))
        
        # 3. Process and report on the result
        logger.info("✅✅✅ Success! parser.parse() completed without errors.")
        logger.info(f"Type of returned object: {type(map_data)}")

        # Inspect the returned map_data object based on documentation
        if hasattr(map_data, 'nodes'):
            logger.info(f"  - Found {len(map_data.nodes)} nodes.")
        if hasattr(map_data, 'ways'):
            logger.info(f"  - Found {len(map_data.ways)} ways.")
        if hasattr(map_data, 'relations'):
            logger.info(f"  - Found {len(map_data.relations)} relations.")
        if hasattr(map_data, 'bounds'):
            logger.info(f"  - Found map bounds: {map_data.bounds}")
        else:
            logger.warning("  - Map data does not have a 'bounds' attribute.")

    except Exception as e:
        logger.error(f"❌❌❌ Failure! An exception occurred during parser.parse(): {e}", exc_info=True)
        logger.error("This confirms that the official parser fails on this file, likely due to internal errors (e.g., CRS/projection issues) not evident from the API signature.")

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("Re-evaluating official tactics2d.map.parser.OSMParser")
    logger.info("="*60)
    test_official_osm_parser()
    logger.info("="*60)
    logger.info("Test finished.")
    logger.info("="*60)
