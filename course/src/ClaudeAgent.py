import os
from typing import Any, Dict

from anthropic import Anthropic
from dotenv import load_dotenv

from LLMAgentBase import LLMAgentBase

# Load environment variables from .env file
load_dotenv()


class ClaudeAgent(LLMAgentBase):
	"""Uses Claude AI API for battle decisions."""

	def __init__(self, api_key: str = None, model: str = "claude-3-opus-20240229", avatar: str = "cynthia", *args, **kwargs):
		# Set avatar before calling parent constructor
		kwargs['avatar'] = avatar
		kwargs['start_timer_on_battle_start'] = True
		super().__init__(*args, **kwargs)
		self.model = model
		# Use API key from environment variable if not provided
		self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
		if not self.api_key:
			raise ValueError("Anthropic API key not provided and not found in environment variables")

		self.client = Anthropic(api_key=self.api_key)
		self.battle_history = []

	async def _get_llm_decision(self, battle_state: str) -> Dict[str, Any]:
		system_prompt = (
			"You are an expert Pokémon battle AI capable of making strategic decisions in Pokémon battles. "
			"Your goal is to analyze the current battle state and select the optimal move or switch based on:"
			"\n- Type advantages and disadvantages"
			"\n- Current HP and status conditions"
			"\n- Move power, accuracy, and effects"
			"\n- Weather and field conditions"
			"\n- Team composition and available switches"
			"\n\nSpecial cases to be aware of:"
			"\n- If no moves are available (empty list under 'Available moves'), choose 'Struggle' as your move."
			"\n- If no switches are available (empty list under 'Available switches'), you cannot switch out."
			"\n\nMake the most strategic choice possible with the information available."
		)

		user_prompt = f"Current battle state:\n{battle_state}\n\nWhat is your next move?"

		try:
			response = await self._run_anthropic_call(system_prompt, user_prompt)

			# Check for tool_use in response
			for content_item in response.content:
				if hasattr(content_item, 'type') and content_item.type == 'tool_use':
					function_name = content_item.name
					arguments = content_item.input

					if function_name in ["choose_move", "choose_switch"]:
						return {"decision": {"name": function_name, "arguments": arguments}}

			# If we reach here, no tool_use was found
			return {"error": "Could not parse a valid function call from Claude's response"}

		except Exception as e:
			print(f"Unexpected error during Claude API call: {e}")
			import traceback
			traceback.print_exc()
			return {"error": f"Unexpected error: {e}"}

	async def _run_anthropic_call(self, system_prompt, user_prompt):
		"""Make the actual call to Claude API"""
		tools = [{
			"name": "choose_move",
			"description": "Select a move from your available moves",
			"input_schema": {
				"type": "object",
				"properties": {
					"move_name": {
						"type": "string",
						"description": "The name or ID of the move to use. Must be one of the available moves."
					}
				},
				"required": ["move_name"]
			}
		}, {
			"name": "choose_switch",
			"description": "Switch to another Pokémon in your team",
			"input_schema": {
				"type": "object",
				"properties": {
					"pokemon_name": {
						"type": "string",
						"description": "The name of the Pokémon to switch to. Must be one of the available switches."
					}
				},
				"required": ["pokemon_name"]
			}
		}]

		# Create a function that makes the API call
		def make_api_call():
			return self.client.messages.create(
				model=self.model,
				system=system_prompt,
				messages=[
					{"role": "user", "content": user_prompt}
				],
				tools=tools,
				max_tokens=1024,
				temperature=0.2  # Lower temperature for more consistent responses
			)

		# Run in an executor to prevent blocking the event loop
		import asyncio
		loop = asyncio.get_running_loop()
		response = await loop.run_in_executor(None, make_api_call)

		return response