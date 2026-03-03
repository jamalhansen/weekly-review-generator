import os
import json
import httpx
from typing import Optional, Dict, Any, Union, get_origin, get_args
from anthropic import Anthropic
from google import genai
from google.genai import types

class ModelClient:
    def __init__(
        self, 
        backend: Optional[str] = None, 
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        debug: bool = False
    ):
        # Support 'backend/model' syntax in the model string
        if model and "/" in model and not backend:
            backend, model = model.split("/", 1)
            
        # List of supported backends
        supported_backends = ["ollama", "anthropic", "gemini", "groq", "deepseek"]
        
        # If model is a backend name, treat it as the backend choice
        if model in supported_backends and not backend:
            backend = model
            model = None

        self.backend = backend or os.environ.get("MODEL_BACKEND", "ollama")
        self.debug = debug
        
        # Default models per backend
        defaults = {
            "ollama": "phi4-mini",
            "anthropic": "claude-3-haiku-20240307",
            "gemini": "gemini-1.5-flash-latest",
            "groq": "llama-3.3-70b-versatile",
            "deepseek": "deepseek-chat"
        }
        
        self.model = model or os.environ.get("MODEL_NAME", defaults.get(self.backend, "phi4-mini"))
        
        # API Keys from env if not provided
        self.api_keys = {
            "anthropic": api_key or os.environ.get("ANTHROPIC_API_KEY"),
            "gemini": api_key or os.environ.get("GEMINI_API_KEY"),
            "groq": api_key or os.environ.get("GROQ_API_KEY"),
            "deepseek": api_key or os.environ.get("DEEPSEEK_API_KEY")
        }

        if self.backend != "ollama" and not self.api_keys.get(self.backend):
            raise ValueError(f"{self.backend.upper()}_API_KEY is required for the {self.backend} backend")

    def complete(
        self, 
        system: str, 
        user: str, 
        response_model: Optional[Any] = None
    ) -> Union[str, Dict[str, Any]]:
        template = self._get_example_json(response_model) if response_model else ""
        
        if self.debug:
            print("\n" + "="*20 + " DEBUG: PROMPT " + "="*20)
            print(f"BACKEND: {self.backend}")
            print(f"MODEL: {self.model}")
            print(f"SYSTEM: {system}")
            print(f"USER: {user}")
            if response_model:
                print(f"TEMPLATE:\n{template}")
            print("="*55 + "\n")

        if self.backend == "ollama":
            result = self._complete_ollama(system, user, response_model, template)
        elif self.backend == "anthropic":
            result = self._complete_anthropic(system, user, response_model, template)
        elif self.backend == "gemini":
            result = self._complete_gemini(system, user, response_model, template)
        elif self.backend == "groq":
            result = self._complete_openai_compatible(
                "https://api.groq.com/openai/v1/chat/completions",
                self.api_keys["groq"],
                system, user, response_model, template
            )
        elif self.backend == "deepseek":
            result = self._complete_openai_compatible(
                "https://api.deepseek.com/chat/completions",
                self.api_keys["deepseek"],
                system, user, response_model, template
            )
        else:
            raise ValueError(f"Unsupported backend: {self.backend}")
            
        if self.debug:
            print("\n" + "="*20 + " DEBUG: RESPONSE " + "="*20)
            print(result)
            print("="*57 + "\n")
            
        return result

    def _get_example_json(self, model: Any) -> str:
        """Return a minimal example JSON structure using the Pydantic model."""
        if not model or not hasattr(model, "model_fields"):
            return "{}"
            
        example = {}
        for name, field in model.model_fields.items():
            # Get the base type (handling Optional, List, etc.)
            annotation = field.annotation
            origin = get_origin(annotation)
            args = get_args(annotation)
            
            # Handle Union/Optional (Union[T, None])
            if origin is Union:
                annotation = args[0]
                origin = get_origin(annotation)
                args = get_args(annotation)

            if origin is list:
                item_type = args[0]
                if hasattr(item_type, "model_fields"):
                    # Nested model
                    example[name] = [json.loads(self._get_example_json(item_type))]
                else:
                    example[name] = ["example item"]
            elif hasattr(annotation, "model_fields"):
                # Nested model
                example[name] = json.loads(self._get_example_json(annotation))
            elif annotation is int:
                example[name] = 0
            elif annotation is bool:
                example[name] = True
            else:
                example[name] = "string"
        return json.dumps(example, indent=2)

    def _clean_json(self, data: Any, model: Any) -> Any:
        """Heuristically fix common LLM JSON errors."""
        if not isinstance(data, dict):
            return data
            
        for field_name, field_info in model.model_fields.items():
            is_list = "List" in str(field_info.annotation) or "list" in str(field_info.annotation)
            if is_list and field_name in data and isinstance(data[field_name], dict):
                data[field_name] = [data[field_name]]
        return data

    def _complete_ollama(self, system: str, user: str, response_model: Optional[Any], template: str) -> Union[str, Dict[str, Any]]:
        url = "http://localhost:11434/api/generate"
        
        prompt = f"""<system>
{system}
</system>

<user>
{user}
</user>

<instructions>
Return ONLY a valid JSON object. Use this exact structure:
{template}
</instructions>"""
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        
        if response_model:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, json=payload)
                if response.status_code == 404:
                    raise RuntimeError(f"Ollama model '{self.model}' not found. Make sure it is downloaded (e.g., 'ollama pull {self.model}') or check if the backend should be different.")
                response.raise_for_status()
                data = response.json()
                content = data.get("response", "")
                return self._parse_json_response(content, response_model) if response_model else content
        except httpx.RequestError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}")

    def _complete_anthropic(self, system: str, user: str, response_model: Optional[Any], template: str) -> Union[str, Dict[str, Any]]:
        client = Anthropic(api_key=self.api_keys["anthropic"])
        actual_system = system
        if response_model:
            actual_system += f"\n\nYou MUST return a valid JSON object matching this structure:\n{template}\nDO NOT include any other text."

        message = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=actual_system,
            messages=[{"role": "user", "content": user}]
        )
        content = message.content[0].text
        return self._parse_json_response(content, response_model) if response_model else content

    def _complete_gemini(self, system: str, user: str, response_model: Optional[Any], template: str) -> Union[str, Dict[str, Any]]:
        client = genai.Client(api_key=self.api_keys["gemini"])
        
        config = types.GenerateContentConfig(
            system_instruction=system,
        )
        
        prompt = user
        if response_model:
            prompt += f"\n\nReturn a valid JSON object matching this structure:\n{template}"
            config.response_mime_type = "application/json"

        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        content = response.text
        return self._parse_json_response(content, response_model) if response_model else content

    def _complete_openai_compatible(self, url: str, api_key: str, system: str, user: str, response_model: Optional[Any], template: str) -> Union[str, Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        actual_system = system
        if response_model:
            actual_system += f"\n\nYou MUST return a valid JSON object matching this structure:\n{template}\nDO NOT include any other text."

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": actual_system},
                {"role": "user", "content": user}
            ]
        }
        
        if response_model:
            payload["response_format"] = {"type": "json_object"}

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_json_response(content, response_model) if response_model else content
        except Exception as e:
            raise RuntimeError(f"API request failed: {e}")

    def _parse_json_response(self, content: str, response_model: Any) -> Dict[str, Any]:
        try:
            result = json.loads(content)
            return self._clean_json(result, response_model)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                result = json.loads(match.group())
                return self._clean_json(result, response_model)
            raise
