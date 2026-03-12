"""
Daily Wisdom Script Generator — Entry Point
============================================
Run this file each day to generate a fresh Marcus Aurelius
wisdom script for the Arthur persona.

Usage:
    python main.py                    # Generate today's script
    python main.py --reset-quotes     # Clear used quotes and regenerate
    python main.py --count            # Show how many scripts generated so far
"""

import argparse
from agents.script_agent import generate_daily_wisdom_script, print_script, get_scripts_count
from agents.topic_agent import reset_used_quotes, get_used_quotes_count


def main():
    parser = argparse.ArgumentParser(description="Daily Wisdom Script Generator")
    parser.add_argument(
        "--reset-quotes",
        action="store_true",
        help="Clear the used quotes tracker before generating",
    )
    parser.add_argument(
        "--count",
        action="store_true",
        help="Show stats and exit without generating",
    )
    args = parser.parse_args()

    if args.count:
        print(f"Scripts generated so far : {get_scripts_count()}")
        print(f"Unique quotes used so far: {get_used_quotes_count()}")
        return
    if args.reset_quotes:
        reset_used_quotes()

    print("Fetching quote and generating script...")
    script = generate_daily_wisdom_script()
    print_script(script)
if __name__ == "__main__":
    main()

