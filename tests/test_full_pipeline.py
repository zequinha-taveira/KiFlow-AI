import sys
import os
from src.bridge import GenerationBridge

def test_pipeline():
    print("--- Iniciando Teste de Pipeline Completo ---")
    
    # Mock de uma descrição de hardware
    description = "Um circuito com microcontrolador ESP32-WROOM-32 e um regulador de tenso AMS1117-3.3V com capacitores de desacoplamento."
    
    if not os.getenv("LLM_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("Aviso: LLM_API_KEY não encontrada. O teste executará até a chamada da IA.")
    
    bridge = GenerationBridge()
    
    print(f"Processando: {description}")
    
    # Executa o pipeline
    success, message = bridge.process(description)
    
    print(f"Resultado: {'SUCESSO' if success else 'FALHA'}")
    print(f"Mensagem: {message}")
    
    if success:
        print("Verificando arquivos na pasta raiz...")
        files = [f for f in os.listdir(".") if f.endswith(".kicad_sch") or f.endswith(".kicad_pcb")]
        print(f"Arquivos encontrados: {files}")

if __name__ == "__main__":
    test_pipeline()
