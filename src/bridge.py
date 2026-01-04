import json
from src.parser.llm_client import LLMClient
from src.models.circuit import Circuit
from src.generators.schematic_generator import SchematicGenerator
from src.generators.pcb_generator import PCBGenerator

class GenerationBridge:
    """
    Coordena o fluxo de geração: Texto -> JSON -> Sch -> PCB.
    """
    def __init__(self, model="gpt-3.5-turbo"):
        self.client = LLMClient(model=model)
        self.sch_gen = SchematicGenerator()
        self.pcb_gen = PCBGenerator()

    def process(self, description: str, callback=None):
        """
        Executa o pipeline completo. 
        O callback pode ser usado para atualizar a UI do plugin.
        """
        def log(msg):
            if callback: callback(msg)
            print(msg)

        log("Enviando descrição para a IA...")
        # 1. Parsing via LLM
        log("Interpretando requisitos com IA...")
        prompt_context = f"""
        Você é um engenheiro de hardware KiCad. Converta em JSON:
        Texto: {description}
        Retorne APENAS o JSON no formato:
        {{
            "project_name": "...",
            "description": "...",
            "components": [{{ "id": "R1", "type": "Resistor", "value": "10k", "library_ref": "Device:R" }}],
            "nets": [{{ "name": "VCC", "nodes": ["R1:1"] }}]
        }}
        """
        messages = [{"role": "user", "content": prompt_context}]
        
        raw_response = self.client.chat_completion(
            messages, 
            response_format={"type": "json_object"},
            callback=log # Agora passa o log para streaming
        )
        
        try:
            # Limpeza básica de markdown
            json_str = raw_response.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"): json_str = json_str[4:]
            
            data = json.loads(json_str)
            circuit = Circuit(**data)
            
            # Refinamento de Componentes via DB
            from src.component_db import ComponentDB
            db = ComponentDB()
            log("Refinando referências de componentes via DB...")
            
            for comp in circuit.components:
                # Tenta encontrar o símbolo real mais próximo
                results = db.search_symbol(comp.type if comp.library_ref == "???" else comp.library_ref)
                if results:
                    comp.library_ref = results[0][0] # Usa o full_name real
                
                # Tenta sugerir footprint se estiver vazio
                if not comp.footprint:
                    fps = db.get_suggested_footprints(comp.library_ref)
                    if fps:
                        comp.footprint = fps[0]
            
            log(f"Circuito '{circuit.project_name}' refinado e validado.")
            
            base_name = circuit.project_name.lower().replace(" ", "_")
            
            # Gerar arquivo de projeto .kicad_pro
            log("Gerando arquivo de projeto (.kicad_pro)...")
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader("src/generators"))
            pro_template = env.get_template("project_template.j2")
            pro_content = pro_template.render({"project_name": circuit.project_name})
            with open(f"{base_name}.kicad_pro", "w", encoding="utf-8") as f:
                f.write(pro_content)

            log("Gerando arquivos do KiCad...")
            sch_file = self.sch_gen.generate(circuit, f"{base_name}.kicad_sch")
            pcb_file = self.pcb_gen.generate(circuit, f"{base_name}.kicad_pcb")
            
            # Exportação IPC-D-356
            log("Exportando Netlist industrial (IPC-D-356)...")
            from src.generators.ipc356_generator import IPC356Generator
            ipc_gen = IPC356Generator()
            ipc_file = f"{base_name}.ipc"
            ipc_gen.generate(circuit, ipc_file)

            # Exportação DSN para Roteamento automático
            log("Exportando formato SPECTRA DSN para Auto-Routing...")
            from src.generators.dsn_generator import DSNGenerator
            dsn_gen = DSNGenerator()
            dsn_file = f"{base_name}.dsn"
            dsn_gen.generate(circuit, dsn_file)
            
            log(f"Projeto completo criado: {base_name}.kicad_pro")
            return True, f"Sucesso! Projeto '{circuit.project_name}' pronto no KiCad (inclui IPC e DSN)."
            
        except Exception as e:
            error_msg = f"Erro no processamento: {str(e)}"
            log(error_msg)
            return False, error_msg
