import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    """
    Cliente universal para LLMs usando o SDK da OpenAI.
    Suporta OpenAI nativo, OpenRouter e Ollama.
    """
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 base_url: Optional[str] = None, 
                 model: str = "gpt-3.5-turbo"):
        
        # Lógica para MODO AUTO
        if model.upper() == "AUTO":
            if os.getenv("OPENAI_API_KEY"):
                self.model = "gpt-4o"
                self.api_key = os.getenv("OPENAI_API_KEY")
                self.base_url = None
            elif os.getenv("OPENROUTER_API_KEY"):
                self.model = "openrouter/auto"
                self.api_key = os.getenv("OPENROUTER_API_KEY")
                self.base_url = "https://openrouter.ai/api/v1"
            else:
                self.model = "llama3"
                self.api_key = "no-key-needed"
                self.base_url = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        else:
            self.api_key = api_key or os.getenv("LLM_API_KEY", "no-key-needed")
            self.base_url = base_url or os.getenv("LLM_BASE_URL")
            self.model = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
            
            # Detecção de OpenRouter via nome do modelo
            if "/" in self.model and not self.base_url:
                self.base_url = "https://openrouter.ai/api/v1"
                self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("LLM_API_KEY")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def chat_completion(self, 
                       messages: List[Dict[str, str]], 
                       temperature: float = 0.2,
                       response_format: Optional[Dict] = None,
                       stream: bool = True,
                       callback: Optional[callable] = None) -> str:
        """
        Gera uma resposta do modelo com suporte a streaming.
        """
        try:
            extra_body = {}
            if "openrouter.ai" in (self.base_url or ""):
                extra_body["include_usage"] = True

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
                stream=stream,
                extra_body=extra_body if extra_body else None
            )

            full_content = ""
            if stream:
                for chunk in response:
                    content = chunk.choices[0].delta.content if chunk.choices else None
                    if content:
                        full_content += content
                        if callback:
                            callback(content)
                    
                    # Extração de Reasoning Tokens no final (padrão OpenRouter)
                    if hasattr(chunk, 'usage') and chunk.usage:
                        reasoning = getattr(chunk.usage, 'reasoning_tokens', 0)
                        if reasoning and callback:
                            callback(f"\n[AI Reasoning Tokens: {reasoning}]")
                return full_content
            else:
                return response.choices[0].message.content
        except Exception as e:
            return f"Erro na chamada da LLM: {str(e)}"

if __name__ == "__main__":
    # Teste rápido de inicialização
    client = LLMClient()
    print(f"Cliente inicializado para o modelo: {client.model}")
