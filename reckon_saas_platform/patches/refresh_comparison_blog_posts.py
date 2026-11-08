from __future__ import annotations


def execute() -> None:
    """Bring the ten comparison posts to the long-form edition, with topic covers.

    Existing posts keep their status and publish date; only the text, summary, keywords and cover change.
    Posts that were deleted are not brought back.
    """
    from reckon_saas_platform.blog_seed import refresh_posts

    refresh_posts()
