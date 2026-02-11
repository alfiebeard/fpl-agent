python -m fpl_agent.main fetch --gameweek 24
python -m fpl_agent.main enrich --gameweek 24 --show-prompt
python -m fpl_agent.main enrich --gameweek 24

python -m fpl_agent.main gw-update --gameweek 24 --use-enrichments --filter-unavailable-players --cached-only --team Gemini-2.5-Pro --save-team --show-prompt

python -m fpl_agent.main gw-update --gameweek 24 --use-enrichments --filter-unavailable-players --cached-only --team Grok-4 --save-team --show-prompt  --debug

python -m fpl_agent.main gw-update --gameweek 24 --use-enrichments --filter-unavailable-players --cached-only --team GPT-5 --save-team --show-prompt  --debug

