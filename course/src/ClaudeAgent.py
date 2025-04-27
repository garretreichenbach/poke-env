import os
from anthropic import Anthropic
from dotenv import load_dotenv
from LLMAgentBase import LLMAgentBase
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
		system_prompt = (
			"You are an expert Pokémon battle AI capable of making strategic decisions in Pokémon battles. "
			"Your goal is to analyze the current battle state and select the optimal move or switch."
			"\n\n"
			"You MUST use one of these functions to make your decision:"
			"\n"
			"1. choose_move(move_name): Use this to select a move from your available moves."
			"\n"
			"2. choose_switch(pokemon_name): Use this to switch to another Pokémon in your team."
			"\n\n"
			"Always respond with ONLY the function call in this exact format:"
			"choose_move(\"move_name\") or choose_switch(\"pokemon_name\")"
		)

		user_prompt = f"Current battle state:\n{battle_state}\n\nWhat is your next move?"

		try:
			response = await self._run_anthropic_call(system_prompt, user_prompt)

			# Add after receiving the response
			print("RESPONSE TYPE:", type(response))
			print("RESPONSE ATTRIBUTES:", dir(response))
			print("RESPONSE CONTENT:", response.content)
			if hasattr(response, 'model_dump'):
				print("RESPONSE MODEL DUMP:", response.model_dump())

			# Get the text content from the response
			if hasattr(response, 'content') and response.content:
				content_text = response.content[0].text if isinstance(response.content, list) else response.content

				# Simplified parsing for direct function calls
				text = content_text.strip()

				# Parse for choose_move
				if "choose_move" in text:
					import re
					match = re.search(r'choose_move\(["\']([^"\']+)["\']', text)
					if match:
						move_name = match.group(1)
						return {"decision": {"name": "choose_move", "arguments": {"move_name": move_name}}}

				# Parse for choose_switch
				if "choose_switch" in text:
					import re
					match = re.search(r'choose_switch\(["\']([^"\']+)["\']', text)
					if match:
						pokemon_name = match.group(1)
						return {"decision": {"name": "choose_switch", "arguments": {"pokemon_name": pokemon_name}}}

			# If we reach here, no valid function call was found
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

		# Create a function that makes the API call
		def make_api_call():
			return self.client.messages.create(
				model=self.model,
				system=system_prompt,
				messages=[
					{"role": "user", "content": user_prompt}
				],
				tools=tools,
				max_tokens=1024
			)

		# Run in an executor to prevent blocking the event loop
		import asyncio
		loop = asyncio.get_running_loop()
		response = await loop.run_in_executor(None, make_api_call)

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