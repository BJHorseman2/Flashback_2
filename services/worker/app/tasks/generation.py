"""Image generation tasks."""
import asyncio
from celery import shared_task
import structlog

from app.celery_app import app

logger = structlog.get_logger()


@app.task(bind=True, max_retries=2)
def generate_scene_images(self, scene_id: str):
    """
    Generate all 5 lens images for a scene.

    This task is triggered when a new scene is created and needs images.
    """
    logger.info("starting_scene_generation", scene_id=scene_id, task_id=self.request.id)

    try:
        # Run async generation in sync context
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_generate_scene_async(scene_id))

        logger.info("scene_generation_complete", scene_id=scene_id, success=result)
        return {"scene_id": scene_id, "success": result}

    except Exception as e:
        logger.error("scene_generation_failed", scene_id=scene_id, error=str(e))
        raise self.retry(exc=e, countdown=60)


@app.task(bind=True, max_retries=3)
def generate_single_lens(self, scene_id: str, lens_id: int):
    """
    Generate a single lens image.

    Used for retrying failed lenses independently.
    """
    logger.info(
        "starting_lens_generation",
        scene_id=scene_id,
        lens_id=lens_id,
        task_id=self.request.id
    )

    try:
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_generate_lens_async(scene_id, lens_id))

        logger.info(
            "lens_generation_complete",
            scene_id=scene_id,
            lens_id=lens_id,
            success=result
        )
        return {"scene_id": scene_id, "lens_id": lens_id, "success": result}

    except Exception as e:
        logger.error(
            "lens_generation_failed",
            scene_id=scene_id,
            lens_id=lens_id,
            error=str(e)
        )
        raise self.retry(exc=e, countdown=30)


async def _generate_scene_async(scene_id: str) -> bool:
    """Async implementation of scene generation."""
    # Import here to avoid circular imports
    from app.services.generator import SceneGenerator

    generator = SceneGenerator()
    return await generator.generate_all_lenses(scene_id)


async def _generate_lens_async(scene_id: str, lens_id: int) -> bool:
    """Async implementation of single lens generation."""
    from app.services.generator import SceneGenerator

    generator = SceneGenerator()
    return await generator.generate_single_lens(scene_id, lens_id)


@app.task
def cleanup_failed_scenes():
    """
    Periodic task to cleanup or retry failed scenes.

    Run via celery beat scheduler.
    """
    logger.info("running_cleanup_task")
    # Implementation would query for failed scenes and either retry or mark as permanently failed
    pass
