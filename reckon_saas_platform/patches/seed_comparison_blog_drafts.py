from __future__ import annotations


def execute() -> None:
    """Load the ten comparison posts as drafts, once, for review in SEO Agent Studio.

    Nothing is published here. A vendor user reads each draft and publishes it from the SEO Agent page
    or the SEO Article list. A draft that is deleted stays deleted: a patch runs only once per site.
    """
    from reckon_saas_platform.blog_seed import seed_drafts

    seed_drafts()
