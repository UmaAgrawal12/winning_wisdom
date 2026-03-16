"""
Daily Wisdom Script Generator — Entry Point
============================================
Run this file each day to generate a fresh Winning Wisdom
script for the Arthur persona.

Usage:
    python main.py                    # Generate today's script
    python main.py --reset-quotes     # Clear used quotes and regenerate
    python main.py --count            # Show how many scripts generated so far
"""

import argparse
from agents.script_agent import generate_daily_wisdom_script, print_script, get_scripts_count
from agents.topic_agent import reset_used_quotes, get_used_quotes_count
from agents.score_agent import score_reel_script, print_score
from agents.seo_agent import generate_seo_metadata


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

    print("Scoring script with AI...")
    score = score_reel_script(script)
    print_score(score)

    print("\nGenerating SEO hashtags...")
    seo_result = generate_seo_metadata(
        topic=script.quote,
        script_text=script.spoken_script.full_script,
        audience="general_self_improver"
    )
    
    print("\n" + "=" * 60)
    print("  SEO HASHTAGS")
    print("=" * 60)
    print("\n📺 YOUTUBE:")
    print("  " + " ".join([f"#{tag}" for tag in seo_result.youtube.hashtags]))
    print("\n📷 INSTAGRAM:")
    print("  " + " ".join([f"#{tag}" for tag in seo_result.instagram.hashtags]))
    print("\n🎵 TIKTOK:")
    print("  " + " ".join([f"#{tag}" for tag in seo_result.tiktok.hashtags]))
    print("\n👥 FACEBOOK:")
    print("  " + " ".join([f"#{tag}" for tag in seo_result.facebook.hashtags]))
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()