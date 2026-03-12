import logging
from workflows.content_pipeline import run_text_only_pipeline
from workflows.langgraph_pipeline import run_langgraph_pipeline

# Configure logging to see all log messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    run_langgraph_pipeline()