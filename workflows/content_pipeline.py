from agents.topic_agent import generate_topics
from agents.script_agent import generate_script
from agents.seo_agent import generate_seo_metadata
import random


def run_text_only_pipeline():
    # 1) Generate topic ideas
    topics = generate_topics()
    print("=== Generated Topics ===")
    for i, t in enumerate(topics.topics, start=1):
        print(f"{i}. {t}")

    # 2) Pick a random topic from the list for variety
    chosen_topic = random.choice(topics.topics)
    print("\n=== Chosen Topic ===")
    print(chosen_topic)

    # 3) Generate script
    script = generate_script(chosen_topic)
    print("\n=== Generated Script ===")
    print(script.text)

    # 4) Generate SEO metadata
    seo = generate_seo_metadata(chosen_topic, script.text)
    print("\n=== SEO Metadata (YouTube) ===")
    print("Title:", seo.youtube.title)
    print("Description:", seo.youtube.description)
    print("Hashtags:", ", ".join("#" + h for h in seo.youtube.hashtags))

    print("\n=== SEO Metadata (Instagram) ===")
    print("Title:", seo.instagram.title)
    print("Description:", seo.instagram.description)
    print("Hashtags:", ", ".join("#" + h for h in seo.instagram.hashtags))

    print("\n=== SEO Metadata (TikTok) ===")
    print("Title:", seo.tiktok.title)
    print("Description:", seo.tiktok.description)
    print("Hashtags:", ", ".join("#" + h for h in seo.tiktok.hashtags))

    print("\n=== SEO Metadata (Facebook) ===")
    print("Title:", seo.facebook.title)
    print("Description:", seo.facebook.description)
    print("Hashtags:", ", ".join("#" + h for h in seo.facebook.hashtags))