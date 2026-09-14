# SmartJisho
Japanese Kanji Search Engine: Application allowing to search up Kanji, displaying info about it and the most common Japanese words using it based on daily world frequency, and using LLM Based definition and translation + exporting Anki card to boost productivity

**Why**

I wanted to create something useful to aid my Japanese learning adventure with Anki. Most current japanese dictionnaries don't use a frequency-based word list, and LLMs used for language are usually very accurate in describing how certain words are used in real life. Combining these two things + anki export option will make for a much more enjoyable and productive japanese learning experience !


First Milestone -> Display a Kanji retrieved through FastAPI.

Workflow -> Trunk-based development, using short-lived branches merged into main through pull requests, aswell as feature flags when needed. CI will also be configured and used.
