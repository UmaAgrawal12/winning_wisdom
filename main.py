from workflows.content_pipeline import run_text_only_pipeline
from workflows.langgraph_pipeline import run_langgraph_pipeline


if __name__ == "__main__":
    # Option 1: original simple pipeline
    # run_text_only_pipeline()

    # Option 2: LangGraph / LangChain-based pipeline
    run_langgraph_pipeline()