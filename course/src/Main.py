import asyncio
from ClaudeAgent import ClaudeAgent
from poke_env.player import RandomPlayer


async def main():
	# Create your Claude-powered agent
	claude_agent = ClaudeAgent(battle_format="gen9randombattle")

	# Create a simple opponent
	opponent = RandomPlayer(battle_format="gen9randombattle")

	# Have them battle
	await claude_agent.battle_against(opponent, n_battles=1)

	# Print results
	print(f"Battle finished! Result: {'Won' if claude_agent.n_won_battles > 0 else 'Lost'}")


if __name__ == "__main__":
	asyncio.run(main())