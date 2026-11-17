# START_MODULE_CONTRACT: MOD-FEED-CONTEXT
# PURPOSE: Expose the active family to translation helpers without process global language settings.
# PRD_REF: docs/PRD.md#PIPELINE
# INVARIANTS:
# - families retain independent language lists [review: engine lead]
# CHANGES_WITH:
# - docs/PRD.md#FORMS
# :END_MODULE_CONTRACT
def instance():
    from .builder import context
    return context.get()
