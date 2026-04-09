# src/main.py
import logging
import sys

from src.config import load_config
from src.collector import collect_all
from src.dedup import deduplicate, preprocess
from src.summarizer import summarize, build_fallback_output
from src.pusher import format_message, push_to_wechat

logger = logging.getLogger(__name__)


def run_pipeline(config_path: str = "config.yaml") -> None:
    """Orchestrate the full pipeline: load config → collect → dedup → summarize → push.

    Exits with code 1 if collection yields nothing or if the final push fails,
    so that CI / cron schedulers can detect a broken run.
    """
    logger.info("=== AI News Daily Pipeline Start ===")

    # 1. Load config
    config = load_config(config_path)

    # 2. Collect
    items = collect_all(config)
    if not items:
        logger.error("All sources failed, no items collected. Aborting.")
        sys.exit(1)

    # 3. Dedup & preprocess
    items = deduplicate(items, config.get("dedup_similarity_threshold", 0.7))
    items = preprocess(
        items,
        max_age_days=config.get("max_age_days", 3),
        max_items=config.get("max_input_items", 80),
    )
    if not items:
        logger.error("No items after dedup/preprocess")
        pushed = push_to_wechat(["今日暂无 AI 新闻更新"], config["wechat_webhook_url"])
        if not pushed:
            logger.error("Push also failed for empty-result notice")
        return

    # 4. Summarize
    result = summarize(items, config["anthropic_api_key"])

    # 5. Push
    if result:
        messages = format_message(result)
    else:
        logger.warning("Summarization failed, using fallback output")
        messages = [build_fallback_output(items)]

    success = push_to_wechat(messages, config["wechat_webhook_url"])

    # 6. Summary
    logger.info(
        f"=== Pipeline Complete === "
        f"Collected: {len(items)} | Push: {'OK' if success else 'FAILED'}"
    )
    if not success:
        logger.error("Final push failed; exiting with error code")
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    run_pipeline(config_file)
