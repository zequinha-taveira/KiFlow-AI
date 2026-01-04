import click
import sys
import os
from src.parser.llm_client import LLMClient
from src.models.circuit import Circuit

@click.group()
def cli():
    """Gerador de PCB a partir de Texto - Text-to-PCB AI"""
    pass

@cli.command()
@click.argument('description')
@click.option('--model', default='gpt-3.5-turbo', help='Modelo da LLM a usar')
def generate(description, model):
    """Gera um projeto KiCad a partir de uma descrição textual."""
    click.echo(f"Interpretando: {description}")
    
    # Configura cliente LLM
    client = LLMClient(model=model)
    
    prompt = f"""
    Você é um engenheiro de hardware especialista em KiCad.
    Converta a descrição abaixo em um JSON válido.
    
    Descrição: {description}
    
    Formato do JSON esperado:
    {{
      "project_name": "nome_do_projeto",
      "description": "descrição curta",
      "components": [
        {{ "id": "R1", "type": "Resistor", "value": "10k", "library_ref": "???" }}
      ],
      "nets": [
        {{ "name": "VCC", "nodes": ["R1:1", "U1:5"] }}
      ]
    }}
    
    IMPORTANTE: No campo 'library_ref', use nomes genéricos como 'Device:R' ou 'Device:LED'.
    Retorne APENAS o JSON.
    """
    
    messages = [{"role": "user", "content": prompt}]
    
    click.echo("Chamando IA...")
    response = client.chat_completion(messages)
    
    try:
        import json
        from src.generators.schematic_generator import SchematicGenerator
        
        # Limpa possível lixo da resposta (se a IA colocar markdown)
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:-3].strip()
        elif json_str.startswith("```"):
            json_str = json_str[3:-3].strip()
            
        data = json.loads(json_str)
        circuit = Circuit(**data)
        
        click.echo(f"Projeto '{circuit.project_name}' interpretado com {len(circuit.components)} componentes.")
        
        # Geração de arquivos
        from src.generators.schematic_generator import SchematicGenerator
        from src.generators.pcb_generator import PCBGenerator
        
        base_filename = circuit.project_name.lower().replace(' ', '_')
        
        # 1. Esquemático
        sch_gen = SchematicGenerator()
        sch_file = f"{base_filename}.kicad_sch"
        sch_gen.generate(circuit, sch_file)
        
        # 2. PCB
        pcb_gen = PCBGenerator()
        pcb_file = f"{base_filename}.kicad_pcb"
        pcb_gen.generate(circuit, pcb_file)
        
        click.echo(f"🚀 Sucesso! Arquivos gerados:\n- {sch_file}\n- {pcb_file}")
        
    except Exception as e:
        click.echo(f"Erro ao processar resposta: {e}")
        click.echo(f"Resposta bruta da IA: {response}")

@cli.command()
def update_libs():
    """Atualiza e indexa as bibliotecas do KiCad."""
    from src.library_manager import main as setup_libs
    from src.component_db import ComponentDB
    
    click.echo("Atualizando repositórios...")
    setup_libs()
    
    click.echo("Indexando componentes (isso pode demorar m pouco)...")
    db = ComponentDB()
    db.scan_libs()
    click.echo("Indexação concluída.")

if __name__ == "__main__":
    cli()
