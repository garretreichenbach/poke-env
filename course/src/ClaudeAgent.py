import os
from anthropic import Anthropic
from dotenv import load_dotenv
import LLMAgentBase
from typing import Any, Dict

# Load environment variables from .env file
load_dotenv()


class ClaudeAgent(LLMAgentBase):
	"""Uses Claude AI API for battle decisions."""

	def __init__(self, api_key: str = None, model: str = "claude-3-opus-20240229", *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.model = model
		# Use API key from environment variable if not provided
		self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
		if not self.api_key:
			raise ValueError("Anthropic API key not provided and not found in environment variables")

		self.client = Anthropic(api_key=self.api_key)
		self.battle_history = []

	async def _get_llm_decision(self, battle_state: str) -> Dict[str, Any]:
		"""Sends battle state to Claude and gets back the function call decision."""
		system_prompt = (
			"You are an expert Pokémon battle AI capable of making strategic decisions in Pokémon battles. "
			"Your goal is to analyze the current battle state and select the optimal move or switch."
			"\n\n"
			"You have access to two functions:"
			"\n"
			"1. choose_move(move_name): Use this to select a move from your available moves."
			"\n"
			"2. choose_switch(pokemon_name): Use this to switch to another Pokémon in your team."
			"\n\n"
			"For each turn, you will analyze the battle state and select ONE action using these functions."
		)

		user_prompt = f"Current battle state:\n{battle_state}\n\nWhat is your next move?"

		try:
			response = await self._run_anthropic_call(system_prompt, user_prompt)

			# Process Claude's response
			function_name = None
			arguments = {}

			# Look for tool use in the response
			if response.tool_use:
				tool_use = response.tool_use[0]
				function_name = tool_use.name
				arguments = tool_use.input

			if function_name:
				return {"decision": {"name": function_name, "arguments": arguments}}
			else:
				# Fallback - try to parse response text for move decision
				return self._parse_text_response(response.content)

		except Exception as e:
			print(f"Unexpected error during Claude API call: {e}")
			return {"error": f"Unexpected error: {e}"}

	async def _run_anthropic_call(self, system_prompt, user_prompt):
		"""Make the actual call to Claude API"""
		tools = [{
			"name": "choose_move",
			"description": "Use this function to select a move from your available moves",
			"input_schema": {
				"type": "object",
				"properties": {
					"move_name": {
						"type": "string",
						"description": "The name of the move to use"
					}
				},
				"required": ["move_name"]
			}
		}, {
			"name": "choose_switch",
			"description": "Use this function to switch to another Pokémon in your team",
			"input_schema": {
				"type": "object",
				"properties": {
					"pokemon_name": {
						"type": "string",
						"description": "The name of the Pokémon to switch to"
					}
				},
				"required": ["pokemon_name"]
			}
		}]

		# Make the API call
		response = await self.client.messages.create(
			model=self.model,
			system=system_prompt,
			messages=[
				{"role": "user", "content": user_prompt}
			],
			tools=tools,
			max_tokens=1024
		)

		return response

	def _parse_text_response(self, content):
		"""Fallback parser for extracting decisions from text responses"""
		text = content[0].text

		if "choose_move" in text.lower():
			# Try to extract move name from text
			# This is a simplistic implementation
			for line in text.split('\n'):
				if "choose_move" in line.lower():
					parts = line.split('"')
					if len(parts) >= 3:
						move_name = parts[1]
						return {"decision": {"name": "choose_move", "arguments": {"move_name": move_name}}}

		if "choose_switch" in text.lower():
			# Try to extract pokemon name from text
			for line in text.split('\n'):
				if "choose_switch" in line.lower():
					parts = line.split('"')
					if len(parts) >= 3:
						pokemon_name = parts[1]
						return {"decision": {"name": "choose_switch", "arguments": {"pokemon_name": pokemon_name}}}

		# If no clear decision found, return error
		return {"error": "Could not parse decision from text response"}