from __future__ import annotations


def execute() -> None:
    """Load the nine buyer-guide and AI posts as drafts, once, for review in SEO Agent Studio.

    Nothing is published here. A vendor user reads each draft and publishes it. A draft that is deleted
    stays deleted: a patch runs only once per site.
    """
    from reckon_saas_platform.blog_guides import seed_guides

    seed_guides()
