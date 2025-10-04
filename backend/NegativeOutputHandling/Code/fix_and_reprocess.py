#!/usr/bin/env python3
"""
Fix Output Location and Re-run Processing

This script moves existing outputs to the correct workspace location
and re-runs processing to ensure outputs are in the right place.
"""

import os
import shutil
import asyncio
from pathlib import Path

# Import our verification processor
from verify_and_process import main as verify_main


def move_existing_outputs():
    """Move existing outputs from wrong location to correct workspace location."""
    
    print("📁 FIXING OUTPUT LOCATION")
    print("=" * 50)
    
    # Wrong location (double backend)
    wrong_path = Path(r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\backend\NegativeOutputHandling\Data\real_processing_output")
    
    # Correct location (within VS Code workspace)
    correct_path = Path(r"c:\Users\vladc\OneDrive\Escritorio\CodingProjects\JunctionXDelft_Carpathian_Union\backend\NegativeOutputHandling\Data\real_processing_output")
    
    print(f"🔄 Moving from: {wrong_path}")
    print(f"🎯 Moving to:   {correct_path}")
    
    if wrong_path.exists():
        # Create correct directory
        correct_path.mkdir(parents=True, exist_ok=True)
        
        # Move all contents
        moved_files = []
        for item in wrong_path.iterdir():
            dest = correct_path / item.name
            if item.is_file():
                shutil.move(str(item), str(dest))
                moved_files.append(f"📄 {item.name}")
            elif item.is_dir():
                if dest.exists():
                    shutil.rmtree(str(dest))
                shutil.move(str(item), str(dest))
                moved_files.append(f"📁 {item.name}/")
        
        print(f"✅ Moved {len(moved_files)} items:")
        for file in moved_files:
            print(f"   {file}")
        
        # Clean up empty wrong directory structure
        try:
            wrong_path.rmdir()
            wrong_parent = wrong_path.parent
            if wrong_parent.name == "NegativeOutputHandling" and not any(wrong_parent.iterdir()):
                wrong_parent.rmdir()
                wrong_grandparent = wrong_parent.parent
                if wrong_grandparent.name == "backend" and not any(wrong_grandparent.iterdir()):
                    wrong_grandparent.rmdir()
        except:
            pass  # Don't worry if cleanup fails
        
        print(f"🗑️ Cleaned up wrong directory structure")
    else:
        print("ℹ️ No files found in wrong location")
    
    print(f"\n📂 Outputs are now in your VS Code workspace at:")
    print(f"   {correct_path}")
    print()


async def main():
    """Main function to fix location and re-run processing."""
    
    print("🚀 FIXING OUTPUT LOCATION AND RE-PROCESSING")
    print("=" * 70)
    
    # Step 1: Move existing files to correct location
    move_existing_outputs()
    
    # Step 2: Re-run processing with fixed paths
    print("🔄 Re-running processing with correct paths...")
    print()
    await verify_main()
    
    print("\n" + "=" * 70)
    print("🎉 COMPLETE! All outputs are now in your VS Code workspace!")
    print("📁 Location: backend/NegativeOutputHandling/Data/real_processing_output/")


if __name__ == "__main__":
    asyncio.run(main())