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
        from src.generators.bom_generator import BOMGenerator
        from src.generators.firmware_generator import FirmwareGenerator
        self.bom_gen = BOMGenerator()
        self.firm_gen = FirmwareGenerator()

    def process(self, description: str, callback=None):
        def log(msg):
            if callback: callback(msg)
            print(msg)

        log("🚀 Iniciando Pipeline Level 3 (Autônomo & Realístico)...")
        
        # Prompt Inicial
        prompt_context = f"""
        Você é um engenheiro de hardware KiCad especializado. Converta a descrição em um JSON estruturado.
        Texto: {description}
        Retorne APENAS o JSON no formato:
        {{
            "project_name": "...",
            "description": "...",
            "components": [{{ "id": "R1", "type": "Resistor", "value": "10k", "library_ref": "Device:R", "connections": [{{ "pin_number": "1", "net_name": "GND" }}] }}],
            "nets": [{{ "name": "GND", "nodes": ["R1:1"] }}]
        }}
        """
        messages = [{"role": "system", "content": "Você é um expert em hardware KiCad."}, 
                    {"role": "user", "content": prompt_context}]
        
        repair_attempts = 2
        circuit = None
        base_name = "project"

        for attempt in range(repair_attempts + 1):
            if attempt > 0:
                log(f"🔄 Iniciando rodada de Auto-Reparo (Tentativa {attempt}/{repair_attempts})...")

            raw_response = self.client.chat_completion(
                messages, 
                response_format={"type": "json_object"},
                callback=log
            )

            try:
                json_str = raw_response.strip()
                if json_str.startswith("```"):
                    json_str = json_str.split("```")[1]
                    if json_str.startswith("json"): json_str = json_str[4:]
                
                data = json.loads(json_str)
                circuit = Circuit(**data)
                base_name = circuit.project_name.lower().replace(" ", "_")

                # Refinamento de Componentes via DB
                from src.component_db import ComponentDB
                db = ComponentDB()
                for comp in circuit.components:
                    results = db.search_symbol(comp.type if comp.library_ref == "???" else comp.library_ref)
                    if results: comp.library_ref = results[0][0]
                    if not comp.footprint:
                        fps = db.get_suggested_footprints(comp.library_ref)
                        if fps: comp.footprint = fps[0]

                # 4. Validação Técnica (ERC/DRC)
                log("🔍 Validando design e verificando integridade técnica...")
                from src.validator import DesignValidator
                validator = DesignValidator(circuit)
                validator.validate_erc()
                
                # Gera PCB temporária para DRC
                temp_pcb = f"temp_val.kicad_pcb"
                self.pcb_gen.generate(circuit, temp_pcb)
                with open(temp_pcb, "r", encoding="utf-8") as f:
                    validator.validate_drc(f.read())
                
                report = validator.get_report()
                
                if not report["is_valid"] and attempt < repair_attempts:
                    log(f"⚠️ Falhas detectadas. Enviando para Auto-Reparo IA...")
                    error_summary = "\n".join(report["errors"] + report["warnings"])
                    repair_prompt = f"""
                    O design anterior possui os seguintes erros técnicos:
                    {error_summary}
                    
                    Por favor, corrija o JSON do circuito para resolver esses problemas. 
                    Certifique-se de que todos os pinos estejam conectados em redes (nets) válidas e não haja sobreposições.
                    Retorne apenas o JSON corrigido.
                    """
                    messages.append({"role": "assistant", "content": raw_response})
                    messages.append({"role": "user", "content": repair_prompt})
                    continue # Tenta de novo
                
                log("✅ Design aprovado pela validação técnica.")
                break # Sai do loop de reparo

            except Exception as e:
                log(f"❌ Erro na tentativa {attempt}: {e}")
                if attempt == repair_attempts: return False, str(e)

        try:
            # Geração de arquivos finais
            log("📁 Gerando arquivos finais do projeto KiCad...")
            
            # .kicad_pro
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader("src/generators"))
            pro_template = env.get_template("project_template.j2")
            pro_content = pro_template.render({"project_name": circuit.project_name})
            with open(f"{base_name}.kicad_pro", "w", encoding="utf-8") as f: f.write(pro_content)

            self.sch_gen.generate(circuit, f"{base_name}.kicad_sch")
            self.pcb_gen.generate(circuit, f"{base_name}.kicad_pcb")

            # 5. Novas Funcionalidades Level 3
            log("🛒 Gerando BOM (Base de Materiais) com preços reais...")
            self.bom_gen.generate(circuit, f"{base_name}_bom.csv")

            log("💻 Gerando Firmware de inicialização (.ino)...")
            self.firm_gen.generate(circuit, f"{base_name}_firmware.ino")

            # IPC & DSN
            from src.generators.ipc356_generator import IPC356Generator
            from src.generators.dsn_generator import DSNGenerator
            IPC356Generator().generate(circuit, f"{base_name}.ipc")
            DSNGenerator().generate(circuit, f"{base_name}.dsn")
            
            log(f"✅ Projeto completo criado com sucesso: {base_name}.kicad_pro")
            return True, f"Sucesso! Projeto '{circuit.project_name}' pronto com BOM e Firmware."
            
        except Exception as e:
            error_msg = f"Erro na geração final: {str(e)}"
            log(error_msg)
            return False, error_msg
