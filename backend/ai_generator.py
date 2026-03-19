import anthropic
from typing import List, Optional
from config import config

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- You may search up to 2 times per query — only when the first search is incomplete or the question has distinct parts requiring different searches
- Do not repeat the same search twice; use a different or more specific query for the second search
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives
- Use the `get_course_outline` tool for questions about a course's structure, lesson list, or outline

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **Course outline responses**: Include the course title, course link, and each lesson's number and title
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to config.MAX_TOOL_ROUNDS sequential tool-call rounds.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Build initial messages list — mutated in-place each round
        messages = [{"role": "user", "content": query}]

        # Prepare first API call parameters
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # First API call
        response = self.client.messages.create(**api_params)

        # Agentic tool loop — up to MAX_TOOL_ROUNDS sequential rounds
        rounds_used = 0
        while response.stop_reason == "tool_use" and tool_manager and rounds_used < config.MAX_TOOL_ROUNDS:
            # Execute all tool calls in this round
            tool_results = []
            had_error = False
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Tool execution failed: {e}"
                        had_error = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Append this round's exchange to message history
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
            rounds_used += 1

            # Build next call — include tools only if rounds remain and no error occurred
            next_params = {**self.base_params, "messages": messages, "system": system_content}
            if tools and rounds_used < config.MAX_TOOL_ROUNDS and not had_error:
                next_params["tools"] = tools
                next_params["tool_choice"] = {"type": "auto"}

            response = self.client.messages.create(**next_params)

            if had_error:
                break

        return response.content[0].text
